import hashlib,json,shutil,sys
from pathlib import Path
sys.path.insert(0,str(Path('tooling/foundation').resolve()))
from capture import run
from analysis_dispatcher import CONTAINER_FORMAT

root=Path('artifacts/p2/repair-regressions-75fc');root.mkdir(parents=True,exist_ok=False)
names=['remission-p2-sol-active-restart-before-5511','remission-p2-sol-replay-before-5511',
       'remission-p2-sol-active-restart-after-5511','remission-p2-sol-replay-after-5511','remission-p2-sol-dev-loop-1']
states={}
for name in names:
    p,m=run(['docker','logs',name],root/'commands',timeout_seconds=30)
    assert p.returncode==0
    (root/(name+'.stdout')).write_bytes(p.stdout);(root/(name+'.stderr')).write_bytes(p.stderr)
    p,m=run(['docker','inspect',name,'--format',CONTAINER_FORMAT],root/'commands',timeout_seconds=30)
    assert p.returncode==0;states[name]=json.loads(p.stdout)
    assert not states[name]['State']['Running']
(root/'actual-states.json').write_text(json.dumps(states,indent=2)+'\n')
shutil.copyfile('tests/generator/test_nof1_loop.py',root/'final-regression-source.py')
shutil.copyfile(__file__,root/'helper.py')
m={str(p.relative_to(root)).replace('\\','/'):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(root.rglob('*')) if p.is_file()}
(root/'raw-manifest.json').write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(files_including_manifest=len(m)+1,manifest_sha256=hashlib.sha256((root/'raw-manifest.json').read_bytes()).hexdigest())))
