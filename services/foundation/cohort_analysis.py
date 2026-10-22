"""Cohort operations inside the existing Store transaction and attempt tables."""
import json
import uuid

from contracts.domain.analysis import canonical, sha
from contracts.domain.cohort import CohortInput, CohortResult, require_executable
from .store import instant, timestamp


def active_overlap(db, patients):
    wanted=set(patients)
    for row in db.execute("SELECT job_id,cohort_json FROM analysis_attempts WHERE status IN ('queued','running')"):
        if wanted.intersection(json.loads(row['cohort_json'])):
            return row['job_id']
    return None


def view(row, current_cutoff, *, current_versions=None):
    product=CohortInput.model_validate_json(row['request_json'])
    manifest=product.cohort.manifest
    day=(manifest.cutoff-manifest.origin).days
    versions={m.patient_id:m.patient_version for m in manifest.members}
    stale=instant(row['cutoff'])!=instant(current_cutoff) or current_versions!=versions
    return dict(id=row['job_id'],kind='cohort_visit_analysis',patient_id=row['patient_id'],
        patient_ids=[m.patient_id for m in manifest.members],cohort=json.loads(row['cohort_json']),
        manifest=manifest.model_dump(mode='json'),manifest_sha256=product.cohort.manifest_sha256,
        cohort_sha256=product.cohort_sha256,status=row['status'],stage=row['stage'],cutoff=row['cutoff'],
        stale=stale,staleness_reason=('whole_cohort_current_versions_unverified' if current_versions is None
            else 'cohort_cutoff_or_member_version_changed' if stale else None),configuration=json.loads(row['configuration_json']),
        previous_attempt=row['previous_attempt'],created_at=row['created_at'],started_at=row['started_at'],
        finished_at=row['finished_at'],failure_reason=row['failure_reason'],progress=json.loads(row['progress_json']),
        result=json.loads(row['result_json']) if row['result_json'] else None,input_sha256=row['input_sha256'],
        history_sha256=row['history_sha256'],sources=product.sources.model_dump(mode='json') if product.sources else None,
        source_set_sha256=product.source_set_sha256,cutoff_day=day,forecast_endpoint_day=day+42,
        recall_first_night=day+29,recall_last_night=day+42)


def submit(db, owner, patient_versions, cutoff, *, cohort_id, approved_manifest_sha256,
           now, previous_attempt=None, source_bundle_id=None, research_run_id=None):
    """Caller owns Store.transaction + authenticated session/CSRF/receipt scope.

    Admission is deliberately closed until exact source/math/role qualification.
    No callback or caller flag can enable the executable configuration.
    """
    from .analysis import AnalysisError, prepare_cohort
    product=prepare_cohort(db,owner,patient_versions,cutoff,cohort_id=cohort_id,
        source_bundle_id=source_bundle_id,research_run_id=research_run_id)
    if product.cohort.manifest_sha256!=approved_manifest_sha256:
        raise AnalysisError('The reviewed full cohort manifest changed. Refresh approval.')
    if active_overlap(db,patient_versions):
        raise AnalysisError('An analysis already includes one or more cohort members.')
    if previous_attempt:
        old=db.execute('SELECT * FROM analysis_attempts WHERE job_id=? AND owner_id=?',
            (previous_attempt,owner)).fetchone()
        if old is None or old['status'] in ('queued','running') or sorted(json.loads(old['cohort_json']))!=sorted(patient_versions):
            raise AnalysisError('Retry requires a finished owned attempt for exactly this cohort.')
    require_executable(product)
    # This insertion stays behind the same closed qualification gate as claim,
    # worker entry and accepted ingest. No queue-only bypass is exposed.
    frozen=product.model_dump(mode='json');job=product.attempt_id;anchor=min(patient_versions)
    db.execute('INSERT INTO pending_work VALUES(?,?,?,?)',(job,anchor,'queued','Joint cohort analysis queued'))
    db.execute('INSERT INTO analysis_attempts(job_id,patient_id,owner_id,previous_attempt,request_json,input_sha256,history_sha256,cutoff,configuration_json,cohort_json,status,stage,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
        (job,anchor,owner,previous_attempt,canonical(frozen),sha(frozen),product.cohort_sha256,
         timestamp(product.cohort.manifest.cutoff),canonical(product.request.configuration.model_dump()),
         canonical(sorted(patient_versions)),'queued','queued',timestamp(now)))
    return view(db.execute('SELECT * FROM analysis_attempts WHERE job_id=?',(job,)).fetchone(),cutoff,current_versions=patient_versions)


