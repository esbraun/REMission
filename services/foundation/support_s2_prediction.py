"""Trusted background saved-S2 preparation; no appointment/controller activation.

All public execution/mutation entry points refuse before Store or file access.
Prepared functions consume actual same-Store rows and service-owned custody.
No scientific dependency or posterior binary is read in foundation.
"""
import json
import uuid
from contracts.domain.analysis import canonical,reference,sha
from contracts.domain.boundaries import lineage_heads,visible_records
from contracts.domain.entities import DecisionSnapshot
from contracts.domain.protocol import LAW_REF,SUPPORT_REF
from contracts.domain.protocol_analysis import Consent,ReducedRef,reduced_header
from contracts.domain.support_s2_native import NativeInput,NativeResult,CONFIG_REF as NATIVE_REF,SCHEMA_REF
from contracts.domain.support_s2_saved import (CONFIG_REF,ContextBody,CurrentContext,SavedFit,
    SavedPredictionInput,SavedPredictionResult,prospective_features,current_mask,make_request,
    validate_saved_result,require_executable,RESULT_CAP)


def current_sources(db,patient,cutoff,origin,verify_closure):
    from .workflow import history
    from .protocol import project_protocol,validate_snapshot
    full=history(db,patient)
    snapshots=[r for r in full.as_known_at(cutoff) if r.kind=='protocol_snapshot' and r.family=='support']
    if len(snapshots)!=1 or snapshots[0].activation_at!=origin:
        raise ValueError('S2_pending_reactivation_or_delayed_activation_context_coverage')
    validate_snapshot(full,snapshots[0],cutoff)
    projection=project_protocol(full,cutoff,family='support',origin=origin,verify_closure=verify_closure)
    # Inclusive current consent heads retain withdrawals/retractions at cutoff;
    # feature projection remains strictly predecision. They are separate inputs.
    heads=lineage_heads(visible_records([r for r in full.records if r.kind=='consent'
        and r.component=='mrt_bandit'],cutoff,inclusive=True))
    consents=tuple(Consent.model_validate_json(canonical(dict(reduced_header(r),**r.model_dump(mode='json',
        include={'component','consent_status','oversight_status','effective_at','expires_at','withdrawn_at'}))))
        for r in sorted(heads,key=lambda r:r.record_id))
    return projection,consents


def current_context(db,owner,target,fit,*,verify_closure=None):
    """Read genuine prospective metadata; never manufacture an executed decision.

    verify_closure is a trusted installed archive/ledger verifier, never an HTTP
    argument. Observed burden without that proof refuses in project_protocol.
    """
    from .support_s2_analysis import store_identity,instant
    fit=SavedFit.model_validate(fit);p=fit.product.initial.export.provenance
    row=db.execute('SELECT * FROM patients WHERE id=? AND owner_id=?',(target,owner)).fetchone()
    if row is None or target not in [m.patient_id for m in p.members]:raise ValueError('owned_fitted_S2_target_required')
    store,authority=store_identity(db)
    state=json.loads(row['state_json']);sim=state.get('simulation',{})
    if ((owner,store,authority)!=(p.owner_id,p.store_id,fit.product.initial.export.selection.authority_generation)
            or sim.get('panel_id')!=p.generation_id or sim.get('family')!='support'
            or sim.get('protocol')!=SUPPORT_REF or sim.get('law')!=LAW_REF
            or instant(sim['origin'])!=p.origin or sim.get('research_run_id') is not None
            or state.get('historical_read_only') or state.get('observed_archive')):
        raise ValueError('S2_current_owned_generation_authority_required')
    saved=db.execute('SELECT * FROM decisions WHERE id=? AND patient_id=?',(row['current_decision'],target)).fetchone()
    if saved is None:raise ValueError('S2_actual_current_predecision_row_required')
    decision=DecisionSnapshot.model_validate_json(saved['snapshot'])
    if (decision.record_id!=row['current_decision'] or decision.patient_id!=target
            or decision.cutoff!=instant(row['cutoff']) or decision.workflow.model_dump(mode='json')!=state['workflow']
            or (decision.patient_version,decision.state_version,decision.consent_version,decision.eligibility_version)!=
                tuple(row[k] for k in ('version','state_version','consent_version','eligibility_version'))):
        raise ValueError('S2_current_predecision_versions_or_workflow_changed')
    projection,consents=current_sources(db,target,decision.cutoff,p.origin,verify_closure)
    activations=[r for r in projection.records if r.kind=='protocol_snapshot' and r.family=='support']
    if len(activations)!=1:raise ValueError('S2_pending_current_activation_coverage')
    activation=activations[0]
    approvals=[r for r in activation.approval_refs if next(v for v in projection.records if v.record_id==r.record_id).purpose=='randomization_protocol']
    if len(approvals)!=1:raise ValueError('S2_unique_explicit_support_approval_required')
    refs=tuple(ReducedRef.model_validate(dict(record_id=r.record_id,projection_sha256=sha(r.model_dump(mode='json'))))
        for r in sorted(projection.records,key=lambda r:r.record_id))
    activation_ref=ReducedRef.model_validate(dict(record_id=activation.record_id,projection_sha256=sha(activation.model_dump(mode='json'))))
    x,_=prospective_features(projection,refs)
    mask,reason=current_mask(decision,projection,consents,activation_ref,approvals[0],refs)
    body=ContextBody.model_validate_json(canonical(dict(schema_version='s2-saved-context-v1',owner_id=owner,store_id=store,
        authority_generation=authority,generation_id=p.generation_id,decision=decision.model_dump(mode='json'),
        projection=projection.model_dump(mode='json'),current_consents=[c.model_dump(mode='json') for c in consents],
        activation_ref=activation_ref.model_dump(),approval_ref=approvals[0].model_dump(),
        feature_refs=[r.model_dump() for r in refs],x_current=x,allowed_actions=mask,mask_reason=reason)))
    value=body.model_dump(mode='json')
    return CurrentContext.model_validate_json(canonical(dict(value,reference=reference('poc-support-s2-current-context-v1',value))))


