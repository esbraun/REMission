import hashlib,json,shutil,sys
from pathlib import Path
sys.path.insert(0,str(Path('tooling/foundation').resolve()))
from capture import run
from analysis_dispatcher import CONTAINER_FORMAT

root=Path('artifacts/p2/final-runtime-75fc');root.mkdir(parents=True,exist_ok=False)
deployment=json.loads(Path('artifacts/p2/browser-refresh-75fc/deployment.json').read_bytes())
def command(argv):
    p,m=run(argv,root/'commands',timeout_seconds=60)
    if p.returncode:raise RuntimeError('retained runtime proof failure '+m['streams']['stderr']['path'])
    return p.stdout.decode().strip()
service=deployment['service_container']
states={role:json.loads(command(['docker','inspect',deployment[role+'_container'],'--format',CONTAINER_FORMAT])) for role in ('service','generator')}
assert states['service']['Image']=='sha256:d73c2919b5f09c09d1326489fb310f2c337d8cf9502848c89380115a8c882383'
assert all(s['State']['Running'] for s in states.values())
(root/'selected-states.json').write_text(json.dumps(states,indent=2)+'\n')
script=r'''
import json,sqlite3,hashlib
db=sqlite3.connect('file:/data/remission.sqlite?mode=ro',uri=True);db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
result={}
for patient_id in ('POC-4df6f3408ae54d7e94499e1a216f11f6','POC-0c2108192c914968b995c25bfa364fe7'):
 p=db.execute('SELECT owner_id,state_json FROM patients WHERE id=?',(patient_id,)).fetchone();state=json.loads(p['state_json']);sim=state['simulation'];loop=sim['nof1']
 rows=list(db.execute('SELECT rowid,kind,payload FROM events WHERE patient_id=?',(patient_id,)));records=[json.loads(r['payload']) for r in rows]
 medication=[r for r in records if r['kind']=='delivery' and r['option'] in ('MED_A','MED_B')]
 assignments={r['record_id']:r for r in records if r['kind']=='assignment'}
 order={json.loads(r['payload'])['record_id']:r['rowid'] for r in rows}
 assert all(assignments[r['assignment_id']]['available_at']<=r['event_at'] and order[r['assignment_id']]<order[r['record_id']] for r in medication)
 bundles=list(db.execute('SELECT display,display_sha256 FROM bundles WHERE patient_id=?',(patient_id,)))
 assert all(hashlib.sha256(b['display'].encode()).hexdigest()==b['display_sha256'] for b in bundles)
 result[patient_id]=dict(owner=p['owner_id'],day=sim['day'],status=loop['status'],phase=loop.get('phase'),draws=len(loop['draws']),reviews=loop['reviews'],
  observed_reports=sum(r['kind']=='daily_report' and r['missingness']=='observed' for r in records),missing_reports=sum(r['kind']=='daily_report' and r['missingness']!='observed' for r in records),
  medication_deliveries=len(medication),taken=sum(r['stage']=='taken' for r in medication),not_taken=sum(r['stage']=='not_taken' for r in medication),
  draw_before_delivery=True,full_distributions=[d['probabilities'] for d in loop['draws']],seed_namespace=sorted({d['seed']['namespace'] for d in loop['draws']}),
  history_bundles=len(bundles),history_bytes_hashes_valid=True,hold=bool(state['workflow']['hold_reasons']),draw_audit_count=sum('nof1_block_draw' in r[0] for r in db.execute('SELECT payload FROM state_changes WHERE patient_id=?',(patient_id,))))
result['analysis_attempts']=db.execute('SELECT COUNT(*) FROM analysis_attempts').fetchone()[0];result['query_only']=db.execute('PRAGMA query_only').fetchone()[0];result['total_changes']=db.total_changes
assert result['POC-4df6f3408ae54d7e94499e1a216f11f6']['draws']==8 and result['POC-4df6f3408ae54d7e94499e1a216f11f6']['medication_deliveries']==56
assert result['POC-0c2108192c914968b995c25bfa364fe7']['draws']==0 and result['POC-0c2108192c914968b995c25bfa364fe7']['hold']
assert result['analysis_attempts']==0 and result['query_only']==1 and result['total_changes']==0
db.rollback();db.close();print(json.dumps(result,sort_keys=True))
'''
database=json.loads(command(['docker','exec',service,'python','-c',script]))
(root/'readonly-public-counts.json').write_text(json.dumps(database,indent=2,sort_keys=True)+'\n')
shutil.copyfile('artifacts/p2/start-browser-stack-9b73.py',root/'actual-start-helper.py')
shutil.copyfile('artifacts/p2/refresh-browser-75fc.py',root/'actual-refresh-helper.py')
shutil.copyfile('artifacts/p2/browser-stack-9b73/deployment.json',root/'initial-deployment.json')
shutil.copyfile('artifacts/p2/browser-refresh-75fc/deployment.json',root/'actual-final-deployment.json')
shutil.copyfile(__file__,root/'helper.py')
files={str(p.relative_to(root)).replace('\\','/'):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(root.rglob('*')) if p.is_file()}
(root/'raw-manifest.json').write_text(json.dumps(files,indent=2,sort_keys=True)+'\n')
print(json.dumps(database,sort_keys=True))
