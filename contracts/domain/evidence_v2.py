"""Exact evidence resolution with separate causal, review and knowledge clocks."""
import hashlib
import json

from .boundaries import lineage_heads, visible_records


def payload_hash(record):
    return hashlib.sha256(json.dumps(record.model_dump(mode='json'), sort_keys=True,
                                    separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def exact_ref(record):
    from .observed_v2 import ExactRef
    return ExactRef(record_id=record.record_id, payload_sha256=payload_hash(record))


def resolve(history, ref, kinds=None, *, cutoff=None, inclusive=False):
    record = next((r for r in history.records if r.record_id == ref.record_id), None)
    if record is None:
        raise ValueError('missing_exact_dependency')
    if payload_hash(record) != ref.payload_sha256 or record.patient_id != history.patient_id or (kinds and record.kind not in kinds):
        raise ValueError('exact_dependency_hash_patient_type_mismatch')
    if cutoff is not None:
        heads = {r.record_id: r for r in lineage_heads(visible_records(history.records, cutoff, inclusive=inclusive))}
        if record.record_id not in heads:
            raise ValueError('stale_or_not_visible_dependency')
        if record.record_status == 'retracted':
            raise ValueError('retracted_dependency')
    return record


def projection_hash(history, cutoff):
    return payload_hash(history.project(cutoff))


def validate_support_decision(history, decision):
    snapshot = resolve(history, decision.decision_snapshot, {'decision_snapshot'})
    if (snapshot.cutoff != decision.cutoff or snapshot.workflow.support_policy != decision.policy
            or snapshot.workflow.support_mode != decision.mode):
        raise ValueError('support_snapshot_policy_cutoff_mismatch')
    eligible = [e for e in snapshot.eligibility if e.action in ('support_prompt', 'no_prompt')]
    if eligible != decision.eligibility:
        raise ValueError('support_snapshot_eligibility_mismatch')
    if projection_hash(history, decision.cutoff) != decision.context_projection_sha256:
        raise ValueError('incomplete_or_changed_context_projection')
    for ref in decision.context:
        resolve(history, ref, cutoff=decision.cutoff)
    if len({r.record_id for r in decision.context}) != len(decision.context):
        raise ValueError('duplicate_context')
    if decision.assignment_id is not None:
        assignment = next((r for r in history.records if r.record_id == decision.assignment_id), None)
        if assignment is None:
            return 'pending_assignment'
        if assignment.kind != 'assignment' or assignment.decision_id != snapshot.record_id or assignment.support_policy != decision.policy:
            raise ValueError('support_assignment_identity_mismatch')
        approval = next((r for r in history.records if r.record_id == assignment.approval_id), None)
        if approval is None or approval.kind != 'approval' or approval.decision_id != snapshot.record_id:
            raise ValueError('support_assignment_requires_archived_approval_context')
        if assignment.experimental:
            if approval.purpose != 'randomization_protocol' or assignment.option not in approval.permitted_options:
                raise ValueError('archived_protocol_approval_option_mismatch')
        elif approval.purpose != 'ordinary_treatment' or approval.option != assignment.option:
            raise ValueError('archived_ordinary_approval_option_mismatch')
        if assignment.event_at < decision.distribution_persisted_at or assignment.option not in decision.probabilities:
            raise ValueError('draw_precedes_persisted_distribution')
        if decision.probabilities[assignment.option] <= 0:
            raise ValueError('assigned_ineligible_action')
        if decision.availability == 'randomized':
            if not assignment.experimental or assignment.component != 'mrt_bandit' or assignment.probability != decision.probabilities[assignment.option]:
                raise ValueError('selected_propensity_or_mrt_metadata_mismatch')
        elif assignment.experimental or assignment.probability is not None or assignment.seed is not None:
            raise ValueError('deterministic_assignment_cannot_claim_randomization')
    return 'validated'


def validate_outcome_link(history, link, *, verify_closure):
    decision = resolve(history, link.support_decision, {'support_decision'}, cutoff=link.evaluated_as_of)
    if link.window_id != decision.outcome_window.id or link.assessment_at != decision.outcome_window.assessment_at:
        raise ValueError('outcome_window_assessment_mismatch')
    if link.lineage_id != decision.outcome_link_id:
        raise ValueError('outcome_lineage_differs_from_reservation')
    if (decision.assignment_id is None) != (link.assignment_ref is None):
        raise ValueError('outcome_assignment_required_unless_unavailable')
    if link.assignment_ref:
        assignment = resolve(history, link.assignment_ref, {'assignment'}, cutoff=link.evaluated_as_of)
        if assignment.record_id != decision.assignment_id:
            raise ValueError('wrong_outcome_assignment')
    if link.reward.status == 'observed':
        report = resolve(history, link.reward.report_ref, {'daily_report'}, cutoff=link.evaluated_as_of)
        if report.event_at != link.assessment_at or report.missingness != 'observed' or report.sleep_quality is None:
            raise ValueError('reward_requires_exact_assessment_observed_report')
    for ref in link.reward.evidence_refs:
        resolve(history, ref, cutoff=link.evaluated_as_of)
    if link.reward.status == 'missing':
        evidence = [resolve(history, ref, cutoff=link.evaluated_as_of) for ref in link.reward.evidence_refs]
        if not any(r.kind == 'daily_report' and r.event_at == link.assessment_at and r.missingness == 'missing' for r in evidence):
            raise ValueError('missing_reward_requires_assessment_reporting_evidence')
    if link.reward.status == 'undefined' and link.reward.reason != 'outside_generated_horizon':
        evidence = [resolve(history, ref, cutoff=link.evaluated_as_of) for ref in link.reward.evidence_refs]
        if not any(r.kind == 'intercurrent_event' and r.event_type == 'death' and r.event_at <= link.assessment_at for r in evidence):
            raise ValueError('undefined_reward_requires_exact_terminal_evidence')
    for burden, ref, stage in [(next(b for b in link.burden if b.type == 'offered_prompt_count'), link.offered_closure_ref, 'offered'),
                               (next(b for b in link.burden if b.type == 'delivered_prompt_count'), link.delivered_closure_ref, 'delivered')]:
        if ref is None:
            if burden.status == 'observed' or burden.source_refs:
                raise ValueError('observed_zero_or_count_requires_verified_closure')
            continue
        closure = resolve(history, ref, {'support_stage_closure'}, cutoff=link.evaluated_as_of)
        if closure.support_decision != link.support_decision or closure.stage != stage or closure.window_id != link.window_id or closure.assignment_ref != link.assignment_ref:
            raise ValueError('closure_decision_assignment_window_stage_mismatch')
        events = verify_closure(closure, link.evaluated_as_of)
        if burden.status == 'observed':
            if closure.status != 'complete' or burden.source_refs != closure.stage_event_refs:
                raise ValueError('count_requires_complete_exact_stage_evidence')
            # One operational exposure per assignment/stage/window, never per retry.
            expected = len({(e.assignment_id, e.stage, link.window_id) for e in events if e.option == 'support_prompt'})
            if burden.value != expected:
                raise ValueError('operational_count_disagrees_with_verified_ledger')
    return link


def outcome_as_known(history, cutoff, *, verify_closure):
    """Do not silently redirect a saved link after any dependency correction."""
    result = []
    for link in history.as_known_at(cutoff):
        if link.kind != 'support_outcome_link':
            continue
        try:
            refs = [link.support_decision, *link.reward.evidence_refs]
            refs += [r for r in (link.assignment_ref, link.reward.report_ref, link.offered_closure_ref, link.delivered_closure_ref) if r]
            for ref in refs:
                dependency = resolve(history, ref, cutoff=cutoff)
                if dependency.kind == 'support_stage_closure':
                    verify_closure(dependency, cutoff)
            validate_outcome_link(history, link, verify_closure=verify_closure)
            result.append(dict(link_ref=exact_ref(link).model_dump(), status='available'))
        except ValueError as error:
            result.append(dict(link_ref=exact_ref(link).model_dump(), status='stale', reason=str(error)))
    return result


def validate_hold(history, bundle, *, cutoff=None):
    # Static record validation uses its own publication, reconstruction uses K.
    k = cutoff or bundle.available_at
    inclusive = cutoff is None
    snapshot = resolve(history, bundle.snapshot_ref, {'decision_snapshot'}, cutoff=k, inclusive=inclusive)
    if snapshot.event_at != bundle.effective_at or snapshot.policy != bundle.policy or snapshot.model != bundle.model:
        raise ValueError('hold_snapshot_time_configuration_mismatch')
    patient = resolve(history, bundle.ownership_ref, {'patient'}, cutoff=k, inclusive=inclusive)
    if bundle.owner_id not in patient.care_team:
        raise ValueError('hold_owner_not_in_bound_care_team')
    for ref in bundle.follow_up_refs:
        task = resolve(history, ref, {'follow_up'}, cutoff=k, inclusive=inclusive)
        if task.owner != bundle.owner_id or task.due_at < bundle.event_at or not task.trigger or not task.escalation_destination:
            raise ValueError('hold_follow_up_owner_due_trigger_mismatch')
    if projection_hash(history, bundle.context_cutoff) != bundle.context_projection_sha256:
        raise ValueError('hold_causal_projection_changed')
    roles = {e.ref.record_id: e for e in bundle.evidence_roles}
    for entry in roles.values():
        record = resolve(history, entry.ref, cutoff=k, inclusive=inclusive)
        if entry.role == 'causal_context':
            resolve(history, entry.ref, cutoff=bundle.context_cutoff)
        elif entry.role == 'transition_trigger':
            # A correction cannot relabel tomorrow's evidence contemporaneous.
            original = min((r for r in history.records if r.lineage_id == bundle.lineage_id and r.duplicate_of is None), key=lambda r: r.revision)
            if record.event_at > original.event_at or record.recorded_at > original.recorded_at or record.available_at > original.available_at:
                raise ValueError('retrospective_trigger_requires_later_review_role')
        if record.kind == 'hold_review_evidence':
            if (record.run_id, record.partition_id, record.hold_episode_id) != (bundle.run_id, bundle.partition_id, bundle.hold_episode_id):
                raise ValueError('hold_evidence_episode_partition_mismatch')
            if record.ownership_ref != bundle.ownership_ref or record.actor_id != bundle.owner_id or record.actor_role != bundle.owner_role:
                raise ValueError('hold_review_owner_mismatch')
            for fact in [*record.facts_refs, *record.follow_up_refs]:
                item = resolve(history, fact, cutoff=k, inclusive=inclusive)
                if item.event_at > record.event_at or item.recorded_at > record.recorded_at or item.available_at > record.available_at:
                    raise ValueError('hold_review_cannot_use_future_facts')
                if item.kind == 'follow_up' and item.owner != record.actor_id:
                    raise ValueError('hold_review_follow_up_owner_clock_mismatch')
    if bundle.transition_type in ('enter', 'change_reason'):
        if snapshot.workflow.clinical != 'clinical_hold' or snapshot.workflow.support_mode != 'paused' or snapshot.workflow.hold_reasons != bundle.reason_codes:
            raise ValueError('hold_snapshot_requires_paused_reasons')
        if any(e.status == 'eligible' for e in snapshot.eligibility) or not bundle.blocked_actions:
            raise ValueError('hold_must_exclude_experimental_actions')
    if bundle.transition_type == 'resolve_to_assessment':
        if snapshot.workflow.clinical != 'assessment':
            raise ValueError('hold_resolution_must_return_through_assessment')
        for review in bundle.required_reviews:
            for ref in review.evidence_refs:
                evidence = resolve(history, ref, {'hold_review_evidence'}, cutoff=k, inclusive=inclusive)
                if evidence.review_result != 'requirements_satisfied' or evidence.requirement != review.definition or evidence.actor_role != review.responsible_role or evidence.event_at > bundle.event_at:
                    raise ValueError('resolution_predates_or_lacks_required_review')
        for ref in bundle.clearance.evidence_refs:
            evidence = resolve(history, ref, {'hold_review_evidence'}, cutoff=k, inclusive=inclusive)
            if evidence.evidence_type != 'clearance' or evidence.rule != bundle.clearance.rule or evidence.review_result != 'requirements_satisfied' or evidence.event_at > bundle.event_at:
                raise ValueError('invalid_or_future_clearance')
    if bundle.predecessor_bundle_ref:
        prior = resolve(history, bundle.predecessor_bundle_ref, {'hold_transition_bundle'}, cutoff=k, inclusive=inclusive)
        old_snapshot = resolve(history, bundle.predecessor_snapshot_ref, {'decision_snapshot'}, cutoff=k, inclusive=inclusive)
        if prior.snapshot_ref != bundle.predecessor_snapshot_ref or (prior.run_id, prior.partition_id, prior.hold_episode_id) != (bundle.run_id, bundle.partition_id, bundle.hold_episode_id):
            raise ValueError('hold_predecessor_identity_mismatch')
        if prior.transition_sequence + 1 != bundle.transition_sequence or prior.event_at > bundle.event_at:
            raise ValueError('hold_chain_skipped_or_reversed')
        if any(getattr(old_snapshot, f) >= getattr(snapshot, f) for f in ('patient_version', 'state_version', 'eligibility_version')):
            raise ValueError('hold_versions_must_increase')
    return snapshot


def reconstruct_hold(history, cutoff):
    bundles = sorted([r for r in lineage_heads(visible_records(history.records, cutoff)) if r.kind == 'hold_transition_bundle'],
                     key=lambda r: (r.transition_sequence, r.event_at))
    intervals = []
    previous = None
    unresolved = False
    if not bundles:
        return [{'interval_status': 'unresolved', 'reason': 'no_visible_baseline'}]
    for index, bundle in enumerate(bundles):
        reason = None
        try:
            if bundle.record_status == 'retracted':
                raise ValueError('retracted_transition')
            if previous is None and bundle.transition_type != 'baseline':
                raise ValueError('missing_baseline')
            if previous is not None and bundle.predecessor_bundle_ref != exact_ref(previous):
                raise ValueError('fork_or_missing_exact_predecessor')
            snapshot = validate_hold(history, bundle, cutoff=cutoff)
            if unresolved:
                raise ValueError('unresolved_predecessor_interval')
        except ValueError as error:
            reason = str(error)
            unresolved = True
        intervals.append(dict(starts_at=bundle.effective_at, ends_at=bundles[index + 1].effective_at if index + 1 < len(bundles) else None,
                              interval_status='unresolved' if reason else 'held' if snapshot.workflow.clinical == 'clinical_hold' else 'assessment' if bundle.transition_type == 'resolve_to_assessment' else 'baseline',
                              bundle_ref=exact_ref(bundle).model_dump(), reason=reason))
        previous = bundle
    return intervals
