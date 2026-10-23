"""Owned, frozen analysis attempts and guarded result ingestion. Never fits here."""
import hashlib
import json
import os
from pathlib import Path
import secrets
import tempfile
import uuid

from contracts.domain.analysis import (AnalysisInput, AnalysisResult, CONFIG_REF, ESTIMAND_REF,
    MODEL_REF, PRIOR_REF, PROTOCOL_REF, project_history, make_input, sha)
from contracts.domain.borrowing import (BORROW_CONFIG_REF,TAU2_CONFIG_REF,BorrowAnalysisResult,
    make_borrow_input,parse_result)
from .store import canonical, timestamp, instant
from .workflow import history


class AnalysisError(ValueError):
    pass


def export_cohort(db, owner, patient_versions, cutoff, *, cohort_id, research_run_id=None):
    """CORE export inside the caller's transaction; no private state leaves it.

    Membership is resolved against owned rows and their persisted panel ID.
    Research membership resolves only from trusted run-export registration;
    a caller-provided string never authorizes research mixing.
    """
    from contracts.domain.cohort import CohortHistory, CohortManifest, COORDINATE_REF
    from .cohort_registration import registration, is_research_member
    if research_run_id is not None:
        try:
            cohort=registration(db,owner,research_run_id,cohort_id,cutoff)
        except ValueError as error:
            raise AnalysisError(str(error)) from error
        if patient_versions!={m.patient_id:m.patient_version for m in cohort.manifest.members}:
            raise AnalysisError('Registered research-run roster/version mismatch.')
        for member in cohort.manifest.members:
            row=db.execute('SELECT owner_id,version,cutoff FROM patients WHERE id=?',(member.patient_id,)).fetchone()
            if (row is None or row['owner_id']!=owner or row['version']!=member.patient_version
                    or instant(row['cutoff'])<cohort.manifest.cutoff):
                raise AnalysisError('Registered research member changed or is unavailable.')
        return cohort
    if len(patient_versions) != 12:
        raise AnalysisError('Select exactly twelve distinct owned patients.')
    histories, members, panels = [], [], set()
    cutoff = instant(cutoff)
    for patient_id in sorted(patient_versions):
        row = db.execute('SELECT * FROM patients WHERE id=? AND owner_id=?', (patient_id, owner)).fetchone()
        if row is None:
            raise AnalysisError('Cohort member unavailable for this owner.')
        if row['version'] != patient_versions[patient_id]:
            raise AnalysisError('Cohort member changed. Refresh the whole manifest.')
        simulation = json.loads(row['state_json']).get('simulation', {})
        if simulation.get('law_version') != 'poc-longitudinal-v1' or 'panel_id' not in simulation:
            raise AnalysisError('Every cohort member must use the compatible v1 panel.')
        if simulation.get('research_run_id') is not None or is_research_member(db,patient_id):
            raise AnalysisError('Research members require registered run membership; interactive export rejected.')
        if cutoff > instant(row['cutoff']):
            raise AnalysisError('Every cohort member must have reached the common cutoff.')
        panels.add(simulation['panel_id'])
        reduced = project_history(history(db, patient_id).project(cutoff))
        if (reduced.cutoff-reduced.origin).days < 14:
            raise AnalysisError('Every cohort member requires at least day14.')
        value = reduced.model_dump(mode='json')
        histories.append(value)
        members.append(dict(patient_id=patient_id, patient_version=row['version'], history_sha256=sha(value),
            provenance_sha256=sha([r.model_dump(mode='json') for r in reduced.provenance])))
    if len(panels) != 1:
        raise AnalysisError('Cohort members must belong to one persisted owned panel.')
    manifest = dict(schema='poc-cohort-manifest-v1/1.0.0', cohort_id=cohort_id, owner_id=owner,
        panel_id=next(iter(panels)), scope='interactive', research_run_id=None, cutoff=cutoff.isoformat(),
        origin=histories[0]['origin'], protocol=PROTOCOL_REF, coordinates=COORDINATE_REF, members=members)
    manifest = CohortManifest.model_validate_json(canonical(manifest)).model_dump(mode='json')
    return CohortHistory.model_validate_json(canonical(dict(schema='poc-cohort-history-v1/1.0.0',
        manifest=manifest, manifest_sha256=sha(manifest), histories=histories)))


