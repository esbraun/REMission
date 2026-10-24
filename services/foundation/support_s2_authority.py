"""Narrow S2 administrative derivation and installed interactive closure verifier.

No HTTP input or worker object constructs these verifiers. Every call checks the
current Store control against the typed binding attached by Store construction.
"""
from datetime import timedelta
import json
from contracts.domain.analysis import canonical,sha,reference
from contracts.domain.boundaries import lineage_heads,visible_records
from contracts.domain.evidence_v2 import exact_ref,resolve,projection_hash
from contracts.domain.protocol import ObservedHistoryV21,RECORD_ADAPTER_V21
from contracts.domain.support_s2_controller import (CONFIG_REF,AuthorizationBasis,
    InteractiveSupportQualification,InteractiveStageCompletion)

BASIS_ID='poc-support-s2-execution-basis-v1'
STAGE_RULE=reference('poc-support-stage-rule-v1','Explicit offered/delivered transitions; exhaustive active stage events per noon window')


def qualification(db):
    from .store import SupportConnection
    if not isinstance(db,SupportConnection):raise ValueError('installed_interactive_support_qualification_required')
    raw,bundle,source,runtime,control=db._read_support_binding()
    q=InteractiveSupportQualification.model_validate_json(raw)
    p=q.packet
    current=db.execute('SELECT * FROM service_control WHERE singleton=1').fetchone()
    if (not current or not current['enabled'] or (current['database_instance_id'],current['authority_generation'])!=(p.store_id,p.authority_generation)
            or any(current[k]!=v for k,v in json.loads(control).items())
            or bundle!=p.installed_bundle_sha256 or source!=p.app_commit or json.loads(runtime)!=p.runtime.model_dump(mode='json')):
        raise ValueError('interactive_installation_source_runtime_Store_generation_mismatch')
    # Store.validate_control independently checks all current service/control and
    # InstalledBundle identities under the existing transaction admission lock.
    return q


def put(db,patient,actor,kind,value,received_at):
    ref=reference(kind,value);identifier='s2-proof-'+ref['sha256']
    if db.execute('SELECT 1 FROM state_changes WHERE id=?',(identifier,)).fetchone():
        raise ValueError('interactive_proof_identity_already_inserted')
    db.execute('INSERT INTO state_changes VALUES(?,?,?,?,?)',(identifier,patient,actor,received_at.isoformat(),canonical(value)))
    return ref


def get(db,patient,ref,model=None):
    row=db.execute('SELECT patient_id,actor_id,payload FROM state_changes WHERE id=?',('s2-proof-'+ref.sha256,)).fetchone()
    if not row or row['patient_id']!=patient:raise ValueError('owned_interactive_proof_required')
    value=json.loads(row['payload'])
    if reference(ref.id,value)!=ref.model_dump():raise ValueError('interactive_proof_content_identity_changed')
    return model.model_validate_json(canonical(value)) if model else value


def known_history(full,refs):
    if len({r.record_id for r in refs})!=len(refs):raise ValueError('duplicate_authorization_context')
    records=[resolve(full,ref) for ref in refs]
    return ObservedHistoryV21.model_validate_json(canonical(dict(schema_version='2.1.0',synthetic=True,
        kind='observed_history',patient_id=full.patient_id,records=[r.model_dump(mode='json') for r in records])))


