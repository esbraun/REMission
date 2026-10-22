import hashlib,io,json,shutil,subprocess,sys,time,zipfile
from pathlib import Path
sys.path.insert(0,str(Path('tooling/foundation').resolve()))
from capture import run
from analysis_dispatcher import CONTAINER_FORMAT
root=Path('artifacts/cohort/factors-r1');root.mkdir(parents=True,exist_ok=False)
shutil.copyfile(__file__,root/'helper.py')
source=root/'source';source.mkdir()
raw=subprocess.check_output(['git','archive','--format=zip','HEAD','contracts','methods','services','tests','tooling/foundation'])
with zipfile.ZipFile(io.BytesIO(raw)) as archive:archive.extractall(source)
shutil.copyfile('tooling/foundation/diagnose_cohort_factors.py',source/'tooling/foundation/diagnose_cohort_factors.py')
manifest={str(p.relative_to(source)).replace('\\','/'):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(source.rglob('*')) if p.is_file()}
(root/'source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
out=root/'output';out.mkdir()
def command(argv,timeout=60):
 p,m=run(argv,root/'commands',timeout_seconds=timeout)
 if p.returncode:raise RuntimeError('retained command failure '+str(p.returncode)+' '+m['streams']['stderr']['path'])
 return p.stdout.decode().strip()
image='sha256:9d2e601f926ae644a041903b076fdb33ff3885be1a0f390137bc61ff461584e1'
assert command(['docker','image','inspect',image,'--format','{{.Id}}'])==image
name='remission-cohort-sol-factors-r1'
argv=['docker','create','--name',name,'--network','none','--cpus','2','--memory','2g','--read-only',
 '--cap-drop','ALL','--security-opt','no-new-privileges','--user','10002:10002',
 '--tmpfs','/tmp:rw,exec,nosuid,nodev,size=512m','--mount','type=bind,src='+str(source.resolve())+',dst=/cohort,readonly',
 '--mount','type=bind,src='+str(out.resolve())+',dst=/out','--workdir','/cohort',
 '--env','PYTHONPATH=/cohort','--env','OPENBLAS_NUM_THREADS=1','--env','OMP_NUM_THREADS=1','--env','MKL_NUM_THREADS=1',
 '--env','PYTENSOR_FLAGS=mode=NUMBA,floatX=float64,compiledir=/tmp/cohort-compile',
 '--entrypoint','python',image,'-u','tooling/foundation/diagnose_cohort_factors.py','--output','/out/result.json']
identifier=command(argv)
(root/'created.json').write_text(json.dumps(dict(container_id=identifier,name=name,source_head=subprocess.check_output(['git','rev-parse','HEAD']).decode().strip(),source_manifest_sha256=hashlib.sha256((root/'source-manifest.json').read_bytes()).hexdigest(),qualification_seconds_cap=1800,no_fit=True),indent=2)+'\n')
print('ACTUAL CREATED '+identifier,flush=True)
before=json.loads(command(['docker','inspect',identifier,'--format',CONTAINER_FORMAT]));(root/'created-state.json').write_text(json.dumps(before,indent=2)+'\n')
started=time.time();p,m=run(['docker','start','--attach',identifier],root/'commands',timeout_seconds=1800)
if p.returncode==124:
 stop=subprocess.run(['docker','stop','--time','10',identifier],capture_output=True,timeout=30)
 (root/'deadline-stop.json').write_text(json.dumps(dict(exit=stop.returncode,stdout=stop.stdout.decode(),stderr=stop.stderr.decode()),indent=2)+'\n')
after=json.loads(command(['docker','inspect',identifier,'--format',CONTAINER_FORMAT]));(root/'terminal-state.json').write_text(json.dumps(after,indent=2)+'\n')
(root/'run-status.json').write_text(json.dumps(dict(host_exit=p.returncode,elapsed_seconds=time.time()-started,command_metadata=m,no_fit=True),indent=2)+'\n')
print(json.dumps(dict(container_id=identifier,host_exit=p.returncode,worker_state=after['State'],elapsed_seconds=time.time()-started)),flush=True)
