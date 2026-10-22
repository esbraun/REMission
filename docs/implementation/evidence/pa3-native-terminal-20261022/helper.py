import hashlib,json,shutil,sys
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path('tooling/foundation').resolve()))
from capture import run
from analysis_dispatcher import CONTAINER_FORMAT
from audit_pa3_native_readiness import SQL_AUDIT

root=Path('artifacts/pa3/native-terminal-r1-3c6');root.mkdir(parents=True,exist_ok=False)
package=Path('artifacts/pa3/native-launch-3c6');job=package/'analysis-jobs/analysis-4ff86193058d4d13a1600f0423e91f12'
deployment=json.loads((package/'deployment.json').read_bytes());manifest=json.loads((job/'dispatch.json').read_bytes())
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)
def sha(v):return hashlib.sha256(canonical(v).encode()).hexdigest()
def command(argv):
    p,m=run(argv,root/'commands',timeout_seconds=60)
    if p.returncode:raise RuntimeError('terminal custody failure retained '+m['streams']['stderr']['path'])
    return p.stdout
def save(name,v):(root/name).write_text(json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+'\n')
actual=json.loads(command(['docker','inspect',manifest['container'],'--format',CONTAINER_FORMAT]))
assert not actual['State']['Running'] and actual['State']['ExitCode']==0 and not actual['State']['OOMKilled']
assert actual['Id']=='93cf67b550a31198b070dafebf2140d64651cfc4b8ac76f777f26ae519f0059b'
assert actual['Image']==manifest['learner_image']=='sha256:9d2e601f926ae644a041903b076fdb33ff3885be1a0f390137bc61ff461584e1'
assert manifest['status']=='completed' and manifest['finished_unix']-manifest['started_unix']<7200
save('worker-terminal-selected.json',actual)
states={role:json.loads(command(['docker','inspect',deployment[role+'_container'],'--format',CONTAINER_FORMAT])) for role in ('service','generator')}
assert all(s['State']['Running'] for s in states.values())
assert states['service']['Image']=='sha256:bad33f377d97f52572e182d0973b1f1f56dbc3f1c413de48f20b0458e0906fb7'
assert states['generator']['Image']=='sha256:5d546abd1448e46d5d45ac4a3d98c31899631f968f93d21b163797ff0674ded9'
save('original-stack-selected.json',states)
shutil.copytree(job,root/'job')
for name in ('runtime-dispatcher.stdout','runtime-dispatcher.stderr'):
    if (package/name).exists():shutil.copyfile(package/name,root/name)
command(['docker','cp',manifest['container']+':/output',str(root/'worker-output')])
command(['docker','cp',manifest['container']+':/input/input.json',str(root/'worker-input.json')])
for path in (root/'job/output').rglob('*'):
    if path.is_file() and path.name not in ("worker.stdout","worker.stderr"):assert path.read_bytes()==(root/"worker-output"/path.relative_to(root/"job/output")).read_bytes()
for name in ("worker.stdout","worker.stderr"):
    assert (root/"job"/name).read_bytes()==(root/"job/output"/name).read_bytes()
assert sha(json.loads((root/'worker-input.json').read_bytes()))==manifest['input_sha256']=='3761da9e876d3830106e5edc47a7b5b930764f934facc95c8b6328b84e65e5a2'
result=json.loads((job/'output/result.json').read_bytes());diagnostics=json.loads((job/'output/diagnostics.json').read_bytes())
for artifact in result['artifacts']:
    assert hashlib.sha256((job/'output'/artifact['path']).read_bytes()).hexdigest()==artifact['sha256']