def validate_basis(db,full,basis):
    from .protocol import validate_snapshot
    from .support_s2_controller import mask,final_distribution
    q=qualification(db);p=q.packet
    patient=db.execute('SELECT * FROM patients WHERE id=? AND owner_id=?',(basis.patient_id,basis.owner_id)).fetchone()
    if (not patient or full.patient_id!=basis.patient_id or basis.configuration.model_dump()!=CONFIG_REF
            or basis.qualification.model_dump()!=q.reference or (basis.store_id,basis.authority_generation)!=(p.store_id,p.authority_generation)
            or json.loads(patient['state_json']).get('simulation',{}).get('panel_id')!=basis.generation_id):
        raise ValueError('authorization_owned_installation_or_generation_changed')
    known=known_history(full,basis.known_refs)
    snapshot=resolve(known,basis.current_snapshot,{'decision_snapshot'})
    envelope=resolve(known,basis.envelope,{'protocol_snapshot'})
    original=resolve(known,basis.original_approval,{'approval'})
    command=db.execute('SELECT patient_id,actor_id,payload FROM state_changes WHERE id=?',(basis.original_command_id,)).fetchone()
    if not command or command['patient_id']!=basis.patient_id or command['actor_id']!=basis.actor_id:
        raise ValueError('original_explicit_envelope_command_required')
    command=json.loads(command['payload'])
    loop=basis.frozen_state['simulation']['support_controller']
    if (command.get('kind')!='support_envelope_command' or command['command']['action']!='approve'
            or command['command']['decision_id']!=original.decision_id or command.get('envelope_id')!=envelope.record_id
            or original.record_id.startswith('s2-admin-') or original.clinician_id!=basis.actor_id or basis.actor_id!=basis.owner_id
            or original.purpose!='randomization_protocol' or original.option is not None
            or set(original.permitted_options)!={'support_prompt','no_prompt'} or basis.original_approval not in envelope.approval_refs
            or (loop.get('snapshot_id'),loop.get('approval_id'),loop.get('actor'),loop.get('command_id'))!=
                (envelope.record_id,original.record_id,original.clinician_id,basis.original_command_id)):
        raise ValueError('original_envelope_actor_or_binary_authority_changed')
    validate_snapshot(known,envelope,max(basis.at,basis.received_at)+timedelta(microseconds=1))
    versions=dict(zip(('version','state_version','consent_version','eligibility_version'),
        (snapshot.patient_version,snapshot.state_version,snapshot.consent_version,snapshot.eligibility_version)))
    if (basis.versions!=versions or snapshot.cutoff!=basis.at or snapshot.view.mode!='current'
            or snapshot.workflow.model_dump(mode='json')!=basis.frozen_state['workflow']):
        raise ValueError('authorization_exact_current_snapshot_versions_required')
    heads=lineage_heads(visible_records([r for r in known.records if r.kind=='consent' and r.component=='mrt_bandit'],max(basis.at,basis.received_at),inclusive=True))
    if [exact_ref(r) for r in sorted(heads,key=lambda r:r.record_id)]!=basis.consent_heads:
        raise ValueError('authorization_current_consent_heads_changed')
    allowed,reasons=mask(known,basis.frozen_state,basis.at,basis.received_at)
    if tuple(basis.allowed_actions)!=allowed:raise ValueError('authorization_current_mask_changed')
    _,probabilities,fallback=final_distribution(allowed,basis.saved)
    if probabilities!=basis.probabilities or fallback!=basis.fallback_reason:
        raise ValueError('authorization_final_distribution_or_saved_basis_changed')
    eligibility=[e for e in snapshot.eligibility if e.action in ('support_prompt','no_prompt')]
    executed={e.action for e in eligibility if e.status=='eligible'} if snapshot.workflow.support_mode!='paused' else set()
    if executed!=set(allowed):
        raise ValueError('authorization_snapshot_eligibility_changed')
    return snapshot,envelope,original


