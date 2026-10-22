"""Owned observed protocol projection; no activation, controller or estimator."""
import json
from contracts.domain.analysis import canonical,sha,FIXED_SUPPORT_REF
from contracts.domain.boundaries import validate_assignment,validate_approval
from contracts.domain.evidence_v2 import resolve,projection_hash,validate_outcome_link,validate_support_decision
from contracts.domain.protocol import LAW,PROTOCOL_REFS
from contracts.domain.protocol_analysis import (ProtocolHistory,REDUCED_MODELS,ReducedRef,
                                               ReducedHeader,reduced_header)
from .store import instant
from .workflow import history,patient_clock


def _available(history,record,cutoff):
    # Requiring the exact active head at fit cutoff is conservative: corrections
    # that stale an archived decision/reward must be surfaced, never redirected.
    active={r.record_id for r in history.as_known_at(cutoff)}
    if record.patient_id!=history.patient_id or record.record_id not in active:
        raise ValueError('stale_or_unavailable_protocol_reference')
    return record


def validate_snapshot(history,snapshot,cutoff):
    def exact(ref,kinds):
        record=resolve(history,ref,kinds,cutoff=cutoff)
        resolve(history,ref,kinds,cutoff=snapshot.activation_at,inclusive=True)
        return record
    component='nof1' if snapshot.family=='nof1_med' else 'mrt_bandit'
    consents=[exact(ref,{'consent'}) for ref in snapshot.consent_refs]
    if not any(c.permits(component,snapshot.activation_at) for c in consents):
        raise ValueError('protocol_snapshot_component_consent_required')
    expected={'MED_A','MED_B'} if component=='nof1' else {'support_prompt','no_prompt'}
    for ref in snapshot.approval_refs:
        approval=exact(ref,{'approval'})
        decision=next((r for r in history.records if r.record_id==approval.decision_id),None)
        if decision is None or decision.kind!='decision_snapshot':raise ValueError('protocol_approval_snapshot_missing')
        _available(history,decision,cutoff)
        validate_approval(approval,decision,decision.view,'doctor',snapshot.activation_at,component,consents)
        if set(approval.permitted_options)!=expected:raise ValueError('protocol_approval_requires_exact_binary_envelope')
    background=exact(snapshot.background_ref,{'assignment'})
    if background.option!='behavioral_continue' or background.experimental or background.clinician_override is not None:
        raise ValueError('protocol_snapshot_requires_fixed_continuation')
    for ref in snapshot.support_refs:
        record=exact(ref,{'support_decision','assignment'})
        if record.kind=='assignment' and record.option!='no_prompt':raise ValueError('protocol_support_snapshot_must_be_no_prompt')
        if record.kind=='support_decision' and (record.availability=='randomized' or record.probabilities['support_prompt']!=0):
            raise ValueError('protocol_support_snapshot_must_be_no_prompt')
    return snapshot


def validate_support_v21(history,decision,cutoff):
    snapshot=resolve(history,decision.decision_snapshot,{'decision_snapshot'},cutoff=cutoff)
    if (snapshot.cutoff!=decision.cutoff or snapshot.workflow.support_policy!=decision.policy
            or snapshot.workflow.support_mode!=decision.mode
            or [e for e in snapshot.eligibility if e.action in ('support_prompt','no_prompt')]!=decision.eligibility):
        raise ValueError('support_snapshot_policy_clock_eligibility_mismatch')
    if projection_hash(history,decision.cutoff)!=decision.context_projection_sha256:
        raise ValueError('support_context_full_audit_projection_mismatch')
    if len({ref.record_id for ref in decision.context})!=len(decision.context):raise ValueError('duplicate_support_context')
    for ref in decision.context:
        resolve(history,ref,cutoff=decision.cutoff)
        resolve(history,ref,cutoff=cutoff)
    if (snapshot.workflow.clinical=='clinical_hold' or snapshot.workflow.hold_reasons) and decision.availability!='unavailable':
        raise ValueError('held_support_cannot_assign')
    restriction=decision.policy_constraint
    if restriction.snapshot_ref is not None:
        frozen=resolve(history,restriction.snapshot_ref,{'protocol_snapshot'},cutoff=cutoff)
        if frozen.activation_at>decision.cutoff:raise ValueError('future_policy_snapshot')
        if (restriction.reason=='nof1_snapshot')!=(frozen.family=='nof1_med'):
            raise ValueError('support_constraint_snapshot_family_mismatch')
        validate_snapshot(history,frozen,cutoff)
        if decision.policy.model_dump()!=FIXED_SUPPORT_REF:raise ValueError('fixed_or_frozen_support_identity_changed')
    if decision.assignment_id is not None:
        assignment=next((r for r in history.records if r.record_id==decision.assignment_id),None)
        if assignment is None or assignment.kind!='assignment':raise ValueError('persisted_support_assignment_required')
        _available(history,assignment,cutoff)
        approval=next((r for r in history.records if r.record_id==assignment.approval_id),None)
        if approval is None or approval.kind!='approval':raise ValueError('support_approval_missing')
        _available(history,approval,cutoff)
        consents=[r for r in history.records if r.kind=='consent']
        validate_assignment(assignment,approval,snapshot,snapshot.view,'doctor',consents)
        if (assignment.event_at<decision.distribution_persisted_at or assignment.option not in decision.probabilities
                or not assignment.experimental or assignment.component!='mrt_bandit' or assignment.seed.namespace!='assignment'
                or assignment.probability!=decision.probabilities[assignment.option] or assignment.probability<=0):
            raise ValueError('support_draw_probability_execution_or_persistence_mismatch')
    return decision


