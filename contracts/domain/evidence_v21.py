"""Public exact report graph validation; execution authority stays in admission.

Callers must supply a verified committed publication ledger and execution /
completion receipt resolvers. A list's order or record ID is never publication
authority. Learner analysis always retains strict-before visibility.
"""
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from .boundaries import lineage_heads
from .evidence_v2 import exact_ref, payload_hash, resolve
from .observed_v21 import ReportingInputV21
from .observed_v2 import ExactRef


def _scope(owner, item):
    if item.patient_id != owner.patient_id:
        raise ValueError('foreign_report_patient')
    for name in ('run_id', 'partition_id'):
        if hasattr(item, name) and hasattr(owner, name) and getattr(item, name) != getattr(owner, name):
            raise ValueError('foreign_report_run_partition')


def _ref(history, owner, ref, kinds, sequence, *, analysis_at=None):
    item = resolve(history, ref, kinds, cutoff=analysis_at or owner.available_at, inclusive=analysis_at is None)
    _scope(owner, item)
    if sequence.get(item.record_id, 0) <= 0 or sequence.get(owner.record_id, 0) <= sequence[item.record_id]:
        raise ValueError('exact_dependency_must_precede_owner_in_verified_committed_prefix')
    return item


def _parent(history, owner, sequence):
    parent = _ref(history, owner, owner.report_decision_ref, {'report_observation_decision'}, sequence)
    if parent.event_at != owner.event_at or parent.indicator != 1:
        raise ValueError('response_upload_requires_same_assessment_R1_parent')
    return parent


def _exact_refs(value):
    if isinstance(value, dict):
        if set(value) == {'record_id', 'payload_sha256'}:
            yield ExactRef.model_validate(value)
        else:
            for child in value.values():
                yield from _exact_refs(child)
    elif isinstance(value, list):
        for child in value:
            yield from _exact_refs(child)


def analysis_closure(history, owner, root, sequence, cutoff):
    """Every recursive exact dependency needs its own current strict proof."""
    visited = set()
    def visit(record):
        if record.record_id in visited:
            return
        visited.add(record.record_id)
        for ref in _exact_refs(record.model_dump(mode='json')):
            item = _ref(history, record, ref, None, sequence, analysis_at=cutoff)
            _scope(owner, item)
            visit(item)
    visit(root)
    return root


def validate_completion_parent(history, parent, sequence, *, verify_execution):
    # The strict projection excludes the current equal-time R/payloads itself.
    projection = history.project(parent.decision_at)
    value = ReportingInputV21(schema_version='2.1.0', synthetic=True, kind='reporting_input', temporal_version='2.1.0',
        patient_id=parent.patient_id, report_event_at=parent.report_event_at, decision_at=parent.decision_at,
        pain_ref=parent.pain_ref, pre_report_history=projection, pre_report_projection_sha256=parent.pre_report_projection_sha256,
        previous_quality_ref=parent.previous_quality_ref, absent_history=parent.absent_history)
    for ref in [parent.pain_ref, *([parent.previous_quality_ref] if parent.previous_quality_ref else [])]:
        _ref(history, parent, ref, None, sequence, analysis_at=parent.decision_at)
    verify_execution(parent, value)
    return parent


def validate_upload_receipt(history, receipt, sequence, *, verify_completion):
    parent = _parent(history, receipt, sequence)
    daily = _ref(history, receipt, receipt.daily_report_ref, {'daily_report'}, sequence)
    rating = _ref(history, receipt, receipt.rating_ref, {'subjective_burden_rating'}, sequence)
    if daily.schema_version != '2.1.0' or rating.schema_version != '2.1.0':
        raise ValueError('v21_upload_cannot_substitute_legacy_response')
    if any(r.event_at != parent.event_at or r.report_decision_ref != exact_ref(parent) for r in (daily, rating)):
        raise ValueError('upload_payload_assessment_or_shared_parent_mismatch')
    zone = ZoneInfo(rating.window.timezone)
    local = datetime.combine(rating.window.local_date + timedelta(days=receipt.upload_delay_days), time(8, 1), zone)
    if (parent.assessment_local_date != rating.window.local_date or
        parent.event_at != rating.window.ends_at or
        parent.event_at.astimezone(zone).time() != time(7) or
        parent.decision_at.astimezone(zone).time() != time(8, 1)):
        raise ValueError('upload_parent_window_local_clock_mismatch')
    if receipt.publication_sequence != sequence.get(receipt.record_id):
        raise ValueError('upload_sequence_disagrees_with_verified_committed_prefix')
    if daily.available_at != rating.available_at or receipt.payload_available_at != daily.available_at:
        raise ValueError('both_responses_must_share_one_actual_upload')
    # Revisions have later actual publication clocks; only original payloads
    # have a delay-defined availability. No correction becomes a new draw.
    if any(r.revision == 1 and (r.recorded_at != parent.decision_at or r.available_at != local) for r in (daily, rating)):
        raise ValueError('original_responses_must_share_the_one_declared_delay')
    verify_completion(receipt, parent, daily, rating)
    return receipt


