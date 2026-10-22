"""Bounded postmerge read-only evidence audit; not a repair of verify-final.py."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path.cwd();E=Path(__file__).parent;OLD=E.parent
MERGE='0e1a11faa01d267fe1cdb06d07c0c06dcc2d5b55'
BASE='ec18cb4020ba239710a3fd615e365d5cd72b4d80'
HEAD='54d0bb41cca44d3464b4547db23e6ca39edd9f0c'
def git(*args):return subprocess.check_output(['git',*args])
def sha(raw):return hashlib.sha256(raw).hexdigest()
def blob(raw):return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
assert git('show','-s','--format=%P',MERGE).decode().strip().split()==[BASE,HEAD]
assert git('rev-parse',MERGE+'^{tree}')==git('rev-parse',HEAD+'^{tree}')
historical=[]
for name,n in [('release-manifest.json',1211),('bootstrap-repair/final-manifest.json',1562)]:
    m=json.loads((OLD/name).read_bytes());assert len(m['files'])==n
    for v in m['files']:
        raw=(OLD/v['path']).read_bytes();assert len(raw)==v['bytes'] and sha(raw)==v['sha256'] and blob(raw)==v['raw_git_blob'],v['path']
        assert git('rev-parse',MERGE+':'+(OLD/v['path']).relative_to(ROOT).as_posix()).decode().strip()==v['raw_git_blob']
    historical.append(dict(manifest=name,files=n,bytes=sum(v['bytes'] for v in m['files']),sha256=sha((OLD/name).read_bytes())))
p=json.loads((OLD/'release-preservation.json').read_bytes())
for v in p['v1']:assert git('show',BASE+':'+v['path'])==git('show',MERGE+':'+v['path'])
for v in p['schemas']:assert sha(git('show',MERGE+':'+v['path']))==v['git_sha256']
for v in p['migrations']:assert git('rev-parse',MERGE+':'+v['path']).decode().strip()==v['git_blob']
ledger='docs/implementation/g0-task-test-ledger-20261020.json';a=json.loads(git('show',BASE+':'+ledger));b=json.loads(Path(ledger).read_bytes())
assert a['tasks']==b['tasks'] and a['coverage']==b['coverage'] and a['coverage_counts']==b['coverage_counts']
counts=dict(tasks=len(b['tasks']),coverage=len(b['coverage']),dependencies=sum(len(t.get('depends_on',[])) for t in b['tasks']),test_refs=sum(len(t.get('test_ids',[])) for t in b['tasks']),requirement_links=sum(len(t.get('requirement_ids',[])) for t in b['tasks']))
assert list(counts.values())==[23,635,52,26,1341]
build=json.loads((E/'build/source-images.json').read_bytes());assert build['source_head']==MERGE
for path,v in build['source'].items():
    raw=Path(path).read_bytes();assert len(raw)==v['bytes'] and sha(raw)==v['sha256'],path
review=json.loads((E/'reviewed-raw-manifest.json').read_bytes())
for v in review['items']:
    raw=Path(v['repository_raw_file']).read_bytes();assert len(raw)==v['bytes'] and sha(raw)==v['sha256'] and blob(raw)==v['git_blob']
captures=[]
for path in E.rglob('*.json'):
    if path.name in ('reviewed-raw-manifest.json','manifest.json'):continue
    try:v=json.loads(path.read_bytes())
    except ValueError:continue
    if isinstance(v,dict) and {'command','streams','source_snapshot'}<=v.keys():
        for stream in v['streams'].values():
            raw=path.with_name(stream['path']).read_bytes();assert len(raw)==stream['bytes'] and sha(raw)==stream['sha256']
        captures.append(dict(path=path.relative_to(E).as_posix(),exit=v['exit']))
value=dict(merge=MERGE,base=BASE,reviewed_head=HEAD,identical_merge_candidate_tree=True,historical=historical,v1_exact=len(p['v1']),schemas_exact=len(p['schemas']),migrations_exact=len(p['migrations']),ledger=counts,merged_build_raw_inputs_exact=len(build['source']),reviewed_raw_blobs=len(review['items']),reviewed_raw_bytes=sum(v['bytes'] for v in review['items']),capture_streams=captures,portability_debt='G7 verify-final.py remains author-byte-form dependent; original scripts and failures preserved, no repair or checkout-independent claim in this scope')
(E/'audit.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in value.items() if k!='capture_streams'}))