def project_protocol(full,cutoff,*,family,origin,verify_closure=None):
    """Full source/ref verification precedes recursive reduction; no raw hashes.

    verify_closure, when needed, is a trusted installed archive/ledger verifier,
    never a caller-provided HTTP argument. Without proof observed burden fails.
    """
    projected=full.project(cutoff)
    selected=set(REDUCED_MODELS)
    records={r.record_id:r for r in projected.records if r.kind in selected}
    cache={};visiting=set()
    def exact(ref,kinds=None,at=None):
        record=resolve(full,ref,kinds,cutoff=cutoff)
        if at is not None:resolve(full,ref,kinds,cutoff=at)
        if record.record_id not in records:raise ValueError('unsupported_protocol_conditioning_reference')
        reduced=reduce(record)
        return dict(record_id=record.record_id,projection_sha256=sha(reduced))
    def closure(ref,at=None):
        if verify_closure is None:raise ValueError('verified_stage_ledger_required_for_burden')
        return verify_closure(ref,at or cutoff)
    def reduce(record):
        if record.record_id in cache:return cache[record.record_id]
        if record.record_id in visiting:raise ValueError('cyclic_protocol_dependency')
        visiting.add(record.record_id)
        model=REDUCED_MODELS[record.kind]
        value=reduced_header(record)
        # Copy only explicitly declared reduced fields that are ordinary values.
        links={'decision_snapshot','context','context_projection_sha256','execution_receipt_id','policy_constraint',
               'consent_refs','approval_refs','background_ref','support_refs','support_decision','assignment_ref','reward','burden',
               'offered_closure_ref','delivered_closure_ref','stage_event_refs','stage_ledger_id','completion_receipt_id'}
        for name in set(model.model_fields)-set(ReducedHeader.model_fields)-links:
            if name=='total':value[name]=record.total
            else:
                copied=record.model_dump(mode='json',include={name})
                if name in copied:value[name]=copied[name]
        if record.kind in {'daily_report','isi','delivery','patient'}:
            expected_adapter='patient_report' if record.kind=='daily_report' else 'simulation'
            if record.source.id!=LAW or record.source.version!='2.0.0' or record.source.adapter!=expected_adapter:
                raise ValueError('unqualified_v2_observed_producer')
        if record.kind=='assignment':
            approval=records.get(record.approval_id);decision=records.get(record.decision_id)
            if approval is None or approval.kind!='approval' or decision is None or decision.kind!='decision_snapshot':
                raise ValueError('owned_assignment_approval_and_decision_required')
            validate_assignment(record,approval,decision,decision.view,'doctor',[r for r in full.records if r.kind=='consent'])
            if record.experimental and record.seed.namespace!='assignment':raise ValueError('independent_protocol_execution_key_required')
            if not record.experimental and record.option!='behavioral_continue':raise ValueError('fixed_protocol_background_required')
        elif record.kind=='protocol_snapshot':
            validate_snapshot(full,record,cutoff)
            value.update(consent_refs=[exact(r,{'consent'}) for r in record.consent_refs],approval_refs=[exact(r,{'approval'}) for r in record.approval_refs],
                         background_ref=exact(record.background_ref,{'assignment'}),support_refs=[exact(r) for r in record.support_refs])
        elif record.kind=='support_decision':
            if record.schema_version=='2.1.0':validate_support_v21(full,record,cutoff)
            else:validate_support_decision(full,record)
            context=sorted((exact(r,at=record.cutoff) for r in record.context),key=lambda r:r['record_id'])
            if record.schema_version!='2.1.0':raise ValueError('protocol_consumer_requires_explicit_2_1_policy_constraint')
            constraint=record.policy_constraint.model_dump(mode='json')
            constraint['snapshot_ref']=exact(record.policy_constraint.snapshot_ref,{'protocol_snapshot'}) if record.policy_constraint.snapshot_ref else None
            value.update(decision_snapshot=exact(record.decision_snapshot,{'decision_snapshot'}),context=context,
                context_projection_sha256=sha(context),policy_constraint=constraint,execution_receipt_id=record.execution_receipt.id)
        elif record.kind=='support_outcome_link':
            validate_outcome_link(full,record,verify_closure=closure)
            reward=record.reward.model_dump(mode='json');reward['report_ref']=exact(record.reward.report_ref,{'daily_report'}) if record.reward.report_ref else None
            reward['evidence_refs']=[exact(r) for r in record.reward.evidence_refs]
            burden=[]
            for item in record.burden:
                data=item.model_dump(mode='json');data['source_refs']=[exact(r,{'delivery'}) for r in item.source_refs];burden.append(data)
            value.update(support_decision=exact(record.support_decision,{'support_decision'}),assignment_ref=exact(record.assignment_ref,{'assignment'}) if record.assignment_ref else None,
                reward=reward,burden=burden,offered_closure_ref=exact(record.offered_closure_ref,{'support_stage_closure'}) if record.offered_closure_ref else None,
                delivered_closure_ref=exact(record.delivered_closure_ref,{'support_stage_closure'}) if record.delivered_closure_ref else None)
        elif record.kind=='support_stage_closure':
            closure(record)
            value.update(support_decision=exact(record.support_decision,{'support_decision'}),assignment_ref=exact(record.assignment_ref,{'assignment'}) if record.assignment_ref else None,
                stage_event_refs=[exact(r,{'delivery'}) for r in record.stage_event_refs],stage_ledger_id=record.stage_ledger.id,
                completion_receipt_id=record.completion_receipt.id if record.completion_receipt else None)
        visiting.remove(record.record_id)
        reduced=model.model_validate_json(canonical(value)).model_dump(mode='json');cache[record.record_id]=reduced
        return reduced
    values=[reduce(record) for record in records.values()]
    return ProtocolHistory.model_validate_json(canonical(dict(schema_version='2.0.0',synthetic=True,kind='poc_protocol_history',version='poc-analysis-history-v1-protocol-v2',
        patient_id=full.patient_id,family=family,cutoff=cutoff.isoformat(),origin=origin.isoformat(),protocol=PROTOCOL_REFS[family],records=values,
        provenance=[reduced_header(r) for r in projected.provenance if r.kind in selected])))


def export_histories(db,owner,patient_ids,cutoff):
    if not patient_ids or len(set(patient_ids))!=len(patient_ids):raise ValueError('unique_owned_protocol_cohort_required')
    result=[]
    for patient_id in sorted(patient_ids):
        patient=db.execute('SELECT * FROM patients WHERE id=? AND owner_id=?',(patient_id,owner)).fetchone()
        if patient is None:raise ValueError('protocol_patient_ownership_required')
        simulation=json.loads(patient['state_json']).get('simulation',{})
        if simulation.get('law_version')!=LAW or simulation.get('family') not in PROTOCOL_REFS:
            raise ValueError('explicit_v2_protocol_patient_required')
        if patient_clock(patient,cutoff)<cutoff:raise ValueError('common_protocol_cutoff_not_reached')
        result.append(project_protocol(history(db,patient_id),cutoff,family=simulation['family'],origin=instant(simulation['origin'])))
    if len({r.family for r in result})!=1:raise ValueError('protocol_families_cannot_share_cohort')
    return result
