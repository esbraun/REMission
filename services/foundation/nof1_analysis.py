"""Explicit owned N analysis commands and saved reads; never imports science."""
import json
import secrets
import uuid

from contracts.domain.analysis import canonical, reference, sha
from contracts.domain.nof1_app import (NInput,NResult,NSubmission,CONFIG_REFS,
    make_input,readiness,validate_result)
from contracts.domain.protocol import LAW_REF,NOF1_REF
from .store import instant,timestamp


def prepare(db,owner,submission,*,attempt_id,fit_seed,now):
    submission=NSubmission.model_validate_json(canonical(submission))
    panels=set()
    for patient_id,version in sorted(submission.patient_versions.items()):
        patient=db.execute('SELECT * FROM patients WHERE id=? AND owner_id=?',(patient_id,owner)).fetchone()
        if patient is None:raise ValueError('owned_N_member_required')
        if patient['version']!=version:raise ValueError('N_member_version_changed')
        if instant(patient['cutoff'])!=submission.cutoff:raise ValueError('N_common_current_cutoff_required')
        state=json.loads(patient['state_json']);simulation=state.get('simulation',{})
        loop=simulation.get('nof1',{})
        if (simulation.get('law_version')!=LAW_REF['id'] or simulation.get('family')!='nof1_med'
                or simulation.get('law')!=LAW_REF or simulation.get('protocol')!=NOF1_REF
                or not simulation.get('panel_id') or simulation.get('research_run_id') is not None):
            raise ValueError('one_explicit_compatible_owned_N_panel_required')
        if loop.get('status') not in ('active','completed') or not loop.get('uninterrupted'):
            raise ValueError('uninterrupted_approved_N_protocol_required')
        from .nof1 import guard
        reasons=guard(db,patient_id,state,submission.cutoff,now)
        if reasons:raise ValueError('; '.join(reasons))
        panels.add(simulation['panel_id'])
    if len(panels)!=1:raise ValueError('N_members_must_share_generation')
    generation=next(iter(panels))
    from .protocol import export_histories
    histories=export_histories(db,owner,list(submission.patient_versions),submission.cutoff)
    run=reference('poc-nof1-app-run-'+sha(generation)[:16],
        dict(generation_id=generation,law=LAW_REF,protocol=NOF1_REF))
    return make_input(histories,purpose=submission.purpose,attempt_id=attempt_id,owner_id=owner,
        cohort_id=submission.cohort_id,generation_id=generation,run=run,target_id=submission.target_id,
        patient_versions=submission.patient_versions,fit_seed=fit_seed)


def submission_for(product,previous=None):
    value=dict(purpose=product.purpose,target_id=product.target_id,cohort_id=product.cohort_id,
        patient_versions={m.patient_id:m.patient_version for m in product.cohort},
        cutoff=product.cutoff.isoformat(),configuration=CONFIG_REFS[product.purpose],previous_attempt=previous)
    return NSubmission.model_validate_json(canonical(value)).model_dump(mode='json')


def frozen(row):
    product=NInput.model_validate_json(row['request_json'])
    if (product.attempt_id!=row['job_id'] or product.owner_id!=row['owner_id']
            or product.target_id!=row['patient_id']
            or [m.patient_id for m in product.cohort]!=json.loads(row['cohort_json'])
            or sha(product.model_dump(mode='json'))!=row['input_sha256']
            or product.history_sha256!=row['history_sha256'] or product.cutoff!=instant(row['cutoff'])
            or product.request.configuration.model_dump()!=json.loads(row['configuration_json'])):
        raise ValueError('stored_N_attempt_binding_changed')
    return product


def revalidate(db,row,*,now):
    product=frozen(row)
    rebuilt=prepare(db,row['owner_id'],submission_for(product,row['previous_attempt']),
        attempt_id=product.attempt_id,fit_seed=product.request.context.seed.replicate,now=now)
    if rebuilt!=product:raise ValueError('N_member_run_generation_or_same_cutoff_history_changed')
    return product


