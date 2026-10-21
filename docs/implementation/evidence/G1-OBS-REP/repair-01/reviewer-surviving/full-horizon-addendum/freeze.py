from pathlib import Path
import json,subprocess,hashlib
root=Path.cwd();out=root/'.review-artifacts/complete-horizon-addendum';paths=set()
for p in out.iterdir():
 if p.is_file() and p.name!='artifact-manifest.json':paths.add(p)
for folder in [out/'wire',out/'complete-attempt-002/wire']:
 m=json.loads((folder/'manifest.json').read_bytes())
 paths.update([folder/'manifest.json',folder/'authority.json'])
 for part in m['partitions']:
  refs=[part['history'],part['replay'],part['coverage'],*part['stage_ledgers'],*part['completion_receipts'],*part['mechanisms']]
  for a in refs:
   p=folder/a['path'];b=p.read_bytes();assert len(b)==a['bytes'] and hashlib.sha256(b).hexdigest()==a['sha256'];paths.add(p)
paths.add(out/'complete-attempt-002/independent-calendar.json')
items={}
for p in sorted(paths):
 b=p.read_bytes();blob=subprocess.check_output(['git','hash-object','-w','--no-filters',str(p)],cwd=root).decode().strip()
 items[p.relative_to(out).as_posix()]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob':blob}
p=out/'artifact-manifest.json';p.write_text(json.dumps({'head':'ceb5a5fc786f487045fd948986bc4bb8b8a43bf4','base':'6bc8bd998e8a0baaef9884998e740665fb5fd7b1','result':'complete-public-wire-positive-pass','candidate_disposition':'changes_requested','files':items},indent=2)+'\n',encoding='utf8')
print('ADDENDUM',items['addendum.md']);print('PROBE',items['attempt-002.probe.py']);print('COMMAND',items['attempt-002.json']);print('STDOUT',items['attempt-002.stdout']);print('MANIFEST',subprocess.check_output(['git','hash-object','-w','--no-filters',str(p)],cwd=root).decode().strip(),'FILES',len(items))
