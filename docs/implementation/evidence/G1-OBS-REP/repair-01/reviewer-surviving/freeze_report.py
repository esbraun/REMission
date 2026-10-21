import pathlib,hashlib,subprocess,json
root=pathlib.Path.cwd();out=root/'.review-artifacts';items={}
for p in sorted(out.rglob('*')):
 if not p.is_file() or 'https-clone' in p.parts or '__pycache__' in p.parts or p.name=='artifact-manifest.json':continue
 raw=p.read_bytes();blob=subprocess.check_output(['git','hash-object','-w','--no-filters',str(p)],cwd=root).decode().strip()
 items[p.relative_to(out).as_posix()]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'git_blob':blob}
m={'head':'ceb5a5fc786f487045fd948986bc4bb8b8a43bf4','base':'6bc8bd998e8a0baaef9884998e740665fb5fd7b1','disposition':'changes_requested','files':items,'limitations':'Four original concurrent capture records were overwritten; see full report. No full all-attempt preservation claim.'}
p=out/'artifact-manifest.json';p.write_text(json.dumps(m,indent=2)+'\n',encoding='utf8')
print('REPORT',items['review-report.md']);print('MANIFEST',subprocess.check_output(['git','hash-object','-w','--no-filters',str(p)],cwd=root).decode().strip(),hashlib.sha256(p.read_bytes()).hexdigest(),'FILES',len(items))