def checked_result(row,product=None):
    """Only bounded canonical JSON is read; numerical artifacts stay offline."""
    try:
        product=product or frozen(row)
        if not row['result_json']:return None,None
        result=NResult.model_validate_json(row['result_json'])
        validate_result(result,product,json.loads(row['progress_json']).get('trusted_launch'))
        if result.status!=row['status']:raise ValueError('stored_N_status_changed')
        return result.model_dump(mode='json'),None
    except (ValueError,KeyError,TypeError):
        return None,'stored_N_summary_unaccepted'


def view(row,*,verified=False,error=None):
    from .appointment import public_summary
    product=frozen(row);result,result_error=checked_result(row,product)
    ready=readiness(product.histories,product.target_id)
    stale=not verified;available=bool(result and result['status']=='completed')
    reason=result_error or error or ('current_N_cohort_unverified' if stale else ready['reason'])
    return public_summary(dict(id=row['job_id'],kind='nof1_analysis',patient_id=product.target_id,
        purpose=product.purpose,target_id=product.target_id,cohort_id=product.cohort_id,
        cohort=[m.patient_id for m in product.cohort],members=[m.model_dump() for m in product.cohort],
        generation_id=product.generation_id,run=product.run.model_dump(),cutoff=row['cutoff'],
        review_day=ready['review_day'],readiness=ready['status'],arm_blocks=ready['arm_blocks'],
        status=row['status'],stage=row['stage'],stale=stale,staleness_reason=error if stale else None,
        configuration=product.request.configuration.model_dump(),previous_attempt=row['previous_attempt'],
        created_at=row['created_at'],started_at=row['started_at'],finished_at=row['finished_at'],
        failure_reason=row['failure_reason'],progress=json.loads(row['progress_json']),result=result,
        input_sha256=row['input_sha256'],history_sha256=row['history_sha256'],
        serving=dict(status='dated' if stale else 'current' if available else row['status'],
            summary_available=available and not stale,saved_summary_available=available,reason=reason,
            data_through=row['cutoff'],published_at=row['finished_at'],
            artifact_generated_at=result['generated_at'] if result else None,
            summary_source='validated_stored_result_json',supported_pair=['MED_A','MED_B'],
            policy='read_only_expected_next7_assignment_contrast')))


def owned_view(db,row,*,now):
    try:revalidate(db,row,now=now)
    except ValueError as error:return view(row,error=str(error))
    return view(row,verified=True)


