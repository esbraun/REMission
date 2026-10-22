import json,sys
from pathlib import Path
sys.path.insert(0,str(Path('tooling/foundation').resolve()))
from capture import run
from analysis_dispatcher import CONTAINER_FORMAT
root=Path('artifacts/cohort/final-ui-custody-r1');root.mkdir(exist_ok=False)
state=json.loads(Path('artifacts/cohort/service-ui-r4/deployment.json').read_text())
def command(argv):
    p,m=run(argv,root/'commands',timeout_seconds=60)
    assert p.returncode==0,m['streams']
    return p.stdout.decode().strip()
expected=json.loads(Path('docs/implementation/poc-cohort-role-source-inventory-20261022.json').read_text())['roles']['service']
code="import hashlib,importlib.util,json,os,sys;from pathlib import Path;expected="+repr(expected)+";assert {p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in expected}==expected;import services.foundation.app;assert 'pymc' not in sys.modules;assert not Path('/app/services/generator').exists();assert importlib.util.find_spec('services.learner') is None;assets={p.relative_to('/app/web/dist').as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/app/web/dist').rglob('*') if p.is_file()};assert 'assets/index-CDzDUbGt.js' in assets;print(json.dumps(dict(uid=os.getuid(),source_files=len(expected),assets=assets)))"
identifier=command(['docker','create','--name','remission-cohort-sol-final-service-custody-r1','--network','none','--cpus','2','--memory','2g',
    '--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=256m',state['images']['service'],'python','-c',code])
actual=json.loads(command(['docker','start','--attach',identifier]))
(root/'image-custody.json').write_text(json.dumps(actual,indent=2)+'\n')
(root/'probe-terminal.json').write_text(command(['docker','inspect',identifier,'--format',CONTAINER_FORMAT])+'\n')
readonly="""import json,os,sqlite3
p='/data/remission.sqlite';db=sqlite3.connect('file:'+p+'?mode=ro',uri=True);db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
counts={table:db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ['patients','events','bundles','analysis_attempts']}
cohort_receipts=db.execute("SELECT COUNT(*) FROM receipts WHERE scope LIKE 'cohort-analysis:%'").fetchone()[0]
assert counts['analysis_attempts']==0 and cohort_receipts==0
value=dict(device=os.stat(p).st_dev,inode=os.stat(p).st_ino,lock_inode=os.stat(p+'.admission.lock').st_ino,counts=counts,cohort_receipts=cohort_receipts,query_only=db.execute('PRAGMA query_only').fetchone()[0],total_changes=db.total_changes)
db.rollback();print(json.dumps(value))
"""
database=json.loads(command(['docker','exec',state['service_container'],'python','-c',readonly]))
assert database['device']==2096 and database['inode']==551159 and database['lock_inode']==551160
(root/'owned-db-public-counts.json').write_text(json.dumps(database,indent=2)+'\n')
for role in ('service','generator'):
    (root/(role+'-selected-state.json')).write_text(command(['docker','inspect',state[role+'_container'],'--format',CONTAINER_FORMAT])+'\n')
(root/'health.json').write_text(command(['docker','exec',state['service_container'],'python','-c',"import json,urllib.request;print(json.dumps(json.load(urllib.request.urlopen('http://127.0.0.1:8765/health',timeout=2))))"])+'\n')
print(json.dumps(dict(source_files=actual['source_files'],assets=len(actual['assets']),owned_db=database)),flush=True)