def admitted_fit(db,owner,job,*,file_custody,collection_sha256,selection_key,source_commit):
    """Revalidate stored completed fit against external collector custody/current H*.

    Collector arguments are owned host custody, never worker/result assertions.
    This is an internal seam; no route accepts these arguments from clients.
    """
    from .support_s2_analysis import export,store_identity,validate_native_collection
    row=db.execute('SELECT * FROM analysis_attempts WHERE job_id=? AND owner_id=?',(job,owner)).fetchone()
    if row is None or row['status']!='completed' or not row['finished_at'] or not row['result_json']:
        raise ValueError('S2_completed_owned_saved_fit_required')
    raw=json.loads(row['request_json'])
    if raw.get('kind')=='poc_support_s2_app_fit_input':
        raw=dict(schema_version='s2-native-source-1.0.0',kind='poc_support_s2_native_fit_input',initial=raw,
            extension=None,parent_result_reference=None,retained_initial_artifact=None,
            configuration=NATIVE_REF,posterior_schema=SCHEMA_REF,executable=False)
    product=NativeInput.model_validate_json(canonical(raw));p=product.initial.export.provenance
    if (row['input_sha256']!=sha(json.loads(row['request_json'])) or row['patient_id']!=p.target_id
            or json.loads(row['cohort_json'])!=[m.patient_id for m in p.members]
            or row['history_sha256']!=p.histories_sha256 or job!=product.attempt_id):
        raise ValueError('S2_stored_fit_complete_identity_changed')
    result=NativeResult.model_validate_json(row['result_json'])
    launch=json.loads(row['progress_json']).get('trusted_launch')
    if not isinstance(launch,dict):raise ValueError('S2_original_trusted_fit_launch_required')
    current=export(db,owner,selection_key,[dict(patient_id=m.patient_id,patient_version=m.patient_version)
        for m in p.members],p.cutoff,source_commit=source_commit,advancing=True)
    store,authority=store_identity(db)
    validate_native_collection(product,result,launch,file_custody=file_custody,current_export=current,
        active_owner=owner,active_store=store,authority_generation=authority,job=job,
        claim_sha256=launch['claim_sha256'],collection_sha256=collection_sha256)
    return SavedFit.model_validate_json(canonical(dict(product=product.model_dump(mode='json'),result=result.model_dump(mode='json'),
        launch=launch,collection=file_custody,collection_reference=reference('poc-support-s2-saved-fit-collection-v1',file_custody))))


def validate_collection(result,product,trusted,*,current_context,current_fit,custody,at):
    """Scalar exact current identity + owned bounded named-result admission."""
    result=validate_saved_result(result,product,trusted,at=at)
    if current_context!=product.context or current_fit!=product.fit:
        raise ValueError('S2_saved_prediction_current_authority_or_fitted_asof_changed')
    expected=dict(schema='s2-saved-owned-collection-v1',attempt_id=product.attempt_id,
        input_sha256=sha(product.model_dump(mode='json')),claim_sha256=trusted['claim_sha256'],
        terminal='reaped_exit_0_no_oom_no_restart',path='result.json',
        result_sha256=sha(result.model_dump(mode='json')))
    if custody!=expected:raise ValueError('S2_saved_prediction_owned_named_terminal_custody_required')
    return result


def prepare(fit,context,attempt):
    return SavedPredictionInput.model_validate_json(canonical(dict(schema_version='s2-saved-prediction-source-1.0.0',
        kind='poc_support_s2_saved_prediction_input',purpose='EST-POLICY:poc-support-prediction-v1',attempt_id=attempt,
        fit=fit.model_dump(mode='json',by_alias=True),context=context.model_dump(mode='json'),
        request=make_request(fit,context).model_dump(mode='json'),configuration=CONFIG_REF,executable=False)))


def enqueue(db,current,key,fit,context,*,now):
    # Trusted background/research driver only. Gate precedes Store/UUID/writes;
    # appointment navigation/approval/advance never calls this function.
    require_executable()
    return _enqueue(db,current,key,fit,context,now=now)