def submit(db,current,key,payload,*,now):
    from .cohort_analysis import active_overlap
    payload=NSubmission.model_validate_json(canonical(payload)).model_dump(mode='json')
    if not key or len(key)>128:raise ValueError('bounded_stable_N_receipt_key_required')
    scope='nof1-analysis:'+payload['target_id']
    matches=db.execute('SELECT * FROM receipts WHERE owner_id=? AND key=?',
        (current['account_id'],key)).fetchall()
    if len(matches)>1:raise ValueError('ambiguous_N_receipt_reconcile_original_attempt')
    prior=matches[0] if matches else None
    if prior:
        if prior['scope']!=scope or prior['payload_sha256']!=sha(payload):raise ValueError('N_receipt_content_conflict')
        row=db.execute('SELECT * FROM analysis_attempts WHERE job_id=? AND owner_id=?',
            (json.loads(prior['response'])['id'],current['account_id'])).fetchone()
        if row is None:raise ValueError('original_N_receipted_attempt_unavailable')
        return owned_view(db,row,now=now)
    product=prepare(db,current['account_id'],payload,attempt_id='analysis-'+uuid.uuid4().hex,
        fit_seed=secrets.randbelow(2147483647),now=now)
    patients=[m.patient_id for m in product.cohort]
    # A named paired comparison cannot silently switch members or corrected H*.
    paired=db.execute("SELECT * FROM analysis_attempts WHERE owner_id=? AND patient_id=? AND json_extract(request_json,'$.kind')='poc_nof1_input' AND json_extract(request_json,'$.cohort_id')=? AND cutoff=?",
        (current['account_id'],product.target_id,product.cohort_id,timestamp(product.cutoff))).fetchall()
    for row in paired:
        other=frozen(row)
        if other.purpose!=product.purpose and (other.history_sha256!=product.history_sha256
                or other.generation_id!=product.generation_id
                or [m.patient_id for m in other.cohort]!=patients):
            raise ValueError('paired_N_purposes_require_identical_ordered_cohort_and_Hstar')
        if other.request.context.seed.replicate==product.request.context.seed.replicate:
            raise ValueError('distinct_recorded_N_fit_seed_required')
    if active_overlap(db,patients):raise ValueError('one_or_more_N_members_already_pending')
    if payload['previous_attempt']:
        old=db.execute('SELECT * FROM analysis_attempts WHERE job_id=? AND owner_id=?',
            (payload['previous_attempt'],current['account_id'])).fetchone()
        if old is None or old['status'] in ('queued','running'):raise ValueError('finished_owned_N_attempt_required')
        previous=frozen(old)
        if (previous.target_id!=product.target_id or previous.cohort_id!=product.cohort_id
                or previous.generation_id!=product.generation_id
                or [m.patient_id for m in previous.cohort]!=patients):
            raise ValueError('previous_N_target_cohort_generation_mismatch')
    job=product.attempt_id;value=product.model_dump(mode='json')
    # The explicit real target is the FK anchor, never the first sorted member.
    db.execute('INSERT INTO pending_work VALUES(?,?,?,?)',(job,product.target_id,'queued','N analysis queued'))
    db.execute('INSERT INTO analysis_attempts(job_id,patient_id,owner_id,previous_attempt,request_json,input_sha256,history_sha256,cutoff,configuration_json,cohort_json,status,stage,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
        (job,product.target_id,current['account_id'],payload['previous_attempt'],canonical(value),sha(value),
         product.history_sha256,timestamp(product.cutoff),canonical(CONFIG_REFS[product.purpose]),
         canonical(patients),'queued','queued',timestamp(now)))
    response=view(db.execute('SELECT * FROM analysis_attempts WHERE job_id=?',(job,)).fetchone(),verified=True)
    db.execute('INSERT INTO receipts VALUES(?,?,?,?,?,?)',(current['account_id'],current['token_hash'],key,
        scope,sha(payload),canonical(response)))
    return response


def queued_request(db,*,owner,job,key,submission,now):
    payload=NSubmission.model_validate_json(canonical(submission)).model_dump(mode='json')
    receipts=db.execute('SELECT * FROM receipts WHERE owner_id=? AND key=?',(owner,key)).fetchall()
    if (len(receipts)!=1 or receipts[0]['scope']!='nof1-analysis:'+payload['target_id']
            or receipts[0]['payload_sha256']!=sha(payload) or json.loads(receipts[0]['response']).get('id')!=job):
        raise ValueError('exact_N_submission_receipt_required')
    row=db.execute('SELECT * FROM analysis_attempts WHERE owner_id=? AND job_id=?',(owner,job)).fetchone()
    if row is None or row['status']!='queued' or row['claim_token'] or row['started_at']:
        raise ValueError('owned_unclaimed_N_queue_required')
    product=revalidate(db,row,now=now)
    if submission_for(product,row['previous_attempt'])!=payload:raise ValueError('N_export_selection_changed')
    active=[dict(r) for r in db.execute("SELECT job_id,status FROM analysis_attempts WHERE status IN ('queued','running') ORDER BY job_id")]
    if active!=[dict(job_id=job,status='queued')]:raise ValueError('one_exact_reviewed_queued_N_attempt_required')
    return dict(schema='nof1-queued-request-v1',attempt_id=job,owner_id=owner,input_sha256=row['input_sha256'],
        input=product.model_dump(mode='json'),submission=payload,
        receipt=dict(key=key,scope=receipts[0]['scope'],payload_sha256=receipts[0]['payload_sha256'],
            response_sha256=sha(json.loads(receipts[0]['response']))),
        active_attempts=[dict(attempt_id=job,status='queued')])