def prepare_cohort(db, owner, patient_versions, cutoff, *, cohort_id, source_bundle_id=None, research_run_id=None):
    """Freeze reviewable input without enqueueing an unqualified native job."""
    from contracts.domain.cohort import make_cohort_input
    cohort = export_cohort(db, owner, patient_versions, cutoff, cohort_id=cohort_id, research_run_id=research_run_id)
    sources = None
    if source_bundle_id is not None:
        from .analysis_sources import load_source
        sources = load_source(source_bundle_id, cohort.manifest.cutoff)
    return make_cohort_input(cohort, 'analysis-'+uuid.uuid4().hex, sources)


def view(row, cutoff, *, current=None):
    if json.loads(row['request_json']).get('kind')=='poc_support_s1_input':
        from .support_analysis import view as support_view
        return support_view(row)
    if json.loads(row['request_json']).get('kind')=='poc_visit_cohort_input':
        from .cohort_analysis import view as cohort_view
        return cohort_view(row,cutoff)
    frozen=json.loads(row['request_json']);h=frozen['history'];day=(instant(h['cutoff'])-instant(h['origin'])).days
    from .appointment import checked_result, metadata, public_summary
    stale=instant(row['cutoff']) != instant(cutoff)
    reason='observation_cutoff_changed' if stale else None
    if current is None:
        stale=True;reason='current_history_unverified'
    elif current['reason']:
        stale=True;reason=current['reason']
    elif current['history_sha256']!=row['history_sha256']:
        stale=True;reason=reason or 'same_cutoff_history_or_lineage_changed'
    result,result_error=checked_result(row)
    return dict(id=row['job_id'],kind='visit_analysis',patient_id=row['patient_id'],status=row['status'],stage=row['stage'],
        cutoff=row['cutoff'],stale=stale,staleness_reason=reason,configuration=json.loads(row['configuration_json']),
        cohort=json.loads(row['cohort_json']),previous_attempt=row['previous_attempt'],created_at=row['created_at'],
        started_at=row['started_at'],finished_at=row['finished_at'],failure_reason=public_summary(row['failure_reason']),
        progress=public_summary(json.loads(row['progress_json'])),result=result,
        serving=metadata(row,stale=stale,reason=reason,result=result,result_error=result_error,current=current),
        input_sha256=row['input_sha256'],history_sha256=row['history_sha256'],sources=frozen.get('sources'),
        source_set_sha256=frozen.get('source_set_sha256'),cutoff_day=day,forecast_endpoint_day=day+42,
        recall_first_night=day+29,recall_last_night=day+42)


def submit(db, patient, owner, expected_version, previous, now, *, mode='v0',source_bundle_id=None):
    state=json.loads(patient['state_json'])
    if 'simulation' not in state or state['simulation']['law_version'] != 'poc-longitudinal-v1':
        raise AnalysisError('Generate a v1 synthetic patient before analysis.')
    if patient['version'] != expected_version:
        raise AnalysisError('Patient changed. Refresh before submitting a new analysis.')
    if state['simulation']['day'] < 14:
        raise AnalysisError('Advance to at least day14 before fitting this representative.')
    if previous:
        old=db.execute('SELECT * FROM analysis_attempts WHERE job_id=? AND patient_id=? AND owner_id=?',(previous,patient['id'],owner)).fetchone()
        if old is None or old['status'] in ('queued','running'):
            raise AnalysisError('Retry requires a finished owned attempt.')
    from .cohort_analysis import active_overlap
    if active_overlap(db,[patient['id']]):
        raise AnalysisError('An analysis is already pending for this patient.')
    reduced=project_history(history(db,patient['id']).project(instant(patient['cutoff'])))
    value=reduced.model_dump(mode='json')
    job='analysis-'+uuid.uuid4().hex
    if mode=='v0':
        if source_bundle_id is not None:raise AnalysisError('V0 cannot include external sources.')
        product=make_input(reduced,job,secrets.randbelow(2147483647))
    else:
        from .analysis_sources import load_source
        if mode not in ('borrow','tau2') or source_bundle_id is None:raise AnalysisError('Choose an approved source bundle for borrowing.')
        sources=load_source(source_bundle_id,reduced.cutoff)
        product=make_borrow_input(reduced,job,sources,TAU2_CONFIG_REF if mode=='tau2' else BORROW_CONFIG_REF)
    frozen=product.model_dump(mode='json')
    db.execute('INSERT INTO pending_work VALUES(?,?,?,?)',(job,patient['id'],'queued','Visit analysis queued'))
    db.execute('INSERT INTO analysis_attempts(job_id,patient_id,owner_id,previous_attempt,request_json,input_sha256,history_sha256,cutoff,configuration_json,cohort_json,status,stage,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
        (job,patient['id'],owner,previous,canonical(frozen),sha(frozen),sha(value),patient['cutoff'],canonical(product.request.configuration.model_dump()),canonical([patient['id']]),'queued','queued',timestamp(now)))
    return view(db.execute('SELECT * FROM analysis_attempts WHERE job_id=?',(job,)).fetchone(),patient['cutoff'])