def submit_receipted(db, current, key, payload, *, now):
    """Same receipt semantics as the current route, in its caller's transaction.

    `current` is obtained by the existing authenticated mutation route, never
    from the submitted payload. No new authentication scheme is introduced.
    """
    from .analysis import AnalysisError
    from contracts.domain.cohort import CohortSubmission
    payload=CohortSubmission.model_validate_json(canonical(payload)).model_dump(mode='json')
    if not key or len(key)>128:
        raise AnalysisError('Supply a bounded stable idempotency key.')
    scope='cohort-analysis:'+payload['cohort_id']
    prior=db.execute('SELECT * FROM receipts WHERE owner_id=? AND session_id=? AND key=?',
        (current['account_id'],current['token_hash'],key)).fetchone()
    if prior:
        if prior['scope']!=scope or prior['payload_sha256']!=sha(payload):
            raise AnalysisError('This key already identifies different content.')
        return json.loads(prior['response'])
    response=submit(db,current['account_id'],now=now,**payload)
    db.execute('INSERT INTO receipts VALUES(?,?,?,?,?,?)',(current['account_id'],current['token_hash'],key,
        scope,sha(payload),canonical(response)))
    return response


def validate_result(result, row, names):
    """Frozen whole-cohort input/result and every applicable patient gate."""
    from .analysis import AnalysisError
    product=CohortInput.model_validate_json(row['request_json'])
    if (result.attempt_id!=row['job_id'] or result.input_sha256!=row['input_sha256']
            or result.cohort_sha256!=product.cohort_sha256 or result.manifest!=product.cohort.manifest
            or result.manifest_sha256!=product.cohort.manifest_sha256
            or result.configuration!=product.request.configuration
            or result.source_set_sha256!=product.source_set_sha256):
        raise AnalysisError('Frozen cohort result/input/manifest/configuration/source mismatch.')
    if result.status=='completed':
        d=result.diagnostics
        from contracts.domain.cohort_runtime import validate_execution
        try:validate_execution(d.get('execution'),product,json.loads(row['progress_json']).get('trusted_launch'))
        except ValueError as error:raise AnalysisError('Completed cohort lacks qualified host/worker binding.') from error
        if not d.get('fits') or not d['fits'][-1]['diagnostics'].get('accepted'):
            raise AnalysisError('Joint fit did not pass posterior diagnostics.')
        for patient in result.patients:
            p=d.get('patients',{}).get(patient.patient_id,{})
            expected='patient-'+sha(patient.patient_id)[:16]+'-expected-effect.npz'
            if (p.get('integration',{}).get('status')!='accepted'
                    or not p.get('effect_mcmc',{}).get('accepted') or expected not in names):
                raise AnalysisError('Every cohort patient requires accepted effect gates/artifacts.')
        if product.sources and (d.get('bridge_precision',{}).get('status')!='accepted'
                or not {'bridge-precision.json','bridge-marginals.npz'}<=names):
            raise AnalysisError('Cohort source bridge did not pass once for the shared posterior.')


def comparison(rows):
    """One joint-cohort pair; retain patient effects rather than averaging them."""
    from .analysis import AnalysisError
    inputs=[CohortInput.model_validate_json(r['request_json']) for r in rows]
    a,b=inputs
    if (a.cohort!=b.cohort or a.cohort_sha256!=b.cohort_sha256
            or a.request.context.estimand!=b.request.context.estimand
            or a.request.context.protocol!=b.request.context.protocol
            or bool(a.sources)==bool(b.sources) or a.numerical_seeds.nuts==b.numerical_seeds.nuts):
        raise AnalysisError('Cohort comparison requires identical H*/membership/cutoff, V0/V1 and distinct seeds.')
    return dict(schema_version='3.0.0',kind='poc_cohort_v0_v1_comparison',synthetic=True,
        manifest=a.cohort.manifest.model_dump(mode='json'),manifest_sha256=a.cohort.manifest_sha256,
        cohort_sha256=a.cohort_sha256,cutoff=timestamp(a.cohort.manifest.cutoff),
        attempts=[dict(id=r['job_id'],configuration=p.request.configuration.model_dump(),input_sha256=r['input_sha256'],
            status=r['status'],failure_reason=r['failure_reason'],
            patients=CohortResult.model_validate_json(r['result_json']).model_dump(mode='json')['patients'] if r['result_json'] else None,
            worker_seconds=json.loads(r['result_json'])['diagnostics'].get('seconds') if r['result_json'] else None,
            source_set_sha256=p.source_set_sha256,fit_seed=p.numerical_seeds.nuts) for r,p in zip(rows,inputs,strict=True)],
        limitations=['One shared joint posterior per attempt; no averaged-effect substitute.',
            'No independent conditional truth, recovery accuracy, clinical superiority or study acceptance.'])
