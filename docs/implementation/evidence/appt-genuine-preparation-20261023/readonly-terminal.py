
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
control=db.execute('SELECT database_instance_id,authority_generation,database_device,database_inode,lock_device,lock_inode FROM service_control WHERE singleton=1').fetchone()
stats={}
for label,p in [('database',path),('lock',Path(str(path)+'.admission.lock'))]:
 s=p.stat();stats[label]={'device':s.st_dev,'inode':s.st_ino,'bytes':s.st_size,'uid':s.st_uid,'gid':s.st_gid}
control=dict(control);checks['authority_file_identity']=(control['database_device'],control['database_inode'],control['lock_device'],control['lock_inode'])==(stats['database']['device'],stats['database']['inode'],stats['lock']['device'],stats['lock']['inode'])
out={'database_mode':'uri mode=ro; query_only=ON; explicit read transaction; no immutable/WAL bypass','query_only':db.execute('PRAGMA query_only').fetchone()[0],'total_changes':db.total_changes,'schema_versions':[r[0] for r in db.execute('SELECT version FROM schema_migrations ORDER BY version')],'journal_mode':db.execute('PRAGMA journal_mode').fetchone()[0],'database_control':control,'file_identities':stats,'protected_tables':protected,'queue':queue,'running':running,'attempt_checks':checks,'attempt':{'id':attempt,'patient_id':row['patient_id'],'canonical_input_sha256':actual,'request_row_utf8_sha256':hashlib.sha256(row['request_json'].encode()).hexdigest(),'history_sha256':row['history_sha256'],'current_projection_sha256':sha(projected),'cutoff':row['cutoff'],'configuration':product['request']['configuration'],'numerical_seeds':product['numerical_seeds'],'source_set_sha256':product['source_set_sha256'],'immutable_identity_sha256':sha({k:row[k] for k in ['job_id','patient_id','owner_id','previous_attempt','request_json','input_sha256','history_sha256','cutoff','configuration_json','cohort_json','created_at']})},'receipt_identities':receipts,'panel':{'seed':json.loads(patient['state_json'])['simulation']['seed'],'index':json.loads(patient['state_json'])['simulation']['index'],'day':json.loads(patient['state_json'])['simulation']['day']}}

EXPECTED_CONTROL={'authority_generation': 1, 'database_device': 2096, 'database_inode': 541605, 'database_instance_id': 'e4924957-b4df-4d83-b013-72e123e13a28', 'lock_device': 2096, 'lock_inode': 541606}
EXPECTED_RESULT='850ffce701dd32587bf2b8cc2abd8121a574b4dddc16a8910b261fc4ceb6faa1'
EXPECTED_TRUSTED='c0a6a9fe0792b946ed66d8115ca031365e136d23f8e0d0527676acb68b6c9204'
EXPECTED_ATTEMPT='2fd91171e2d521c6396f44608bdd737e70257c1e07bfc8d7c1724602cb8fe7d5'

result=json.loads(row['result_json']) if row['result_json'] else None
trusted=json.loads(row['progress_json']).get('trusted_launch')
out['terminal_attempt']={'id':row['job_id'],'patient_id':row['patient_id'],'status':row['status'],'stage':row['stage'],'started_at':row['started_at'],'finished_at':row['finished_at'],'failure_reason':row['failure_reason'],'result_status':result['status'] if result else None,'result_canonical_sha256':sha(result) if result else None,'trusted_launch_sha256':sha(trusted),'owner_matches_expected':row['owner_id']==patient['owner_id']=='alice'}
control_all=dict(db.execute('SELECT * FROM service_control WHERE singleton=1').fetchone())
out['control_clock_at']=control_all.pop('last_receipt_at')
out['control_except_clock_sha256']=sha(control_all)
out.pop('panel')
out['attempt'].pop('numerical_seeds')
out.pop('receipt_identities')
assert out['database_control']==EXPECTED_CONTROL
assert out['terminal_attempt']['owner_matches_expected']
assert row['status']=='completed' and row['stage']=='complete' and result['status']=='completed'
assert sha(result)==EXPECTED_RESULT
assert sha(trusted)==EXPECTED_TRUSTED
assert out['attempt']['immutable_identity_sha256']==EXPECTED_ATTEMPT
assert actual==row['input_sha256']=='3761da9e876d3830106e5edc47a7b5b930764f934facc95c8b6328b84e65e5a2'
assert sha(projected)==row['history_sha256']=='ce5a5a2bbf99405d2457654791f3ac9a263f669770b075ac1dfa1cff0f4ac00c'
assert not out['queue'] and not out['running']
assert out['query_only']==1 and out['total_changes']==0

db.rollback();db.close();print(canonical(out))
