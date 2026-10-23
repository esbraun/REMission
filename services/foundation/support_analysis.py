"""Authenticated archive-cohort command adapters. Never imports numerical code."""
import json
import uuid

from contracts.domain.analysis import canonical, sha
from contracts.domain.support_s1 import (S1Input,S1Result,S1Submission,CONFIG_REF,
    MODEL_REF,S1_ESTIMAND,WCLS_PRIOR_REF,LAW_REF,SUPPORT_REF,validate_result)
from .store import timestamp, instant
from .support_archive import read_support_history, MODE


def authority_for(archive, configured):
    from contracts.runs.support_research import SupportArchiveAuthority
    receipt=json.loads(archive['receipt'])
    matches=[a for raw,_root,a in (configured or {}).values()
        if type(a) is SupportArchiveAuthority and sha_bytes(raw)==archive['export_sha256']
        and a.admission_sha256==receipt.get('admission_sha256')]
    if len(matches)!=1:raise ValueError('one_configured_support_qualification_required')
    return matches[0]


def sha_bytes(raw):
    import hashlib
    return hashlib.sha256(raw).hexdigest()


def prepare(db,owner,submission,configured,*,attempt_id):
    submission=S1Submission.model_validate_json(canonical(submission))
    archive=db.execute('SELECT * FROM observed_archives WHERE id=? AND owner_id=? AND mode=?',
        (submission.archive_id,owner,MODE)).fetchone()
    if archive is None:raise ValueError('owned_support_archive_required')
    authority=authority_for(archive,configured)
    if authority.qualification_scope!='accepted_saved_producer':
        raise ValueError('accepted_saved_support_producer_required_for_estimation')
    index=authority.descriptor;members=[];histories=[]
    for patient in sorted(index.members):
        value=read_support_history(db,owner,patient,submission.archive_id,'S1',submission.cutoff_day,authority)
        history=value['projection'];histories.append(history)
        row=db.execute('SELECT version FROM patients WHERE id=? AND owner_id=?',(patient,owner)).fetchone()
        members.append(dict(patient_id=patient,patient_version=row['version'],partition_id=value['partition_id'],
            projection_sha256=value['projection_sha256'],history_sha256=sha(history)))
    receipt=json.loads(archive['receipt'])
    identity=dict(owner_id=owner,archive_id=submission.archive_id,run_id=index.run_id,cohort_id=index.cohort_id,
        manifest_sha256=receipt['manifest_sha256'],admission_sha256=receipt['admission_sha256'],
        source_commit=receipt['source_commit'],producer_runtime=receipt['runtime'],
        producer_qualification=receipt['producer_qualification'],outcome_qualification=receipt['outcome_qualification'])
    return S1Input.model_validate_json(canonical(dict(schema_version='3.0.0',synthetic=True,
        kind='poc_support_s1_input',purpose='S1-WCLS',attempt_id=attempt_id,archive=identity,
        mode='S1',cutoff_day=submission.cutoff_day,cutoff=histories[0]['cutoff'],cohort=members,
        histories=histories,history_sha256=sha(histories),configuration=CONFIG_REF,model=MODEL_REF,
        prior=WCLS_PRIOR_REF,estimand=S1_ESTIMAND,law=LAW_REF,protocol=SUPPORT_REF,
        provenance_seed='fit/wcls-unused-provenance/'+attempt_id)))


def submission_for(product,previous=None):
    return dict(archive_id=product.archive.archive_id,mode='S1',cutoff_day=product.cutoff_day,
        configuration=CONFIG_REF,previous_attempt=previous)


def revalidate(db,row,configured):
    product=S1Input.model_validate_json(row['request_json'])
    if (row['owner_id']!=product.archive.owner_id or row['patient_id']!=product.cohort[0].patient_id
            or json.loads(row['cohort_json'])!=[m.patient_id for m in product.cohort]
            or sha(product.model_dump(mode='json'))!=row['input_sha256']
            or product.history_sha256!=row['history_sha256']
            or json.loads(row['configuration_json'])!=CONFIG_REF
            or timestamp(product.cutoff)!=timestamp(instant(row['cutoff']))):
        raise ValueError('stored_S1_attempt_binding_changed')
    rebuilt=prepare(db,row['owner_id'],submission_for(product),configured,attempt_id=product.attempt_id)
    if rebuilt!=product:raise ValueError('owned_S1_member_version_or_same_version_history_changed')
    return product


