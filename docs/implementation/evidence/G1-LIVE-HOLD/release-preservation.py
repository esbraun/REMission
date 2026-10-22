"""Recompute final legacy Git bytes and complete original ledger mappings."""
import hashlib,json,subprocess
from pathlib import Path

BASE='ec18cb4020ba239710a3fd615e365d5cd72b4d80'
def git(*args):return subprocess.check_output(['git',*args])
def blob(ref,path):return git('show',ref+':'+path)
head=git('rev-parse','HEAD').decode().strip()
old_inventory=json.loads(git('cat-file','blob','fb992718bde3b6bac894cdcae021d9e7092a0a53'))
rows=[]
for item in old_inventory['golden_v1']['paths']:
 path=item['path'];old=blob(BASE,path);current=blob(head,path);assert old==current
 raw=Path(path).read_bytes();rows.append(dict(path=path,git_blob=git('rev-parse',head+':'+path).decode().strip(),bytes=len(current),git_sha256=hashlib.sha256(current).hexdigest(),raw_sha256=hashlib.sha256(raw).hexdigest(),raw_equals_git=raw==current,raw_crlf_only=raw.replace(b'\r\n',b'\n')==current))
assert len(rows)==53
ledger='docs/implementation/g0-task-test-ledger-20261020.json'
old=json.loads(blob(BASE,ledger));new=json.loads(Path(ledger).read_bytes())
assert len(new['coverage'])==635 and old['coverage']==new['coverage']
assert len(new['tasks'])==23 and old['tasks']==new['tasks']
assert old['coverage_counts']==new['coverage_counts']
tasks={t['id'] for t in new['tasks']};assert all(set(r['task_ids'])<=tasks for r in new['coverage'])
edges=sum(len(t.get('depends_on',[])) for t in new['tasks']);testrefs=sum(len(t.get('test_ids',[])) for t in new['tasks']);links=sum(len(t.get('requirement_ids',[])) for t in new['tasks'])
assert (edges,testrefs,links)==(52,26,1341)
schemas=[]
for path in git('ls-tree','-r','--name-only',BASE,'contracts/domain/schemas','contracts/runs/schemas','contracts/dgp/schemas').decode().splitlines():
 oldbytes=blob(BASE,path);current=blob(head,path);assert oldbytes==current
 schemas.append(dict(path=path,git_sha256=hashlib.sha256(current).hexdigest()))
migrations=[]
for path,source in [('001_foundation.sql',BASE),('002_observed_archive.sql',BASE),('003_live_hold.sql','1096d6da86048e7a53f98ed70abdd85f6f497aed')]:
 path='services/foundation/migrations/'+path;assert blob(source,path)==blob(head,path);migrations.append(dict(path=path,git_blob=git('rev-parse',head+':'+path).decode().strip()))
spec=Path('contracts/service/spec-v1.json').read_bytes();assert hashlib.sha256(spec).hexdigest()=='a6dece1e9d0e5933f3701789e5f9a562a0fee083587a4a3e302e52e0d971f1a3'
delta=git('diff','--name-only','8019314fb3ef7640339f2b0bbb3d70de93913239',head).decode().splitlines()
assert all(p in ('services/foundation/README.md',ledger) or p.startswith('docs/implementation/evidence/G1-LIVE-HOLD/') for p in delta),delta
result=dict(base=BASE,head=head,scope='Git source preservation, original ordered ledger rows/inverse references and raw-versus-Git bytes; no runtime behavior inference',v1=rows,schemas=schemas,migrations=migrations,ledger=dict(coverage=635,tasks=23,dependencies=edges,task_test_refs=testrefs,requirement_links=links,all_original_rows_equal=True),post801_committed_delta=delta,composed_spec_sha256=hashlib.sha256(spec).hexdigest())
out=Path(__file__).with_name('release-preservation.json');out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(status='passed',head=head,v1=len(rows),schemas=len(schemas),coverage=635,tasks=23,dependencies=edges,task_test_refs=testrefs,requirement_links=links,post801_runtime_unchanged=True)))