def queued_request(db, *, owner, job, key, submission, configured=None):
    """Read one receipted ordinary cohort request; no claim/session secrets leave.

    The caller uses the existing admitted Store read transaction. A missing
    receipt is UNKNOWN submission outcome, never permission to submit again.
    """
    if 'archive_id' in submission:
        from .support_analysis import queued_request as support_queued
        return support_queued(db,owner=owner,job=job,key=key,submission=submission,configured=configured)
    from contracts.domain.cohort import CohortInput, CohortSubmission, require_executable
    submission=CohortSubmission.model_validate_json(canonical(submission)).model_dump(mode='json')
    if not key or len(key)>128:raise AnalysisError('Bounded original receipt key required.')
    receipts=db.execute('SELECT scope,payload_sha256,response FROM receipts WHERE owner_id=? AND key=?',
        (owner,key)).fetchall()
    if len(receipts)!=1:raise AnalysisError('Unknown or ambiguous submission receipt; retain original key.')
    receipt=receipts[0];scope='cohort-analysis:'+submission['cohort_id']
    if receipt['scope']!=scope or receipt['payload_sha256']!=sha(submission):
        raise AnalysisError('Submission receipt selection mismatch.')
    response=json.loads(receipt['response'])
    if response.get('id')!=job:raise AnalysisError('Submission receipt job mismatch.')
    active=db.execute("SELECT job_id,status FROM analysis_attempts WHERE status IN ('queued','running') ORDER BY job_id").fetchall()
    if [(r['job_id'],r['status']) for r in active]!=[(job,'queued')]:
        raise AnalysisError('Expected exactly the one reviewed queued attempt and no running attempt.')
    row=db.execute('SELECT * FROM analysis_attempts WHERE job_id=? AND owner_id=?',(job,owner)).fetchone()
    if row is None or row['claim_token'] is not None or row['started_at'] is not None:
        raise AnalysisError('Expected owned unclaimed queued attempt.')
    product=CohortInput.model_validate_json(row['request_json']);require_executable(product)
    frozen=product.model_dump(mode='json');manifest=product.cohort.manifest
    if (product.attempt_id!=job or sha(frozen)!=row['input_sha256'] or manifest.owner_id!=owner
            or product.cohort.manifest_sha256!=submission['approved_manifest_sha256']
            or manifest.cohort_id!=submission['cohort_id'] or timestamp(manifest.cutoff)!=timestamp(instant(submission['cutoff']))
            or manifest.research_run_id!=submission['research_run_id']
            or {m.patient_id:m.patient_version for m in manifest.members}!=submission['patient_versions']
            or submission['source_bundle_id'] is not None or product.sources is not None
            or row['previous_attempt']!=submission['previous_attempt']):
        raise AnalysisError('Frozen queued request differs from approved submission.')
    # Rebuild through the existing public projection and ownership path. This
    # detects version, cutoff, lineage or same-version H* changes before claim.
    current=prepare_cohort(db,owner,submission['patient_versions'],submission['cutoff'],
        cohort_id=submission['cohort_id'],research_run_id=submission['research_run_id'])
    if current.cohort_sha256!=product.cohort_sha256:
        raise AnalysisError('Current owned cohort changed since submission.')
    return dict(schema='ordinary-queued-request-v1',attempt_id=job,owner_id=owner,
        input_sha256=row['input_sha256'],input=frozen,submission=submission,
        receipt=dict(key=key,scope=scope,payload_sha256=receipt['payload_sha256'],response_sha256=sha(response)),
        active_attempts=[dict(attempt_id=job,status='queued')])