def validate_burden_state(history, state, sequence):
    k = state.evaluated_as_of
    for ref in [*state.source_refs, *state.closure_refs]:
        _ref(history, state, ref, None, sequence, analysis_at=k)
    if state.status == 'undefined':
        if state.terminal_ref:
            terminal = _ref(history, state, state.terminal_ref, {'intercurrent_event'}, sequence, analysis_at=k)
            if terminal.event_type != 'death' or terminal.event_at > state.event_at + timedelta(minutes=61):
                raise ValueError('undefined_state_requires_actual_predecision_terminal_evidence')
        return state
    parent = _ref(history, state, state.report_decision_ref, {'report_observation_decision'}, sequence, analysis_at=k)
    analysis_closure(history, state, parent, sequence, k)
    if parent.event_at != state.event_at or parent.assessment_local_date != state.window.local_date:
        raise ValueError('state_parent_assessment_mismatch')
    if (state.status == 'missing') != (parent.indicator == 0):
        raise ValueError('missing_requires_R0_pending_observed_require_R1')
    if state.status == 'observed':
        rating = _ref(history, state, state.rating_ref, {'subjective_burden_rating'}, sequence, analysis_at=k)
        receipt = _ref(history, state, state.receipt_ref, {'report_upload_receipt'}, sequence, analysis_at=k)
        analysis_closure(history, state, receipt, sequence, k)
        if (rating.window != state.window or rating.instrument != state.instrument or rating.report_decision_ref != state.report_decision_ref or
            receipt.report_decision_ref != state.report_decision_ref or receipt.rating_ref != state.rating_ref):
            raise ValueError('observed_state_requires_exact_shared_parent_rating_receipt')
    return state


def validate_burden_link(history, link, sequence, *, reserved_lineage):
    k = link.evaluated_as_of
    decision = _ref(history, link, link.support_decision, {'support_decision'}, sequence, analysis_at=k)
    analysis_closure(history, link, decision, sequence, k)
    if reserved_lineage(decision.record_id) != link.lineage_id:
        raise ValueError('burden_link_does_not_match_its_coverage_reservation')
    if (decision.assignment_id is None) != (link.assignment_ref is None):
        raise ValueError('burden_link_assignment_is_null_iff_unavailable')
    if link.assignment_ref:
        assignment = _ref(history, link, link.assignment_ref, {'assignment'}, sequence, analysis_at=k)
        if assignment.record_id != decision.assignment_id:
            raise ValueError('burden_link_wrong_support_assignment')
    local_cutoff = decision.cutoff.astimezone(ZoneInfo(link.target_window.timezone))
    if local_cutoff.date() + timedelta(days=1) != link.target_window.local_date:
        raise ValueError('burden_link_targets_next_local_morning')
    for ref in [*link.source_refs, *link.closure_refs]:
        _ref(history, link, ref, None, sequence, analysis_at=k)
    if link.state_ref:
        state = _ref(history, link, link.state_ref, {'burden_assessment_state'}, sequence, analysis_at=k)
        if state.window != link.target_window or state.instrument != link.instrument:
            raise ValueError('burden_link_state_window_instrument_mismatch')
        validate_burden_state(history, state, sequence)
    elif link.terminal_ref:
        terminal = _ref(history, link, link.terminal_ref, {'intercurrent_event'}, sequence, analysis_at=k)
        if terminal.event_type != 'death' or terminal.event_at > link.assessment_at:
            raise ValueError('burden_link_wrong_terminal_evidence')
    return link


def validate_report_graph(history, *, publication_sequences, verify_execution, verify_completion, reserved_lineage):
    """Validate full immutable history at each record's actual publication.

    Resolvers qualify receipt hash/ownership and source execution outside this
    module. A producer cannot turn a shape-only fixture into authority by
    supplying a boolean. Run admission constructs these resolvers from its
    accepted artifact/receipt graph.
    """
    sequence = publication_sequences
    if set(sequence) != {r.record_id for r in history.records} or any(type(s) is not int or s < 1 for s in sequence.values()) or len(set(sequence.values())) != len(sequence):
        raise ValueError('complete_unique_committed_publication_sequence_required')
    if any(r.record_id in refs for r in history.records for refs in [
        {getattr(r, f).record_id for f in ('report_decision_ref', 'daily_report_ref', 'rating_ref', 'receipt_ref', 'state_ref') if getattr(r, f, None)}]):
        raise ValueError('self_exact_report_reference')
    for record in history.records:
        if record.schema_version != '2.1.0' or record.record_status == 'retracted':
            continue
        if record.kind == 'report_observation_decision':
            validate_completion_parent(history, record, sequence, verify_execution=verify_execution)
        elif record.kind in ('daily_report', 'subjective_burden_rating'):
            _parent(history, record, sequence)
        elif record.kind == 'report_upload_receipt':
            validate_upload_receipt(history, record, sequence, verify_completion=verify_completion)
        elif record.kind == 'burden_assessment_state':
            validate_burden_state(history, record, sequence)
        elif record.kind == 'support_burden_outcome_link':
            validate_burden_link(history, record, sequence, reserved_lineage=reserved_lineage)
    active = [r for r in lineage_heads(history.records) if r.record_status != 'retracted']
    zeros = {r.event_at for r in active if r.kind == 'report_observation_decision' and r.indicator == 0}
    if any(r.kind in ('daily_report', 'subjective_burden_rating', 'report_upload_receipt') and r.event_at in zeros for r in active):
        raise ValueError('active_R0_cannot_leave_an_active_response_upload')
    return history