def derive_execution_authorization(db,full,patient,state,snapshot,saved,probabilities,fallback,at,received_at):
    from .support_s2_controller import mask
    q=qualification(db);loop=state['simulation']['support_controller']
    current=db.execute('SELECT * FROM patients WHERE id=? AND owner_id=?',(patient['id'],patient['owner_id'])).fetchone()
    actual=json.loads(current['state_json']) if current else {}
    if (not current or any(current[k]!=patient[k] for k in ('version','state_version','consent_version','eligibility_version'))
            or actual.get('workflow')!=state['workflow'] or actual.get('simulation',{}).get('support_controller')!=loop
            or actual.get('simulation',{}).get('nof1',{})!=state['simulation'].get('nof1',{})):
        raise ValueError('derive_authorization_requires_actual_current_locked_state')
    envelope=next(r for r in full.records if r.record_id==loop['snapshot_id'])
    original=next(r for r in full.records if r.record_id==loop['approval_id'])
    known=full.records if any(r.record_id==snapshot.record_id for r in full.records) else [*full.records,snapshot]
    heads=lineage_heads(visible_records([r for r in known if r.kind=='consent' and r.component=='mrt_bandit'],max(at,received_at),inclusive=True))
    allowed,_=mask(full,state,at,received_at)
    basis=AuthorizationBasis.model_validate_json(canonical(dict(schema_version='s2-controller-authorization-v1',configuration=CONFIG_REF,
        qualification=q.reference,owner_id=patient['owner_id'],patient_id=patient['id'],generation_id=state['simulation']['panel_id'],
        store_id=q.packet.store_id,authority_generation=q.packet.authority_generation,envelope=exact_ref(envelope).model_dump(),
        original_approval=exact_ref(original).model_dump(),original_command_id=loop['command_id'],actor_id=original.clinician_id,
        assignment_unit='assignment-unit-'+sha(['s2-assignment-unit-v1',state['simulation']['seed'],state['simulation']['index']])[:32],
        current_snapshot=exact_ref(snapshot).model_dump(),versions={k:patient[k] for k in ('version','state_version','consent_version','eligibility_version')},
        known_refs=[exact_ref(r).model_dump() for r in known],consent_heads=[exact_ref(r).model_dump() for r in sorted(heads,key=lambda r:r.record_id)],
        frozen_state=dict(workflow=state['workflow'],simulation=dict(day=state['simulation']['day'],support_controller=loop,nof1=state['simulation'].get('nof1',{}))),
        at=at.isoformat(),received_at=received_at.isoformat(),allowed_actions=list(allowed),probabilities=probabilities,saved=saved,fallback_reason=fallback)))
    validate_basis(db,known_history(full,basis.known_refs),basis)
    return put(db,patient['id'],original.clinician_id,BASIS_ID,basis.model_dump(mode='json'),received_at)


def authorization_verifier(db,full):
    def verify(decision,cutoff):
        if decision.execution_receipt.id!=BASIS_ID:raise ValueError('interactive_derivation_basis_required')
        basis=get(db,full.patient_id,decision.execution_receipt,AuthorizationBasis)
        snapshot,envelope,original=validate_basis(db,full,basis)
        if (decision.decision_snapshot!=basis.current_snapshot or decision.cutoff!=basis.at or decision.probabilities!=basis.probabilities
                or decision.context_projection_sha256!=projection_hash(known_history(full,basis.known_refs),basis.at)
                or decision.context_projection_sha256!=projection_hash(full,basis.at)):
            raise ValueError('interactive_decision_basis_or_context_mismatch')
        if decision.assignment_id:
            assignment=next(r for r in full.records if r.record_id==decision.assignment_id)
            approval=next(r for r in full.records if r.record_id==assignment.approval_id)
            if (approval.record_id!='s2-admin-'+decision.execution_receipt.sha256[:32] or approval.clinician_id!=original.clinician_id
                    or approval.decision_id!=snapshot.record_id or assignment.decision_id!=snapshot.record_id
                    or assignment.option not in basis.allowed_actions or assignment.probability!=
                        (basis.probabilities[assignment.option] if decision.availability=='randomized' else None)):
                raise ValueError('administrative_execution_not_derived_from_original_envelope')
            if decision.availability=='randomized':
                expected=dict(namespace='assignment',protocol=CONFIG_REF['id'],scenario='interactive-synthetic',replicate=0,
                    patient=basis.assignment_unit,time_index=basis.frozen_state['simulation']['day'],process='s2-support-assignment-v1')
                if assignment.seed is None or assignment.seed.model_dump()!=expected:
                    raise ValueError('interactive_assignment_purpose_key_changed')
            elif assignment.seed is not None:raise ValueError('deterministic_interactive_execution_has_no_rng')
        return basis
    return verify