def export_queued_request(store, *, configured=None, **selection):
    with store.transaction() as db:
        return queued_request(db,configured=configured,**selection)


def claim(store, *, expected=None, configured=None):
    with store.transaction(write=True) as db:
        if expected is not None:
            proof=queued_request(db,configured=configured,**expected['selection'])
            if sha(proof)!=expected['export_sha256']:
                raise AnalysisError('Reviewed queued export changed before claim.')
        if db.execute("SELECT 1 FROM analysis_attempts WHERE status='running'").fetchone():
            return None
        row=db.execute("SELECT * FROM analysis_attempts WHERE status='queued' ORDER BY created_at,job_id LIMIT 1").fetchone()
        if row is None:
            return None
        product=json.loads(row['request_json'])
        if product.get('kind')=='poc_support_s1_input':
            from .support_analysis import revalidate
            revalidate(db,row,configured)
        if product.get('kind')=='poc_visit_cohort_input':
            from contracts.domain.cohort import CohortInput,require_executable
            require_executable(CohortInput.model_validate_json(row['request_json']))
        if product.get('kind')=='poc_protocol_input':
            from contracts.domain.protocol_request import ProtocolInput,require_executable
            require_executable(ProtocolInput.model_validate_json(row['request_json']))
        token=secrets.token_hex(24)
        db.execute("UPDATE analysis_attempts SET status='running',stage='preparing',claim_token=?,started_at=? WHERE job_id=? AND status='queued'",(token,timestamp(store.clock()),row['job_id']))
        db.execute("UPDATE pending_work SET status='running',reason='Visit analysis preparing' WHERE id=?",(row['job_id'],))
        return dict(attempt_id=row['job_id'],claim_token=token,input=json.loads(row['request_json']))


def running(db, job, token):
    row=db.execute('SELECT * FROM analysis_attempts WHERE job_id=?',(job,)).fetchone()
    if row is None or row['status'] != 'running' or not secrets.compare_digest(row['claim_token'] or '',token):
        raise AnalysisError('Stale or unclaimed worker; result not ingested.')
    return row


def progress(store, job, token, value):
    stages=['preparing','fitting','diagnostics','rollouts']
    if set(value)-{'attempt_id','input_sha256','stage','extension','K','checks'} or value.get('stage') not in stages:
        raise AnalysisError('Invalid progress envelope')
    with store.transaction(write=True) as db:
        row=running(db,job,token)
        if value.get('attempt_id')!=job or value.get('input_sha256')!=row['input_sha256']:
            raise AnalysisError('Progress identity mismatch')
        persisted=dict(value)
        trusted=json.loads(row['progress_json']).get('trusted_launch')
        if trusted is not None:persisted['trusted_launch']=trusted
        db.execute('UPDATE analysis_attempts SET stage=?,progress_json=? WHERE job_id=?',(value['stage'],canonical(persisted),job))
        db.execute('UPDATE pending_work SET reason=? WHERE id=?',('Visit analysis '+value['stage'],job))


def bind_execution(store,job,token,origin, *, configured=None):
    """Host CLI only, before launch. The isolated learner never receives token."""
    from contracts.domain.borrowing import parse_input,BorrowAnalysisInput
    from contracts.domain.borrow_runtime import runtime_origin,execution_binding
    if set(origin)!={'learner_image','source_commit'}:raise AnalysisError('Invalid host launch fields')
    try:runtime_origin(origin['learner_image'],origin['source_commit'])
    except ValueError as error:raise AnalysisError('Invalid trusted host origin') from error
    with store.transaction(write=True) as db:
        row=running(db,job,token);product=parse_input(row['request_json'])
        if product.kind=='poc_support_s1_input':
            from .support_analysis import revalidate
            from contracts.domain.support_s1 import execution_binding as support_binding
            revalidate(db,row,configured)
            binding=support_binding(product,origin)
        elif product.kind=='poc_visit_cohort_input':
            from contracts.domain.cohort import require_executable
            from contracts.domain.cohort_runtime import execution_binding as cohort_binding
            require_executable(product)
            binding=cohort_binding(product,origin)
        elif not isinstance(product,BorrowAnalysisInput):
            raise AnalysisError('V0 does not select borrowing execution binding')
        else:binding=execution_binding(product,origin)
        saved=json.loads(row['progress_json']);previous=saved.get('trusted_launch')
        if previous is None and row['stage']!='preparing':raise AnalysisError('Host launch must be frozen before fitting')
        if previous is not None and previous!=binding:raise AnalysisError('Immutable host launch already bound')
        saved['trusted_launch']=binding
        db.execute('UPDATE analysis_attempts SET progress_json=? WHERE job_id=?',(canonical(saved),job))
    return binding


