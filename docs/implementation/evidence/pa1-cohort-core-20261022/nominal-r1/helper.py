import datetime,hashlib,io,json,shutil,subprocess,sys,time,zipfile
from pathlib import Path
sys.path.insert(0,str(Path('tooling/foundation').resolve()))
from capture import run
from analysis_dispatcher import CONTAINER_FORMAT
root=Path('artifacts/cohort/nominal-r1');root.mkdir(parents=True,exist_ok=False)
shutil.copyfile(__file__,root/'helper.py');shutil.copyfile('artifacts/cohort/nominal-watchdog.py',root/'watchdog.py')
head='8aeebf554cb4dbc1e3305c6e46d7775db19459e1'
source=root/'source';source.mkdir()
raw=subprocess.check_output(['git','archive','--format=zip',head,'contracts','methods','services','tests','tooling/foundation'])
with zipfile.ZipFile(io.BytesIO(raw)) as archive:archive.extractall(source)
manifest={str(p.relative_to(source)).replace('\\','/'):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(source.rglob('*')) if p.is_file()}
(root/'source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
out=root/'output';out.mkdir()
def command(argv,timeout=60):
 p,m=run(argv,root/'commands',timeout_seconds=timeout)
 if p.returncode:raise RuntimeError('retained command failure '+str(p.returncode)+' '+m['streams']['stderr']['path'])
 return p.stdout.decode().strip()
image='sha256:9d2e601f926ae644a041903b076fdb33ff3885be1a0f390137bc61ff461584e1'
assert command(['docker','image','inspect',image,'--format','{{.Id}}'])==image
name='remission-cohort-sol-nominal-r1'
argv=['docker','create','--name',name,'--network','none','--cpus','2','--memory','2g','--read-only','--cap-drop','ALL',
 '--security-opt','no-new-privileges','--user','10002:10002','--tmpfs','/tmp:rw,exec,nosuid,nodev,size=512m',
 '--mount','type=bind,src='+str(source.resolve())+',dst=/cohort,readonly','--mount','type=bind,src='+str(out.resolve())+',dst=/out',
 '--workdir','/cohort','--env','PYTHONPATH=/cohort','--env','OPENBLAS_NUM_THREADS=1','--env','OMP_NUM_THREADS=1','--env','MKL_NUM_THREADS=1',
 '--entrypoint','python',image,'-u','tooling/foundation/qualify_cohort_nominal_singleton.py','--output','/out/result.json']
identifier=command(argv)
(root/'created.json').write_text(json.dumps(dict(container_id=identifier,name=name,source_head=head,
 source_manifest_sha256=hashlib.sha256((root/'source-manifest.json').read_bytes()).hexdigest(),qualification_seconds_cap=1800,no_fit=True),indent=2)+'\n')
(root/'created-state.json').write_text(command(['docker','inspect',identifier,'--format',CONTAINER_FORMAT])+'\n')
deadline=datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(seconds=1800)
(root/'watchdog-config.json').write_text(json.dumps(dict(container_id=identifier,deadline=deadline.isoformat()),indent=2)+'\n')
watchdog=subprocess.Popen([sys.executable,str((root/'watchdog.py').resolve()),str(root.resolve())],
    creationflags=subprocess.CREATE_NO_WINDOW,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
for _ in range(100):
 if (root/'watchdog-ready.json').exists():break
 if watchdog.poll() is not None:raise RuntimeError('watchdog exited before arming')
 time.sleep(.1)
assert (root/'watchdog-ready.json').exists() and watchdog.poll() is None
print(json.dumps(dict(actual_container=identifier,watchdog_pid=watchdog.pid,deadline=deadline.isoformat(),source=head)),flush=True)
started=time.monotonic();p,m=run(['docker','start','--attach',identifier],root/'commands',timeout_seconds=1835)
if p.returncode==124:command(['docker','stop','--time','0',identifier],30)
watchdog.wait(timeout=20)
(root/'terminal-state.json').write_text(command(['docker','inspect',identifier,'--format',CONTAINER_FORMAT])+'\n')
(root/'run-status.json').write_text(json.dumps(dict(host_exit=p.returncode,elapsed_seconds=time.monotonic()-started,
 command_metadata=m,no_fit=True,watchdog_pid=watchdog.pid,watchdog_exit=watchdog.returncode),indent=2)+'\n')
print(json.dumps(dict(container_id=identifier,host_exit=p.returncode,elapsed_seconds=time.monotonic()-started)),flush=True)