def submit(db,current,key,payload,configured,*,now):
    from .cohort_analysis import active_overlap
    payload=S1Submission.model_validate_json(canonical(payload)).model_dump(mode='json')
    if not key or len(key)>128:raise ValueError('bounded_stable_receipt_key_required')
    scope='support-s1:'+payload['archive_id']
    prior=db.execute('SELECT * FROM receipts WHERE owner_id=? AND session_id=? AND key=?',
        (current['account_id'],current['token_hash'],key)).fetchone()
    if prior:
        if prior['scope']!=scope or prior['payload_sha256']!=sha(payload):raise ValueError('receipt_content_conflict')
        saved=json.loads(prior['response'])
        row=db.execute('SELECT * FROM analysis_attempts WHERE job_id=? AND owner_id=?',
            (saved['id'],current['account_id'])).fetchone()
        if row is None:raise ValueError('original_S1_receipted_attempt_unavailable')
        return owned_view(db,row,configured)
    product=prepare(db,current['account_id'],payload,configured,attempt_id='analysis-'+uuid.uuid4().hex)
    patients=[m.patient_id for m in product.cohort]
    if active_overlap(db,patients):raise ValueError('cohort_analysis_already_pending')
    if payload['previous_attempt']:
        old=db.execute('SELECT * FROM analysis_attempts WHERE job_id=? AND owner_id=?',
            (payload['previous_attempt'],current['account_id'])).fetchone()
        if old is None or old['status'] in ('queued','running'):raise ValueError('finished_owned_previous_S1_attempt_required')
        previous=S1Input.model_validate_json(old['request_json'])
        if previous.archive!=product.archive:raise ValueError('previous_S1_archive_mismatch')
    job=product.attempt_id;frozen=product.model_dump(mode='json')
    db.execute('INSERT INTO pending_work VALUES(?,?,?,?)',(job,patients[0],'queued','Cohort S1 WCLS queued'))
    db.execute('INSERT INTO analysis_attempts(job_id,patient_id,owner_id,previous_attempt,request_json,input_sha256,history_sha256,cutoff,configuration_json,cohort_json,status,stage,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
        (job,patients[0],current['account_id'],payload['previous_attempt'],canonical(frozen),sha(frozen),
         product.history_sha256,timestamp(product.cutoff),canonical(CONFIG_REF),canonical(patients),'queued','queued',timestamp(now)))
    response=view(db.execute('SELECT * FROM analysis_attempts WHERE job_id=?',(job,)).fetchone(),verified=product)
    db.execute('INSERT INTO receipts VALUES(?,?,?,?,?,?)',(current['account_id'],current['token_hash'],key,scope,sha(payload),canonical(response)))
    return response


def view(row,*,verified=None,error=None):
    from .appointment import public_summary
    product=S1Input.model_validate_json(row['request_json']);result=None;result_error=None
    if row['result_json']:
        try:
            result=S1Result.model_validate_json(row['result_json'])
            validate_result(result,product,json.loads(row['progress_json']).get('trusted_launch'))
            if result.status!=row['status']:raise ValueError('stored S1 status mismatch')
        except (ValueError,KeyError,TypeError):result=None;result_error='stored_S1_summary_unaccepted'
    stale=verified is None;reason=error or ('current_archive_unverified' if stale else None)
    available=result is not None and result.status=='completed' and not stale
    return public_summary(dict(id=row['job_id'],kind='support_s1_analysis',patient_id=row['patient_id'],
        archive_id=product.archive.archive_id,cohort_id=product.archive.cohort_id,member_count=12,
        mode='S1',cutoff_day=product.cutoff_day,cutoff=row['cutoff'],status=row['status'],stage=row['stage'],
        stale=stale,staleness_reason=reason,configuration=CONFIG_REF,cohort=[m.patient_id for m in product.cohort],
        created_at=row['created_at'],started_at=row['started_at'],finished_at=row['finished_at'],
        previous_attempt=row['previous_attempt'],failure_reason=row['failure_reason'],
        result=result.model_dump(mode='json') if result is not None and not stale else None,
        input_sha256=row['input_sha256'],history_sha256=row['history_sha256'],
        serving=dict(status='current' if available else 'dated' if stale else row['status'],
            summary_available=available,reason=result_error or reason,data_through=row['cutoff'],
            published_at=row['finished_at'],artifact_generated_at=result.generated_at.isoformat() if result else None,
            summary_source='validated_stored_result_json',supported_pair=['support_prompt','no_prompt'],
            policy='historical_cohort_excursion_only')))


def owned_view(db,row,configured):
    try:product=revalidate(db,row,configured)
    except ValueError as error:return view(row,error=str(error))
    return view(row,verified=product)


def queued_request(db,*,owner,job,key,submission,configured):
    payload=S1Submission.model_validate_json(canonical(submission)).model_dump(mode='json')
    receipts=db.execute('SELECT * FROM receipts WHERE owner_id=? AND key=?',(owner,key)).fetchall()
    if (len(receipts)!=1 or receipts[0]['scope']!='support-s1:'+payload['archive_id']
            or receipts[0]['payload_sha256']!=sha(payload) or json.loads(receipts[0]['response']).get('id')!=job):
        raise ValueError('exact_S1_submission_receipt_required')
    row=db.execute('SELECT * FROM analysis_attempts WHERE owner_id=? AND job_id=?',(owner,job)).fetchone()
    if row is None or row['status']!='queued' or row['claim_token'] or row['started_at']:
        raise ValueError('owned_unclaimed_S1_queue_required')
    product=revalidate(db,row,configured)
    if submission_for(product,row['previous_attempt'])!=payload:raise ValueError('S1_export_selection_changed')
    active=[dict(r) for r in db.execute("SELECT job_id,status FROM analysis_attempts WHERE status IN ('queued','running') ORDER BY job_id")]
    if active!=[dict(job_id=job,status='queued')]:raise ValueError('one_exact_reviewed_queued_S1_attempt_required')
    return dict(schema='support-s1-queued-request-v1',attempt_id=job,owner_id=owner,input_sha256=row['input_sha256'],
        input=product.model_dump(mode='json'),submission=payload,
        receipt=dict(key=key,scope=receipts[0]['scope'],payload_sha256=receipts[0]['payload_sha256'],
            response_sha256=sha(json.loads(receipts[0]['response']))),active_attempts=[dict(attempt_id=job,status='queued')])