def fail(store, job, token, reason):
    with store.transaction(write=True) as db:
        running(db,job,token)
        db.execute("UPDATE analysis_attempts SET status='failed',stage='failed',failure_reason=?,finished_at=? WHERE job_id=?",(reason[:1000],timestamp(store.clock()),job))
        db.execute("UPDATE pending_work SET status='failed',reason=? WHERE id=?",(reason[:1000],job))


def interrupt(store):
    """Dispatcher startup only, after supervisor stops all preceding learner jobs."""
    with store.transaction(write=True) as db:
        rows=db.execute("SELECT job_id FROM analysis_attempts WHERE status='running'").fetchall()
        for row in rows:
            db.execute("UPDATE analysis_attempts SET status='failed',stage='failed',failure_reason='dispatcher-restarted; interrupted attempt retained',finished_at=? WHERE job_id=?",(timestamp(store.clock()),row[0]))
            db.execute("UPDATE pending_work SET status='failed',reason='Analysis interrupted by dispatcher restart' WHERE id=?",(row[0],))
    return len(rows)


def ingest(store,job,token,directory, *, accept_before=None, configured=None):
    def within_host_deadline(db):
        if accept_before is not None and store.clock()>=instant(accept_before):
            raise AnalysisError('Host absolute completion deadline exceeded before commit.')
    directory=Path(directory)
    if directory.is_symlink():
        raise AnalysisError('Invalid artifact directory')
    directory=directory.resolve(strict=True)
    result_path=directory/'result.json'
    if result_path.is_symlink() or not result_path.is_file() or result_path.stat().st_size>10*1024*1024:
        raise AnalysisError('Invalid result file')
    result=parse_result(result_path.read_bytes())
    cohort_result=result.kind=='poc_visit_cohort_result'
    support_result=result.kind=='poc_support_s1_result'
    if result.kind=='poc_protocol_result':
        from contracts.domain.protocol_request import require_executable
        require_executable(result)
    # Validate output files BEFORE acquiring the SQLite writer lock.
    names=set()
    for ref in result.artifacts:
        if set(ref)!={'path','sha256'} or Path(ref['path']).name != ref['path'] or ref['path'] in names:
            raise AnalysisError('Invalid artifact reference')
        names.add(ref['path'])
        path=directory/ref['path']
        if path.is_symlink() or not path.is_file() or path.stat().st_size>1024**3:
            raise AnalysisError('Invalid artifact file')
        h=hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda:stream.read(1024*1024),b''):
                h.update(chunk)
        if h.hexdigest()!=ref['sha256']:
            raise AnalysisError('Artifact hash mismatch')
    if result.status=='completed' and not cohort_result and not support_result:
        d=result.diagnostics
        if not d.get('fits') or not d['fits'][-1]['diagnostics'].get('accepted') or not d.get('effect_mcmc',{}).get('accepted') or d.get('integration',{}).get('status')!='accepted' or 'expected-effect.npz' not in names:
            raise AnalysisError('Completed result lacks accepted computational diagnostics')
        if isinstance(result,BorrowAnalysisResult) and (d.get('bridge_precision',{}).get('status')!='accepted' or not {'bridge-precision.json','bridge-marginals.npz'}<=names):
            raise AnalysisError('Completed borrowing result lacks accepted bridge precision')
    with store.transaction(write=True,before_commit=within_host_deadline) as db:
        row=running(db,job,token)
        if support_result:
            from .support_analysis import revalidate
            from contracts.domain.support_s1 import validate_result
            product=revalidate(db,row,configured)
            validate_result(result,product,json.loads(row['progress_json']).get('trusted_launch'))
            if names!={'wcls.json'}:raise AnalysisError('S1 requires exactly its full WCLS JSON artifact')
            artifact=json.loads((directory/'wcls.json').read_bytes())
            if artifact!=result.diagnostics:raise AnalysisError('S1 artifact/summary diagnostics mismatch')
        elif cohort_result:
            from contracts.domain.cohort import CohortInput,require_executable
            require_executable(CohortInput.model_validate_json(row['request_json']))
            from .cohort_analysis import validate_result
            validate_result(result,row,names)
        elif (result.attempt_id!=job or result.input_sha256!=row['input_sha256'] or result.history_sha256!=row['history_sha256']
            or result.cutoff!=instant(row['cutoff']) or result.configuration.model_dump()!=json.loads(row['configuration_json'])):
            raise AnalysisError('Frozen result identity/hash/cutoff mismatch')
        source_hash=json.loads(row['request_json']).get('source_set_sha256')
        if source_hash!=getattr(result,'source_set_sha256',None):raise AnalysisError('Frozen result source hash mismatch')
        if isinstance(result,BorrowAnalysisResult) and result.status=='completed':
            from contracts.domain.borrowing import parse_input
            from contracts.domain.borrow_runtime import validate_execution
            try:validate_execution(result.diagnostics.get('execution',{}),parse_input(row['request_json']),json.loads(row['progress_json']).get('trusted_launch'))
            except ValueError as error:raise AnalysisError('Completed borrowing result lacks qualified execution binding') from error
        frozen_result=result.model_dump_json()
        completed_at=store.clock()
        if accept_before is not None and completed_at>=instant(accept_before):
            raise AnalysisError('Host absolute completion deadline exceeded after validation.')
        if support_result and result.status=='completed':
            if row['started_at'] is None or not instant(row['started_at'])<=result.generated_at<=completed_at:
                raise AnalysisError('S1 generation time must lie within authoritative execution times.')
            if not 0<=(completed_at-instant(row['started_at'])).total_seconds()<180:
                raise AnalysisError('S1 completion exceeds persisted lifecycle bound.')
        if cohort_result and result.status=='completed':
            if row['started_at'] is None:
                raise AnalysisError('Cohort completion lacks authoritative start time.')
            elapsed=(completed_at-instant(row['started_at'])).total_seconds()
            if not 0<=elapsed<7200:
                raise AnalysisError('Cohort completion exceeds persisted claim deadline.')
        db.execute('UPDATE analysis_attempts SET status=?,stage=?,failure_reason=?,result_json=?,artifact_root=?,finished_at=? WHERE job_id=?',
            (result.status,'complete' if result.status=='completed' else result.status,result.reason,frozen_result,str(directory),timestamp(completed_at),job))
        db.execute('UPDATE pending_work SET status=?,reason=? WHERE id=?',(result.status,result.reason or 'Visit analysis complete',job))
    return dict(id=job,status=result.status)


