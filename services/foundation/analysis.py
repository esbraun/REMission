"""Owned, frozen analysis attempts and guarded result ingestion. Never fits here."""
import hashlib
import json
from pathlib import Path
import secrets
import uuid

from contracts.domain.analysis import (AnalysisInput, AnalysisResult, CONFIG_REF, ESTIMAND_REF,
    MODEL_REF, PRIOR_REF, PROTOCOL_REF, project_history, make_input, sha)
from .store import canonical, timestamp, instant
from .workflow import history


class AnalysisError(ValueError):
    pass


def view(row, cutoff):
    return dict(id=row['job_id'],kind='visit_analysis',patient_id=row['patient_id'],status=row['status'],stage=row['stage'],
        cutoff=row['cutoff'],stale=instant(row['cutoff']) != instant(cutoff),configuration=json.loads(row['configuration_json']),
        cohort=json.loads(row['cohort_json']),previous_attempt=row['previous_attempt'],created_at=row['created_at'],
        started_at=row['started_at'],finished_at=row['finished_at'],failure_reason=row['failure_reason'],
        progress=json.loads(row['progress_json']),result=json.loads(row['result_json']) if row['result_json'] else None,
        input_sha256=row['input_sha256'],history_sha256=row['history_sha256'])


def submit(db, patient, owner, expected_version, previous, now):
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
    if db.execute("SELECT 1 FROM analysis_attempts WHERE patient_id=? AND status IN ('queued','running')",(patient['id'],)).fetchone():
        raise AnalysisError('An analysis is already pending for this patient.')
    reduced=project_history(history(db,patient['id']).project(instant(patient['cutoff'])))
    value=reduced.model_dump(mode='json')
    job='analysis-'+uuid.uuid4().hex
    product=make_input(reduced,job,secrets.randbelow(2147483647))
    frozen=product.model_dump(mode='json')
    db.execute('INSERT INTO pending_work VALUES(?,?,?,?)',(job,patient['id'],'queued','Visit analysis queued'))
    db.execute('INSERT INTO analysis_attempts(job_id,patient_id,owner_id,previous_attempt,request_json,input_sha256,history_sha256,cutoff,configuration_json,cohort_json,status,stage,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
        (job,patient['id'],owner,previous,canonical(frozen),sha(frozen),sha(value),patient['cutoff'],canonical(CONFIG_REF),canonical([patient['id']]),'queued','queued',timestamp(now)))
    return view(db.execute('SELECT * FROM analysis_attempts WHERE job_id=?',(job,)).fetchone(),patient['cutoff'])


def claim(store):
    with store.transaction(write=True) as db:
        if db.execute("SELECT 1 FROM analysis_attempts WHERE status='running'").fetchone():
            return None
        row=db.execute("SELECT * FROM analysis_attempts WHERE status='queued' ORDER BY created_at,job_id LIMIT 1").fetchone()
        if row is None:
            return None
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
        db.execute('UPDATE analysis_attempts SET stage=?,progress_json=? WHERE job_id=?',(value['stage'],canonical(value),job))
        db.execute('UPDATE pending_work SET reason=? WHERE id=?',('Visit analysis '+value['stage'],job))


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


def ingest(store,job,token,directory):
    directory=Path(directory)
    if directory.is_symlink():
        raise AnalysisError('Invalid artifact directory')
    directory=directory.resolve(strict=True)
    result_path=directory/'result.json'
    if result_path.is_symlink() or not result_path.is_file() or result_path.stat().st_size>10*1024*1024:
        raise AnalysisError('Invalid result file')
    result=AnalysisResult.model_validate_json(result_path.read_bytes())
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
    if result.status=='completed':
        d=result.diagnostics
        if not d.get('fits') or not d['fits'][-1]['diagnostics'].get('accepted') or not d.get('effect_mcmc',{}).get('accepted') or d.get('integration',{}).get('status')!='accepted' or 'expected-effect.npz' not in names:
            raise AnalysisError('Completed result lacks accepted computational diagnostics')
    with store.transaction(write=True) as db:
        row=running(db,job,token)
        if (result.attempt_id!=job or result.input_sha256!=row['input_sha256'] or result.history_sha256!=row['history_sha256']
            or result.cutoff!=instant(row['cutoff']) or result.configuration.model_dump()!=json.loads(row['configuration_json'])):
            raise AnalysisError('Frozen result identity/hash/cutoff mismatch')
        db.execute('UPDATE analysis_attempts SET status=?,stage=?,failure_reason=?,result_json=?,artifact_root=?,finished_at=? WHERE job_id=?',
            (result.status,'complete' if result.status=='completed' else result.status,result.reason,result.model_dump_json(),str(directory),timestamp(store.clock()),job))
        db.execute('UPDATE pending_work SET status=?,reason=? WHERE id=?',(result.status,result.reason or 'Visit analysis complete',job))
    return dict(id=job,status=result.status)