extra=r'''
result=json.loads(row['result_json']) if row['result_json'] else None
artifact_checks=[]
if result:
 for a in result['artifacts']:
  f=Path(row['artifact_root'])/a['path'];artifact_checks.append({'path':a['path'],'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'matches':hashlib.sha256(f.read_bytes()).hexdigest()==a['sha256']})
out['terminal_attempt']={'id':row['job_id'],'patient_id':row['patient_id'],'status':row['status'],'stage':row['stage'],'started_at':row['started_at'],'finished_at':row['finished_at'],'failure_reason':row['failure_reason'],'result_status':result['status'] if result else None,'result_canonical_sha256':sha(result) if result else None,'artifact_root':row['artifact_root'],'artifact_checks':artifact_checks,'trusted_launch':json.loads(row['progress_json']).get('trusted_launch')}
out['pending_work']=[dict(r) for r in db.execute('SELECT id,status,reason FROM pending_work WHERE id=?',(attempt,))]
'''
script=SQL_AUDIT.replace('db.rollback();db.close();print(canonical(out))',extra+'\ndb.rollback();db.close();print(canonical(out))')
database=json.loads(command(['docker','exec',deployment['service_container'],'python','-c',script]))
save('terminal-database-readonly.json',database)
assert database['query_only']==1 and database['total_changes']==0
assert database['terminal_attempt']['status']=='completed' and database['terminal_attempt']['stage']=='complete'
assert database['terminal_attempt']['result_canonical_sha256']==sha(result)
assert all(a['matches'] for a in database['terminal_attempt']['artifact_checks'])
assert database['terminal_attempt']['trusted_launch']==manifest['trusted_launch']
before=json.loads(Path('artifacts/pa3/native-job-launch-witness-3c6/fresh-protected-target.json').read_bytes())
changed=[table for table,value in before['protected_tables'].items() if database['protected_tables'][table]!=value]
assert set(changed)<= {'analysis_attempts','pending_work','service_control'}
assert database['database_control']==before['database_control']
assert database['attempt']==before['attempt'] and database['receipt_identities']==before['receipt_identities']
assert not database['queue'] and not database['running']
fit=diagnostics['fits'][0]['diagnostics']
summary=dict(observed_utc=datetime.now(timezone.utc).isoformat(),unified_exec_session_id=25783,owner_poll_exit_code=0,
    original_attempt=manifest['attempt_id'],source_commit=manifest['source_head'],learner_image=manifest['learner_image'],
    host_dispatcher_origin='55c07c8ac15d5b55d4d7acdff273570422cd3b01',host_dispatcher_sha256=hashlib.sha256((package/'analysis_dispatcher.py').read_bytes()).hexdigest(),
    actual_worker_id=actual['Id'],worker_finished_at=actual['State']['FinishedAt'],dispatcher_elapsed_wall_seconds=manifest['finished_unix']-manifest['started_unix'],
    watchdog_seconds=7200,worker_seconds=diagnostics['seconds'],service_status=database['terminal_attempt']['status'],service_result_status=database['terminal_attempt']['result_status'],
    service_and_worker_results_exact=True,artifact_count=len(result['artifacts']),all_artifact_hashes_verified=True,
    clinical_protected_tables_unchanged=True,changed_tables=changed,authority_identity_same=True,original_input_identity_same=True,submission_receipt_identity_same=True,
    source_posterior_checks_accepted=fit['accepted'],fit_count=len(diagnostics['fits']),extension=diagnostics['fits'][0]['extension'],
    divergences=fit['divergences'],maximum_tree_depth=fit['maximum_tree_depth'],rhat_max=max(fit['rhat'].values()),ess_bulk_min=min(fit['ess_bulk'].values()),ess_tail_min=min(fit['ess_tail'].values()),
    effect_mcmc=diagnostics['effect_mcmc'],integration=diagnostics['integration'],effect=result['effect'],
    cgroup_peak_memory_bytes=diagnostics['cgroup_peak_memory_bytes'],process_peak_memory_kib=diagnostics['peak_memory_kib'],
    limitations=['One actual synthetic single-patient borrowing job; no full cohort/PA2/study/clinical efficacy claim.','Cgroup peak reached exact2GiB cap without OOM; memory headroom is not established.','Public interval crosses zero; no superiority claim.','Independent terminal/posterior review still required.'])
save('summary.json',summary)
shutil.copyfile(__file__,root/'helper.py')
files={str(p.relative_to(root)).replace('\\','/'):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(root.rglob('*')) if p.is_file()}
save('raw-manifest.json',dict(files=files,files_count=len(files),status='frozen; no more writes'))
print(json.dumps({k:summary[k] for k in ['actual_worker_id','service_status','service_result_status','dispatcher_elapsed_wall_seconds','divergences','rhat_max','ess_bulk_min','ess_tail_min','changed_tables','authority_identity_same','original_input_identity_same','artifact_count']},sort_keys=True))
