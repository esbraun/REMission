"""Read-only audit of the single owned 8780 app; never deploy, claim or fit."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from capture import run

SERVICE='remission-poc13-ac8e16e0-service'
GENERATOR='remission-poc13-ac8e16e0-generator'
PREFIX='remission-poc13-ac8e16e0'
TARGET_SOURCE='4a340baf63fdb0f9a6f4fb065166232dafd10ca3'
CONTAINER_FORMAT='{"Id":{{json .Id}},"Name":{{json .Name}},"Image":{{json .Image}},"State":{{json .State}},"User":{{json .Config.User}},"Mounts":{{json .Mounts}},"Networks":{{json .NetworkSettings.Networks}},"Ports":{{json .NetworkSettings.Ports}},"Memory":{{json .HostConfig.Memory}},"NanoCpus":{{json .HostConfig.NanoCpus}},"ReadonlyRootfs":{{json .HostConfig.ReadonlyRootfs}},"CapDrop":{{json .HostConfig.CapDrop}},"SecurityOpt":{{json .HostConfig.SecurityOpt}},"Tmpfs":{{json (index .HostConfig "Tmpfs")}},"RestartPolicy":{{json .HostConfig.RestartPolicy}}}'
SQL_AUDIT=r'''
import hashlib,json,os,sqlite3
from pathlib import Path
from urllib.parse import quote
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)
def sha(x):return hashlib.sha256(canonical(x).encode()).hexdigest()
path=Path(os.environ.get('REMISSION_DATABASE','/data/remission.sqlite')).resolve(strict=True)
db=sqlite3.connect('file:'+quote(str(path),safe='/')+'?mode=ro',uri=True,timeout=5)
db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
def encode(x):
 if isinstance(x,bytes):return {'blob_bytes':len(x),'blob_sha256':hashlib.sha256(x).hexdigest()}
 return x
allowed=['patients','events','decisions','bundles','tasks','receipts','ingestion_receipts','replay_runs','pending_work','drafts','state_changes','observed_archives','observed_archive_entries','observed_archive_artifacts','service_control','live_authority_history','live_activation_receipts','live_hold_operations','live_hold_episodes','live_hold_reviews','live_hold_tasks','live_hold_task_events','live_hold_keys','live_patient_journals','live_safety_facts','live_projection_receipts','live_export_receipts','live_hold_additional_tasks','live_hold_task_bindings','live_hold_additional_task_events','analysis_attempts']
tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
protected={}
for table in allowed:
 if table not in tables:continue
 info=db.execute('PRAGMA table_info("'+table+'")').fetchall()
 keys=[r['name'] for r in sorted(info,key=lambda r:r['pk']) if r['pk']]
 rows=[{k:encode(row[k]) for k in row.keys()} for row in db.execute('SELECT * FROM "'+table+'"')]
 hashes=sorted(sha(row) for row in rows)
 protected[table]={'rows':len(rows),'rows_sha256':sha(hashes),'row_hashes':hashes,'primary_key_columns':keys}
queue=[dict(r) for r in db.execute("SELECT job_id,patient_id,status,stage,created_at,input_sha256,history_sha256 FROM analysis_attempts WHERE status='queued' ORDER BY created_at,job_id")]
running=[dict(r) for r in db.execute("SELECT job_id,patient_id,status,stage,created_at,input_sha256 FROM analysis_attempts WHERE status='running' ORDER BY created_at,job_id")]
attempt='analysis-4ff86193058d4d13a1600f0423e91f12'
row=db.execute('SELECT * FROM analysis_attempts WHERE job_id=?',(attempt,)).fetchone()
assert row is not None
product=json.loads(row['request_json']);h=product['history'];patient=db.execute('SELECT * FROM patients WHERE id=?',(row['patient_id'],)).fetchone()
from services.foundation.workflow import history
from services.foundation.store import instant
from contracts.domain.analysis import project_history
projected=project_history(history(db,row['patient_id']).project(instant(patient['cutoff']))).model_dump(mode='json')
actual=sha(product)
checks={'queued':row['status']=='queued','stage_queued':row['stage']=='queued','kind_borrow':product['kind']=='poc_visit_borrow_input','canonical_input':actual==row['input_sha256']=='3761da9e876d3830106e5edc47a7b5b930764f934facc95c8b6328b84e65e5a2','history':sha(h)==row['history_sha256']=='ce5a5a2bbf99405d2457654791f3ac9a263f669770b075ac1dfa1cff0f4ac00c','current_db_projection':sha(projected)==row['history_sha256'],'cutoff':all(instant(value)==instant('2026-01-15T12:00:00Z') for value in [row['cutoff'],patient['cutoff'],h['cutoff']]),'configuration':product['request']['configuration']['sha256']=='114d69435430a98d60d1724a30ba89073efebd5ba0e1b7bdae55ddb3f3a90675','source_set':product['source_set_sha256']=='11420d1f40754021a13cd7fed1152bc824d6b669af233efe60a0dc4facec9ddb','nuts_seed':product['numerical_seeds']['nuts']==3859568062,'prior_seed':product['numerical_seeds']['prior_check']==2854342402,'effect_seed':product['numerical_seeds']['effect_rollout']==2134078996,'bridge_seed':product['numerical_seeds']['bridge_reference']==4047038903,'unclaimed':row['claim_token'] is None,'unstarted':row['started_at'] is None,'no_result':row['result_json'] is None,'oldest':bool(queue) and queue[0]['job_id']==attempt,'no_running':not running}
receipts=[]
for receipt in db.execute('SELECT * FROM receipts'):
 response=json.loads(receipt['response'])
 if isinstance(response,dict) and response.get('id')==attempt:
  receipts.append({'owner_id':receipt['owner_id'],'scope':receipt['scope'],'key_sha256':hashlib.sha256(receipt['key'].encode()).hexdigest(),'session_id_sha256':hashlib.sha256(receipt['session_id'].encode()).hexdigest(),'payload_sha256':receipt['payload_sha256'],'response_sha256':hashlib.sha256(receipt['response'].encode()).hexdigest(),'attempt_id':response['id']})
control=db.execute('SELECT database_instance_id,authority_generation,database_device,database_inode,lock_device,lock_inode FROM service_control WHERE singleton=1').fetchone()
stats={}
for label,p in [('database',path),('lock',Path(str(path)+'.admission.lock'))]:
 s=p.stat();stats[label]={'device':s.st_dev,'inode':s.st_ino,'bytes':s.st_size,'uid':s.st_uid,'gid':s.st_gid}
control=dict(control);checks['authority_file_identity']=(control['database_device'],control['database_inode'],control['lock_device'],control['lock_inode'])==(stats['database']['device'],stats['database']['inode'],stats['lock']['device'],stats['lock']['inode'])
out={'database_mode':'uri mode=ro; query_only=ON; explicit read transaction; no immutable/WAL bypass','query_only':db.execute('PRAGMA query_only').fetchone()[0],'total_changes':db.total_changes,'schema_versions':[r[0] for r in db.execute('SELECT version FROM schema_migrations ORDER BY version')],'journal_mode':db.execute('PRAGMA journal_mode').fetchone()[0],'database_control':control,'file_identities':stats,'protected_tables':protected,'queue':queue,'running':running,'attempt_checks':checks,'attempt':{'id':attempt,'patient_id':row['patient_id'],'canonical_input_sha256':actual,'request_row_utf8_sha256':hashlib.sha256(row['request_json'].encode()).hexdigest(),'history_sha256':row['history_sha256'],'current_projection_sha256':sha(projected),'cutoff':row['cutoff'],'configuration':product['request']['configuration'],'numerical_seeds':product['numerical_seeds'],'source_set_sha256':product['source_set_sha256'],'immutable_identity_sha256':sha({k:row[k] for k in ['job_id','patient_id','owner_id','previous_attempt','request_json','input_sha256','history_sha256','cutoff','configuration_json','cohort_json','created_at']})},'receipt_identities':receipts,'panel':{'seed':json.loads(patient['state_json'])['simulation']['seed'],'index':json.loads(patient['state_json'])['simulation']['index'],'day':json.loads(patient['state_json'])['simulation']['day']}}
db.rollback();db.close();print(canonical(out))
'''


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--evidence',type=Path,required=True);args=parser.parse_args()
    root=args.evidence;root.mkdir(parents=True,exist_ok=False)
    def save(name,value):(root/name).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
    def command(argv):
        p,m=run(argv,root/'commands',timeout_seconds=60)
        if p.returncode:raise RuntimeError('audit failed; retained selected stderr '+m['streams']['stderr']['path'])
        return p.stdout
    states={role:json.loads(command(['docker','inspect',name,'--format',CONTAINER_FORMAT])) for role,name in [('service',SERVICE),('generator',GENERATOR)]}
    assert states['service']['Image']=='sha256:35910f5f5d1aa579367a60bf0a6264843b6fca68a8699369c6b7e4a1b863e93e'
    assert states['generator']['Image']=='sha256:5d546abd1448e46d5d45ac4a3d98c31899631f968f93d21b163797ff0674ded9'
    save('selected-stack-states.json',states)
    # The only environment read is private in-memory. Never send this command
    # through capture.run, persist its streams, print values, or log them in argv.
    private=subprocess.run(['docker','inspect',SERVICE,'--format','{{json .Config.Env}}'],capture_output=True)
    if private.returncode:raise RuntimeError('private environment identity read failed; no streams retained')
    values=json.loads(private.stdout);mapping={entry.split('=',1)[0]:entry.split('=',1)[1] for entry in values}
    env=dict(count=len(values),canonical_sha256=hashlib.sha256(json.dumps(values,separators=(',',':')).encode()).hexdigest(),source_commit_matches_target=mapping.get('REMISSION_SOURCE_COMMIT')==TARGET_SOURCE,values_never_persisted=True)
    del mapping,values,private
    save('environment-identity-only.json',env)
    database=json.loads(command(['docker','exec',SERVICE,'python','-c',SQL_AUDIT]))
    save('protected-database-snapshot.json',database)
    worker_ids=command(['docker','ps','-aq','--filter','label=remission.analysis='+PREFIX]).decode().split()
    workers=[json.loads(command(['docker','inspect',identifier,'--format',CONTAINER_FORMAT])) for identifier in worker_ids]
    save('owned-analysis-workers.json',workers)
    prospective=Path('artifacts/pa3/app-native-4a')
    pending_name=PREFIX+'-service-pre-pa3-4a'
    existing_backup_name=command(['docker','ps','-aq','--filter','name=^/'+pending_name+'$']).decode().split()
    host=dict(prospective_deployment=str(prospective/'deployment.json'),prospective_job_directory=str(prospective/'analysis-jobs'/database['attempt']['id']),deployment_root_exists=prospective.exists(),old_dispatcher_record_present=Path('artifacts/pa3/app-8780/dispatcher.json').exists(),retained_old_service_name=pending_name,retained_name_conflict=bool(existing_backup_name),existing_prepared_manifest_sha256=hashlib.sha256(Path('artifacts/pa3/service-overlay-sanitized-bc09/deployment-prepared.json').read_bytes()).hexdigest())
    save('host-readiness.json',host)
    readiness=dict(read_only_audit=True,attempt_gates=database['attempt_checks'],all_attempt_checks=all(database['attempt_checks'].values()),no_active_owned_workers=not any(w['State']['Running'] for w in workers),new_host_job_path_free=not prospective.exists(),no_retained_name_conflict=not existing_backup_name,source_env_update_needed=not env['source_commit_matches_target'],limitations=['Point-in-time audit; recheck immediately before separately authorized maintenance/claim.','No backup, service mutation, private-env staging, claim, worker or fit performed.','No broad host-process enumeration; original deployment recorded no dispatcher and no owned analysis worker is active.'])
    save('readiness.json',readiness)
    files={str(p.relative_to(root)).replace('\\','/'):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(root.rglob('*')) if p.is_file()}
    save('raw-manifest.json',dict(files=files,files_count=len(files),status='frozen; no more writes'))
    print(json.dumps(readiness,sort_keys=True))


if __name__=='__main__':main()
