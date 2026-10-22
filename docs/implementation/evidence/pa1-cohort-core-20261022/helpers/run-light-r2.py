import json,sys
from pathlib import Path
sys.path.insert(0,str(Path('tooling/foundation').resolve()))
from capture import run
from analysis_dispatcher import CONTAINER_FORMAT
root=Path('artifacts/cohort/light-r2');root.mkdir(parents=True,exist_ok=False)
image='sha256:24fcd00563071feb11d18f82acb8f85393dd28f6ba4aa2ecfe7ce17d0c13bda8'
limits=['--network','none','--cpus','0.5','--memory','1g','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges',
 '--user','10001:10001','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=256m','--mount','type=bind,src='+str(Path.cwd())+',dst=/cohort,readonly',
 '--workdir','/cohort','--env','PYTHONPATH=/cohort:/cohort/tests/integration/replay','--env','OPENBLAS_NUM_THREADS=1','--env','OMP_NUM_THREADS=1']
for name,directory,pattern in [('contracts','tests/contracts','test_cohort.py'),('service','tests/integration/replay','test_cohort_service.py')]:
 container='remission-cohort-sol-light-'+name+'-r2'
 p,m=run(['docker','run','--name',container,*limits,'--entrypoint','python',image,'-m','unittest','discover','-s',directory,'-p',pattern,'-v'],root/'commands',timeout_seconds=120)
 print(json.dumps(dict(name=name,exit=p.returncode,metadata=m['streams'])),flush=True)
 s,sm=run(['docker','inspect',container,'--format',CONTAINER_FORMAT],root/'commands',timeout_seconds=30)
 (root/(name+'-state.json')).write_bytes(s.stdout)
 if p.returncode:break