def is_interactive(decision):
    return decision.policy.id==CONFIG_REF['id'] or decision.execution_receipt.id==BASIS_ID


def validate_live_history(db,full):
    """Shared live projection/export admission; legacy records remain untouched."""
    decisions=[r for r in full.records if r.kind=='support_decision' and is_interactive(r)]
    admins=[r for r in full.records if r.kind=='approval' and r.record_id.startswith('s2-admin-')]
    if not decisions and not admins:return full
    verify=authorization_verifier(db,full)
    for decision in decisions:verify(decision,max(r.available_at for r in full.records)+timedelta(microseconds=1))
    owned={r.approval_id for r in full.records if r.kind=='assignment' and r.record_id in {d.assignment_id for d in decisions}}
    if any(r.record_id not in owned for r in admins):raise ValueError('unbound_interactive_administrative_approval')
    return full


def interactive_stage_verifier(db,full):
    def verify(closure,cutoff):
        q=qualification(db)
        if not hasattr(closure,'stage'):closure=resolve(full,closure,{'support_stage_closure'},cutoff=cutoff)
        else:resolve(full,exact_ref(closure),{'support_stage_closure'},cutoff=cutoff)
        if closure.completion_receipt is None or closure.completion_receipt.id!='poc-support-interactive-completion-v1':
            raise ValueError('interactive_completed_stage_proof_required')
        completion=get(db,full.patient_id,closure.completion_receipt,InteractiveStageCompletion)
        decision=resolve(full,completion.decision,{'support_decision'},cutoff=cutoff)
        basis=authorization_verifier(db,full)(decision,cutoff)
        if (completion.qualification.model_dump()!=q.reference or completion.authorization!=decision.execution_receipt
                or (completion.owner_id,completion.patient_id,completion.generation_id,completion.store_id,completion.authority_generation)!=
                    (basis.owner_id,basis.patient_id,basis.generation_id,basis.store_id,basis.authority_generation)
                or closure.support_decision!=completion.decision or closure.assignment_ref!=completion.assignment
                or closure.window_id!=decision.outcome_window.id or closure.decision_index!=decision.decision_index
                or closure.status!='complete' or closure.stage_completed_at!=completion.simulated_completed_at
                or closure.available_at!=completion.simulated_available_at or not completion.simulated_available_at<cutoff
                or not decision.cutoff<=completion.simulated_completed_at<decision.outcome_window.ends_at):
            raise ValueError('interactive_completion_identity_or_clock_mismatch')
        assignment=resolve(full,completion.assignment,{'assignment'},cutoff=cutoff) if completion.assignment else None
        if assignment is None or assignment.record_id!=decision.assignment_id:
            raise ValueError('interactive_unavailable_or_canceled_stage_is_unknown')
        output=get(db,full.patient_id,completion.output_ref)
        encoded=canonical(output).encode()
        if (len(encoded)!=completion.output_bytes or sha(output)!=completion.output_sha256
                or not isinstance(output,list) or len(output)!=completion.output_count
                or len({r['record_id'] for r in output})!=len(output)):
            raise ValueError('interactive_preclosure_output_integrity')
        rows=[RECORD_ADAPTER_V21.validate_json(canonical(r)) for r in output]
        dispatch=decision.cutoff+timedelta(hours=8)
        expected_stages=['delivered','offered'] if assignment.option=='support_prompt' else ['delivered']
        if sorted(r.stage for r in rows if r.kind=='delivery')!=expected_stages or any(r.kind!='delivery' for r in rows):
            raise ValueError('interactive_actual_offer_and_delivery_required')
        for r in rows:
            if (r.patient_id!=full.patient_id or r.assignment_id!=assignment.record_id or r.option!=assignment.option
                    or r.event_at!=dispatch or r.available_at>completion.simulated_completed_at
                    or resolve(full,exact_ref(r),{'delivery'},cutoff=cutoff)!=r):
                raise ValueError('interactive_output_foreign_changed_or_outside_stage')
            expected_source=('foundation-support-offer-v1','1.0.0','research_configuration') if r.stage=='offered' else ('poc-longitudinal-v2','2.0.0','simulation')
            if (r.source.id,r.source.version,r.source.adapter)!=expected_source:
                raise ValueError('interactive_stage_registered_producer_required')
        active=full.as_known_at(cutoff)
        exhaustive=[r for r in active if r.kind=='delivery' and r.assignment_id==assignment.record_id and r.stage in ('offered','delivered')]
        if sorted((exact_ref(r).model_dump() for r in rows),key=lambda r:r['record_id'])!=sorted((exact_ref(r).model_dump() for r in exhaustive),key=lambda r:r['record_id']):
            raise ValueError('interactive_stage_output_not_exhaustive')
        ledgers=completion.ledgers
        if len(ledgers)!=2 or {r.stage for r in ledgers}!={'offered','delivered'}:
            raise ValueError('interactive_two_separate_stage_ledgers_required')
        ledger=next(r for r in ledgers if r.stage==closure.stage)
        expected=[exact_ref(r) for r in rows if r.stage==closure.stage]
        if (ledger.patient_id!=full.patient_id or ledger.run_id!=completion.generation_id
                or ledger.window_id!=closure.window_id or ledger.decision_index!=closure.decision_index
                or ledger.stage!=closure.stage or ledger.rule.model_dump()!=STAGE_RULE
                or ledger.event_refs!=expected or closure.stage_event_refs!=expected or closure.row_count!=len(expected)
                or closure.run_id!=ledger.run_id or closure.partition_id!=ledger.partition_id
                or reference(ledger.id,ledger.model_dump(mode='json'))!=closure.stage_ledger.model_dump()):
            raise ValueError('interactive_stage_ledger_or_event_set_changed')
        return [r for r in rows if r.stage==closure.stage]
    return verify


