"""Postmerge evidence only: preserve routed independent raw chains without rewriting them."""
import hashlib,json,subprocess,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
def blob(raw):return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)

def main():
    existing={}
    scope=ROOT/'docs/implementation/evidence/G1-LIVE-HOLD'
    for p in sorted(scope.rglob('*')):
        if p.is_file() and OUT not in p.parents:
            raw=p.read_bytes();existing.setdefault(blob(raw),dict(repository_raw_file=p.relative_to(ROOT).as_posix()))
    starts=['482224','545dc','0ac6ae','d5fffea','fee78f3fadc633871b15b58819f0155e02549e29','d4c40b01858ba8de0df4a4f81cd56709d1d62513','e4aa9d6aa9a63f227b79906b82b9bdae336343f7','20c8fc58887f2fa7e440ba0da3f9d1b6c14751ec','ca7f81b86b31f88aa6a58c86949e4d1d907ce515','97ffd7296297410062f686eb446623453116cd64']
    queue=[git('rev-parse',x).decode().strip() for x in starts];seeds=queue.copy();seen={};declarations=[]
    def refs(x,parent):
        if isinstance(x,dict):
            for k,v in x.items():
                if k in ('blob','git_blob','raw_git_blob') and isinstance(v,str) and re.fullmatch('[0-9a-f]{40}',v):
                    declarations.append(dict(parent=parent,git_blob=v,declared_bytes=x.get('bytes'),declared_sha256=x.get('sha256')));queue.append(v)
                else:refs(v,parent)
        elif isinstance(x,list):
            for v in x:refs(v,parent)
    while queue:
        h=queue.pop(0)
        if h in seen:continue
        raw=git('cat-file','blob',h);assert blob(raw)==h
        if h in existing:location=existing[h]
        else:
            p=OUT/'reviewed-raw'/h;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);location=dict(repository_raw_file=p.relative_to(ROOT).as_posix())
        seen[h]=dict(git_blob=h,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),**location)
        try:refs(json.loads(raw),h)
        except (ValueError,UnicodeDecodeError):pass
    mismatches=[]
    for d in declarations:
        got=seen[d['git_blob']]
        for a,b in [('declared_bytes','bytes'),('declared_sha256','sha256')]:
            if d[a] is not None and d[a]!=got[b]:mismatches.append(dict(declaration=d,actual=got))
    assert not mismatches,mismatches
    value=dict(scope='Complete routed independent source/image/browser/final/Luna raw chains; declared blob recursion; exact raw-file deduplication only',seeds=seeds,items=list(seen.values()),declarations=declarations,errors=mismatches)
    (OUT/'reviewed-raw-manifest.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(blobs=len(seen),bytes=sum(v['bytes'] for v in seen.values()),deduplicated=sum(v['repository_raw_file'].find('/integrated-merge/')<0 for v in seen.values()),declarations=len(declarations))))

if __name__=='__main__':main()