def comparison_root(root,owner,patient):
    if root is None:raise AnalysisError('Comparison artifact storage is unavailable.')
    return Path(root)/'comparisons'/sha([owner,patient])


def compare(db,patient,owner,left,right,root):
    if left==right:raise AnalysisError('Choose two distinct V0/V1 attempts.')
    rows=[db.execute('SELECT * FROM analysis_attempts WHERE job_id=? AND owner_id=? AND (patient_id=? OR EXISTS(SELECT 1 FROM json_each(cohort_json) WHERE value=?))',(job,owner,patient,patient)).fetchone() for job in (left,right)]
    if any(row is None for row in rows):raise AnalysisError('Comparison attempt is unavailable.')
    if any(row['status'] in ('queued','running') for row in rows):raise AnalysisError('Both attempts must finish before freezing a comparison.')
    from .appointment import checked_result
    if any(checked_result(row)[1] for row in rows):
        raise AnalysisError('Stored comparison summary is incompatible or unaccepted.')
    inputs=[json.loads(row['request_json']) for row in rows]
    if any(p.get('kind')=='poc_visit_cohort_input' for p in inputs):
        if not all(p.get('kind')=='poc_visit_cohort_input' for p in inputs):
            raise AnalysisError('Cannot pair a cohort posterior with a single-patient fit.')
        from .cohort_analysis import comparison
        manifest=comparison(rows)
        anchor=min(m['patient_id'] for m in manifest['manifest']['members'])
        manifest.update(patient_id=anchor,owner_id=owner)
        return publish_comparison(manifest,root,owner,anchor)
    contexts=[v['request']['context'] for v in inputs]
    if len({row['history_sha256'] for row in rows})!=1 or len({row['cutoff'] for row in rows})!=1:
        raise AnalysisError('Pairing requires identical patient H* and observation cutoff.')
    for key in ('estimand','comparator_estimand','protocol'):
        if contexts[0][key]!=contexts[1][key]:raise AnalysisError('Pairing requires the same protocol and target.')
    configs=[json.loads(row['configuration_json']) for row in rows]
    if sorted(c['id']=='poc-visit-v1' for c in configs)!=[False,True] or any(c['id'] not in ('poc-visit-v1','poc-visit-borrow-v1','poc-visit-borrow-tau2-v1') for c in configs):
        raise AnalysisError('This comparison pairs V0 with a production V1 configuration.')
    if contexts[0]['seed']==contexts[1]['seed'] or contexts[0]['seed']['replicate']==contexts[1]['seed']['replicate']:
        raise AnalysisError('Comparison requires distinct recorded fit seeds.')
    attempts=[]
    for row in rows:
        value=view(row,row['cutoff']);result=value['result']
        effect=result['effect'] if result else None
        attempts.append(dict(id=row['job_id'],configuration=value['configuration'],input_sha256=value['input_sha256'],
            status=value['status'],failure_reason=value['failure_reason'],effect=effect,
            published_at=row['finished_at'],data_through=row['cutoff'],
            interval_width=effect['upper']-effect['lower'] if effect else None,
            worker_seconds=result['diagnostics'].get('seconds') if result else None,
            sources=value['sources'],source_set_sha256=value['source_set_sha256']))
    manifest=dict(schema_version='1.0.0',kind='poc_v0_v1_comparison',synthetic=True,patient_id=patient,owner_id=owner,
        cutoff=rows[0]['cutoff'],history_sha256=rows[0]['history_sha256'],estimand=contexts[0]['estimand'],protocol=contexts[0]['protocol'],
        attempts=attempts,fit_seeds=[ctx['seed'] for ctx in contexts],
        limitations=['Same H*/cutoff, distinct original-prior fits; source studies contribute once only in V1.',
            'Estimates, interval widths and observed latency only; PA6 independent conditional truth and accuracy are unavailable.',
            'No beneficial direction or clinical superiority is required or established.'])
    return publish_comparison(manifest,root,owner,patient)


