import json,sys
from pathlib import Path
sys.path.insert(0,str(Path('tooling/foundation').resolve()))
from capture import run
from analysis_dispatcher import CONTAINER_FORMAT
root=Path('artifacts/cohort/counts-r1');root.mkdir(parents=True,exist_ok=False)
source=Path('artifacts/cohort/factors-r3/source').resolve()
name='remission-cohort-sol-counts-r1'
argv=['docker','run','--name',name,'--network','none','--cpus','2','--memory','2g','--read-only','--cap-drop','ALL',
 '--security-opt','no-new-privileges','--user','10002:10002','--tmpfs','/tmp:rw,exec,nosuid,nodev,size=512m',
 '--mount','type=bind,src='+str(source)+',dst=/cohort,readonly','--workdir','/cohort','--env','PYTHONPATH=/cohort',
 '--env','OPENBLAS_NUM_THREADS=1','--env','OMP_NUM_THREADS=1','--entrypoint','python',
 'sha256:9d2e601f926ae644a041903b076fdb33ff3885be1a0f390137bc61ff461584e1','-m','unittest','discover',
 '-s','tests/methods','-p','test_cohort_counts.py','-v']
p,m=run(argv,root/'commands',timeout_seconds=300)
if p.returncode==124:
 run(['docker','stop','--time','10',name],root/'commands',timeout_seconds=30)
s,sm=run(['docker','inspect',name,'--format',CONTAINER_FORMAT],root/'commands',timeout_seconds=30)
(root/'terminal.json').write_bytes(s.stdout)
(root/'status.json').write_text(json.dumps(dict(exit=p.returncode,streams=m['streams'],source_root=str(source),no_fit=True),indent=2)+'\n')
print(p.stderr.decode()[-4000:]);print('HOST EXIT',p.returncode,flush=True)