def close_stages(db,settings,patient,decision,assignment,offered,received_at,*,canceled=False):
    """Called AFTER full product admission, in the same app transaction."""
    from .workflow import history,record_header
    from .nof1 import persist
    from contracts.runs.coverage_v2 import StageLedgerV2
    q=qualification(db);full=history(db,patient['id'])
    basis=authorization_verifier(db,full)(decision,decision.outcome_window.ends_at+timedelta(minutes=1))
    cutoff=decision.outcome_window.ends_at+timedelta(minutes=1)
    reports=[r for r in full.as_known_at(cutoff) if r.kind=='daily_report' and r.event_at==decision.outcome_window.assessment_at]
    if len(reports)!=1:raise ValueError('interactive_exact_mature_report_required')
    report=reports[0];closures=[];rows=[]
    if assignment is not None and not canceled:
        rows=[r for r in full.as_known_at(cutoff) if r.kind=='delivery' and r.assignment_id==assignment.record_id and r.stage in ('offered','delivered')]
        if assignment.option=='support_prompt' and (offered is None or not any(r==offered for r in rows)):
            raise ValueError('interactive_missing_actual_offer_remains_unknown')
        # Independent delivery-only output precedes the completion/closure hashes.
        output=[r.model_dump(mode='json') for r in rows]
        output_ref=put(db,patient['id'],basis.actor_id,'poc-support-interactive-stage-output-v1',output,received_at)
        completed=decision.cutoff+timedelta(hours=8,seconds=1);available=completed+timedelta(seconds=1)
        ledgers=[StageLedgerV2.model_validate_json(canonical(dict(schema_version='2.0.0',synthetic=True,kind='support_stage_ledger',
            id='interactive-ledger-'+sha([decision.record_id,stage])[:32],run_id=basis.generation_id,
            partition_id='interactive-'+sha(patient['id'])[:32],patient_id=patient['id'],decision_index=decision.decision_index,
            window_id=decision.outcome_window.id,stage=stage,rule=STAGE_RULE,event_refs=[exact_ref(r).model_dump() for r in rows if r.stage==stage])))
            for stage in ('offered','delivered')]
        completion=InteractiveStageCompletion.model_validate_json(canonical(dict(schema_version='poc-support-interactive-completion-v1',
            qualification=q.reference,authorization=decision.execution_receipt.model_dump(),owner_id=patient['owner_id'],patient_id=patient['id'],
            generation_id=basis.generation_id,store_id=q.packet.store_id,authority_generation=q.packet.authority_generation,
            decision=exact_ref(decision).model_dump(),assignment=exact_ref(assignment).model_dump(),output_ref=output_ref,
            output_bytes=len(canonical(output).encode()),output_sha256=sha(output),output_count=len(output),ledgers=[r.model_dump(mode='json') for r in ledgers],
            simulated_completed_at=completed.isoformat(),simulated_available_at=available.isoformat(),received_at=received_at.isoformat(),
            published_at=settings.clock().isoformat())))
        ref=put(db,patient['id'],basis.actor_id,'poc-support-interactive-completion-v1',completion.model_dump(mode='json'),received_at)
        if settings.fault:settings.fault('after_support_completion')
        for ledger in ledgers:
            header=record_header('interactive-closure-'+sha([decision.record_id,ledger.stage])[:32],patient['id'],completed)
            header.update(schema_version='2.0.0',recorded_at=available.isoformat(),available_at=available.isoformat())
            closures.append(persist(db,dict(**header,kind='support_stage_closure',run_id=ledger.run_id,partition_id=ledger.partition_id,
                support_decision=exact_ref(decision).model_dump(),assignment_ref=exact_ref(assignment).model_dump(),window_id=decision.outcome_window.id,
                decision_index=decision.decision_index,stage=ledger.stage,rule=STAGE_RULE,stage_completed_at=completed.isoformat(),status='complete',
                stage_event_refs=[r.model_dump() for r in ledger.event_refs],stage_ledger=reference(ledger.id,ledger.model_dump(mode='json')),
                row_count=len(ledger.event_refs),reason='Actual interactive simulated stage closed exhaustively',completion_receipt=ref),received_at))
        full=history(db,patient['id']);verify=interactive_stage_verifier(db,full)
        for closure in closures:verify(closure,cutoff)
    assessment=decision.outcome_window.assessment_at;published=assessment+timedelta(seconds=20)
    header=record_header(decision.outcome_link_id,patient['id'],assessment)
    header.update(schema_version='2.0.0',recorded_at=published.isoformat(),available_at=published.isoformat())
    observed=report.missingness=='observed' and report.sleep_quality is not None
    available=assignment is not None and not canceled
    reward=dict(status=('observed' if observed else 'missing') if available else 'pending',
        report_ref=exact_ref(report).model_dump() if available and observed else None,field='sleep_quality',unit='quality_points',
        reason=None if available and observed else ('Independent reported reward missing' if available else 'Unavailable or canceled assignment; no selector reward'),
        evidence_refs=[exact_ref(report).model_dump()] if available else [],definition_refs=[])
    link=persist(db,dict(**header,kind='support_outcome_link',support_decision=exact_ref(decision).model_dump(),
        assignment_ref=exact_ref(assignment).model_dump() if assignment else None,window_id=decision.outcome_window.id,
        assessment_at=assessment.isoformat(),evaluated_as_of=(assessment+timedelta(seconds=10)).isoformat(),reward=reward,
        burden=[dict(definition=STAGE_RULE,type=stage+'_prompt_count',unit='count',status='observed' if closures else 'pending',
            value=int(assignment.option=='support_prompt') if closures else None,
            source_refs=[exact_ref(r).model_dump() for r in rows if r.stage==stage] if closures else []) for stage in ('offered','delivered')],
        offered_closure_ref=exact_ref(closures[0]).model_dump() if closures else None,
        delivered_closure_ref=exact_ref(closures[1]).model_dump() if closures else None),received_at)
    if settings.fault:settings.fault('after_support_outcome')
    return link