def publish_comparison(manifest,root,owner,patient):
    identifier='comparison-'+sha(manifest);manifest['id']=identifier
    destination=comparison_root(root,owner,patient);destination.mkdir(parents=True,exist_ok=True)
    path=destination/(identifier+'.json');encoded=canonical(manifest)+'\n'
    if path.is_symlink():raise AnalysisError('Invalid comparison artifact.')
    descriptor,temporary=tempfile.mkstemp(prefix='.comparison-',suffix='.partial',dir=destination)
    try:
        with os.fdopen(descriptor,'w',encoding='utf-8',newline='\n') as stream:
            stream.write(encoded);stream.flush();os.fsync(stream.fileno())
        try:
            # Link only complete bytes, atomically and without overwriting an
            # immutable artifact published by an earlier successful request.
            os.link(temporary,path)
        except FileExistsError:
            if path.is_symlink() or path.read_text(encoding='utf-8')!=encoded:
                raise AnalysisError('Frozen comparison checksum changed.')
    finally:
        Path(temporary).unlink(missing_ok=True)
    return manifest


def comparisons(root,owner,patient):
    destination=comparison_root(root,owner,patient)
    if not destination.exists():return []
    results=[]
    for path in sorted(destination.glob('comparison-*.json')):
        if path.is_symlink() or path.stat().st_size>1024*1024:raise AnalysisError('Invalid comparison artifact.')
        value=json.loads(path.read_bytes());identifier=value.pop('id',None)
        if identifier!='comparison-'+sha(value) or value.get('patient_id')!=patient or value.get('owner_id')!=owner:
            raise AnalysisError('Comparison artifact identity mismatch.')
        value['id']=identifier;results.append(value)
    return results