def _enqueue(db,current,key,fit,context,*,now):
    """Prepared normal transaction/immutable original receipt; no scheduler/RNG."""
    from .support_s2_analysis import receipt_rows,timestamp
    identity=dict(fit=fit.collection_reference.model_dump(),context=context.reference.model_dump(),configuration=CONFIG_REF)
    payload_sha=sha(identity);scope='support-s2-prediction:'+context.decision.patient_id
    receipts=receipt_rows(db,current['account_id'],key)
    if receipts:
        if len(receipts)!=1 or receipts[0]['scope']!=scope or receipts[0]['payload_sha256']!=payload_sha:
            raise ValueError('S2_saved_prediction_original_receipt_conflict')
        return json.loads(receipts[0]['response'])
    # Caller owns the existing BEGIN IMMEDIATE transaction; exact identity may
    # have only one attempt even with a different receipt key.
    for row in db.execute("SELECT * FROM analysis_attempts WHERE owner_id=? AND json_extract(request_json,'$.kind')='poc_support_s2_saved_prediction_input'",(current['account_id'],)):
        other=SavedPredictionInput.model_validate_json(row['request_json'])
        if other.fit.collection_reference==fit.collection_reference and other.context.reference==context.reference:
            raise ValueError('S2_saved_prediction_reconcile_original_receipt')
    if current['account_id']!=context.owner_id:raise ValueError('S2_saved_prediction_owned_context_required')
    members=[m.patient_id for m in fit.product.initial.export.provenance.members]
    for row in db.execute("SELECT job_id,cohort_json FROM analysis_attempts WHERE status IN ('queued','running')"):
        if set(members).intersection(json.loads(row['cohort_json'])):
            raise ValueError('S2_saved_prediction_cohort_member_already_pending')
    job='analysis-'+uuid.uuid4().hex;product=prepare(fit,context,job);p=fit.product.initial.export.provenance
    value=product.model_dump(mode='json',by_alias=True)
    db.execute('INSERT INTO pending_work VALUES(?,?,?,?)',(job,context.decision.patient_id,'queued','S2 saved prediction queued'))
    db.execute('INSERT INTO analysis_attempts(job_id,patient_id,owner_id,previous_attempt,request_json,input_sha256,history_sha256,cutoff,configuration_json,cohort_json,status,stage,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
        (job,context.decision.patient_id,current['account_id'],fit.product.attempt_id,canonical(value),sha(value),p.histories_sha256,
            timestamp(context.decision.cutoff),canonical(CONFIG_REF),canonical([m.patient_id for m in p.members]),'queued','queued',timestamp(now)))
    response=dict(id=job,status='queued',execution_available=False,serving_authority=False)
    db.execute('INSERT INTO receipts VALUES(?,?,?,?,?,?)',(current['account_id'],current['token_hash'],key,scope,payload_sha,canonical(response)))
    return response


def reconcile(db,owner,key):
    from .support_s2_analysis import receipt_rows
    rows=receipt_rows(db,owner,key)
    if not rows:return dict(status='unknown',attempt=None)
    if len(rows)!=1 or not rows[0]['scope'].startswith('support-s2-prediction:'):
        raise ValueError('S2_saved_prediction_original_receipt_required')
    return dict(status='found',attempt=json.loads(rows[0]['response']))


def read_summary(db,owner,job,*,current_context,current_fit,at):
    """Bounded persisted scalar only. No fit/predict call, wait, or binary read.

    Kept default unavailable until serving qualification. The prepared scalar
    validator remains independently testable; this cannot activate a controller.
    """
    return dict(summary_available=False,reason='S2_saved_prediction_serving_unqualified',serving_authority=False)


def _read_summary(db,owner,job,*,current_context,current_fit,custody,at):
    """Prepared bounded persisted scalar read; never launches or waits."""
    row=db.execute('SELECT * FROM analysis_attempts WHERE job_id=? AND owner_id=?',(job,owner)).fetchone()
    if row is None or row['status']!='completed' or not row['result_json']:
        return dict(summary_available=False,reason='S2_saved_prediction_not_completed',serving_authority=False)
    if len(row['result_json'].encode())>RESULT_CAP:raise ValueError('S2_saved_persisted_summary_byte_cap')
    product=SavedPredictionInput.model_validate_json(row['request_json'])
    if (product.context.owner_id!=owner or product.attempt_id!=job or row['input_sha256']!=sha(product.model_dump(mode='json'))):
        raise ValueError('S2_saved_persisted_attempt_identity_changed')
    result=SavedPredictionResult.model_validate_json(row['result_json'])
    trusted=json.loads(row['progress_json']).get('trusted_launch')
    validate_collection(result,product,trusted,current_context=current_context,current_fit=current_fit,custody=custody,at=at)
    return dict(summary_available=result.status=='candidate_ready',status=result.status,reason=result.reason,
        probability=result.probability,context_reference=result.context_reference.model_dump(),
        fit_collection_reference=result.fit_collection_reference.model_dump(),serving_authority=False)


def ingest_saved(store,job,token,directory,raw_result,*,accept_before=None):
    require_executable()  # before parsing/private Store/collection I/O
