"""Preserve the accepted exact PLAN and complete independent raw review chain."""
import hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path.cwd();OUT=Path(__file__).parent
PLAN='5409d54f570040b435a729769ba2d9353b7daffb'
def git(*args):return subprocess.check_output(['git',*args])
def blob(raw):return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()

def main():
    paths=git('diff','--name-only','ec18cb4020ba239710a3fd615e365d5cd72b4d80',PLAN).decode().splitlines()
    identity=[dict(path=p,blob=git('rev-parse',PLAN+':'+p).decode().strip()) for p in paths]
    seeds=['e5a67a4ad7e37b82cb591226e6b522d767f59db8','5e020233cb78c30a63f57122cebb5e69f81704fc','d5a7ae24b94ebf7c83834a001b814f7d83b35a78','9bc1286a16ed8a89c57018effd286dc19e3ebdce','cd3d84ca6e2129cfefdb25bd49eb26b83dbbd735','4b52a422a7172b73faed5664e5e47668ab17c5b2','95fe61d999f43fa6e0157ff3d3314cbd10ad3b55','040fd1b139dac4ac1fcde00b4d48d8bad4d8de57','2361d1d34f27fc220254534e87a459b068e3aabc','d3a4e67ff525284aec30727b3d76c615af40b4f6']
    existing={}
    for p in Path('docs/implementation/evidence').rglob('*'):
        if p.is_file() and OUT not in p.parents:
            existing.setdefault(blob(p.read_bytes()),p.as_posix())
    seeds += ['ff59eba525091a92c47e83a8efca6fd8426e97e3','d15630a474d519aa0819eb9bf610354a8a705cf1','1237cf4860b6a636f183935a735959246b8e84f0','413e5ee1c47964e1caf93e4fe952f8095c356992']
    queue=seeds+[x['blob'] for x in identity];seen={};declarations=[];physical_hints={};unavailable=[]
    def refs(x,parent):
        if isinstance(x,dict):
            if {'physical_bytes_git_blob_oid','git_tree_blob_oid_at_head','path'}<=x.keys():
                physical_hints[x['physical_bytes_git_blob_oid']]=x
            for k,v in x.items():
                if 'blob' in k and isinstance(v,str) and re.fullmatch('[0-9a-f]{40}',v):
                    queue.append(v);declarations.append(dict(parent=parent,git_blob=v))
                else:refs(v,parent)
        elif isinstance(x,list):
            for v in x:refs(v,parent)
    while queue:
        h=queue.pop(0)
        if h in seen:continue
        if h=='e5a67a4ad7e37b82cb591226e6b522d767f59db0':
            unavailable.append(dict(git_blob=h,reason='Historical Luna mistyped proposal citation, confirmed absent and corrected to supplied db8; original failing metadata retained, never substituted as authority'))
            continue
        if h in physical_hints:
            hint=physical_hints[h];source=git('cat-file','blob',hint['git_tree_blob_oid_at_head'])
            variants=[source,source.replace(b'\r\n',b'\n'),source.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')]
            raw=next((v for v in variants if blob(v)==h),None)
            if raw is None:raise ValueError('cannot independently reproduce declared physical source bytes: '+hint['path'])
            assert len(raw)==hint['physical_worktree_bytes'] and hashlib.sha256(raw).hexdigest()==hint['physical_worktree_sha256']
        else:raw=git('cat-file','blob',h)
        assert blob(raw)==h
        if h in existing:p=Path(existing[h])
        else:p=OUT/'b'/h;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
        seen[h]=dict(git_blob=h,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),repository_raw_file=p.as_posix())
        try:refs(json.loads(raw),h)
        except (ValueError,UnicodeDecodeError):pass
    path=Path('docs/implementation/g1-clearance-burden-contract-proposal-r1-20261021.md');path.write_bytes(git('cat-file','blob',seeds[0]))
    value=dict(plan=PLAN,root_acceptance='5409 accepted PLAN ONLY, historical unaccepted header retained; independent exact-code review still required',review=seeds[1],seeds=seeds,plan_tree_paths=identity,declarations=declarations,items=list(seen.values()),unavailable_historical_erroneous_references=unavailable)
    (OUT/'accepted-plan-raw-manifest.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(raw_blobs=len(seen),raw_bytes=sum(v['bytes'] for v in seen.values()),plan_paths=len(paths))))

if __name__=='__main__':main()
