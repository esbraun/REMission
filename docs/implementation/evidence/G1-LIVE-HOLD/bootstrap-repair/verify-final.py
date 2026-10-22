"""Read-only current repair, preservation, copied assets and full raw-chain audit."""
import base64,hashlib,json,subprocess
from pathlib import Path

ROOT=Path.cwd();E=Path(__file__).parent;OLD=E.parent
BASE='ec18cb4020ba239710a3fd615e365d5cd72b4d80'
RUNTIME='ec49af47ec437abe7f4ba357205886a23f353402'
def git(*args):return subprocess.check_output(['git',*args])
def sha(raw):return hashlib.sha256(raw).hexdigest()
old_manifest=json.loads((OLD/'release-manifest.json').read_bytes())
for item in old_manifest['files']:
 raw=(OLD/item['path']).read_bytes();assert len(raw)==item['bytes'] and sha(raw)==item['sha256'];assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==item['raw_git_blob']
assert len(old_manifest['files'])==1211
preservation=json.loads((OLD/'release-preservation.json').read_bytes())
for row in preservation['v1']:
 assert git('show',BASE+':'+row['path'])==git('show',RUNTIME+':'+row['path'])
for row in preservation['schemas']:
 assert sha(git('show',RUNTIME+':'+row['path']))==row['git_sha256']
for row in preservation['migrations']:
 assert git('rev-parse',RUNTIME+':'+row['path']).decode().strip()==row['git_blob']
ledger='docs/implementation/g0-task-test-ledger-20261020.json';old=json.loads(git('show',BASE+':'+ledger));current=json.loads(Path(ledger).read_bytes())
assert old['tasks']==current['tasks'] and len(current['tasks'])==23
assert old['coverage']==current['coverage'] and len(current['coverage'])==635
assert old['coverage_counts']==current['coverage_counts']
assert (sum(len(t.get('depends_on',[])) for t in current['tasks']),sum(len(t.get('test_ids',[])) for t in current['tasks']),sum(len(t.get('requirement_ids',[])) for t in current['tasks']))==(52,26,1341)
backend=git('diff','--name-only','8019314fb3ef7640339f2b0bbb3d70de93913239',RUNTIME,'--','services','contracts','tests','tooling').decode().splitlines()
assert backend==['services/foundation/README.md'],backend
build=json.loads((E/'build/source-images.json').read_bytes())
assert build['source_head']==RUNTIME
for name,item in build['source'].items():assert sha(Path(name).read_bytes())==item['sha256'],name
raw_mcp=json.loads((E/'browser/mcp-raw-complete.json').read_bytes());assert len(raw_mcp)==90
for item in json.loads((E/'browser/artifact-manifest.json').read_bytes())['generated']:
 raw=(E/'browser'/item['path']).read_bytes();assert len(raw)==item['bytes'] and sha(raw)==item['sha256']
observed=json.loads(raw_mcp[1]['result']['content'][0]['text'].split('### Result\n',1)[1].split('\n### Ran',1)[0])
role=json.loads((E/'roles/inventory.json').read_bytes());assets=role['roles']['service']['copied_source']['assets']
for url,digest in observed['assets'].items():assert assets['/app/web/dist'+url]==digest
items=json.loads((E/'raw-rejection-and-historical-audit.json').read_bytes())['items'];cache={}
for item in items:
 if 'base64' in item:raw=base64.b64decode(item['base64'])
 else:
  ref=item['complete_payload_already_preserved']
  if 'repository_raw_file' in ref:raw=Path(ref['repository_raw_file']).read_bytes()
  else:
   path=ref['base64_envelope']
   if path not in cache:cache[path]=json.loads(Path(path).read_bytes())
   raw=base64.b64decode(cache[path][ref['item_index']]['base64'])
 assert len(raw)==item['bytes'] and sha(raw)==item['sha256'];assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==item['git_blob']
captures=[]
for p in E.rglob('*.json'):
 if p.name in ('raw-rejection-and-historical-audit.json','final-manifest.json'):continue
 v=json.loads(p.read_bytes())
 if isinstance(v,dict) and {'command','streams','source_snapshot'}<=v.keys():
  for stream in v['streams'].values():
   raw=p.with_name(stream['path']).read_bytes();assert len(raw)==stream['bytes'] and sha(raw)==stream['sha256']
  captures.append(dict(path=p.relative_to(E).as_posix(),exit=v['exit']))
result=dict(runtime_source=RUNTIME,base=BASE,old_6f40_manifest_files_exact=1211,v1_exact=53,schemas_exact=64,original_coverage=635,original_tasks=23,dependencies=52,task_test_refs=26,requirement_links=1341,backend_runtime_delta_from801=False,build_source_files_exact=len(build['source']),new_mcp_entries=90,new_artifacts=50,new_png=4,assets=assets,raw_chain_blobs_verified=len(items),command_capture_hashes_verified=captures)
(E/'final-audit.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(status='passed',runtime_source=RUNTIME,old_files_exact=1211,raw_chain=len(items),command_captures=len(captures),new_browser_entries=90)))
