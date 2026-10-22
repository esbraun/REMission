"""Fresh owned synthetic UI stack; no old containers, cutover, or dispatcher."""
import hashlib,io,json,socket,subprocess,sys,time,urllib.request,uuid,zipfile
from pathlib import Path
sys.path.insert(0,str(Path('tooling/foundation').resolve()))
from capture import run
from analysis_dispatcher import CONTAINER_FORMAT
root=Path('artifacts/cohort/stack-r1');root.mkdir(exist_ok=False)
source=root/'bootstrap-source';source.mkdir()
head='45d35071036ca3b635ae60e97ca04e924d98f74e'
images=json.loads(Path('artifacts/cohort/roles-r2/images.json').read_text())['images']
assert set(images)=={'service','learner','generator'}
with socket.socket() as probe:probe.bind(('127.0.0.1',8784))
archive=subprocess.check_output(['git','archive','--format=zip',head,'contracts','services','tests','tooling/foundation'])
with zipfile.ZipFile(io.BytesIO(archive)) as z:z.extractall(source)
prefix='remission-cohort-sol-'+uuid.uuid4().hex[:10]
network=prefix+'-app';volumes={k:prefix+'-'+k for k in ('database','fixtures','exports')}
common=['--cpus','2','--memory','2g','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=256m']
runtime='sha256:ce346feace2ae607ebd574e1bb681d594c9b676c06b56f8ba8d50b858a577faa'
def command(argv,timeout=120):
    p,m=run(argv,root/'commands',timeout_seconds=timeout)
    if p.returncode:raise RuntimeError('Retained new-stack command failure: '+m['streams']['stderr']['path'])
    return p.stdout.decode().strip()
def mount(role,target,ro=False):return ['--mount',f'type=volume,source={volumes[role]},target={target}'+(',readonly' if ro else '')]
for image in [runtime,*images.values()]:assert command(['docker','image','inspect',image,'--format','{{.Id}}'])==image
command(['docker','network','create','--internal','--label','remission.task='+prefix,network])
for name in volumes.values():
    command(['docker','volume','create','--label','remission.task='+prefix,name])
    command(['docker','run','--rm','--network','none',*common,'--cap-add','CHOWN','--user','0:0','--mount',f'type=volume,source={name},target=/owned',runtime,
        'python','-c',"import os;os.chmod('/owned',0o700);os.chown('/owned',10001,10001)"])
command(['docker','run','--rm','--network','none',*common,'--user','10001:10001','--env','PYTHONPATH=/source',
    '--mount',f'type=bind,source={source.resolve()},target=/source,readonly','--workdir','/source',*mount('database','/data'),*mount('fixtures','/fixtures'),runtime,
    'python','tooling/foundation/prepare_live_demo.py','--fixture-root','/fixtures','--database','/data/remission.sqlite','--source-commit',head])
generator=command(['docker','run','--detach','--name',prefix+'-generator','--label','remission.task='+prefix,'--network',network,'--network-alias','generator',*common,images['generator']])
service=command(['docker','run','--detach','--name',prefix+'-service','--label','remission.task='+prefix,'--network',network,'--publish','127.0.0.1:8784:8765',*common,
    *mount('database','/data'),*mount('fixtures','/fixtures',True),*mount('exports','/exports'),
    '--env','REMISSION_ORIGIN=http://127.0.0.1:8784','--env','REMISSION_CONTROL_BUNDLE=/fixtures/bundle.json',
    '--env','REMISSION_ARCHIVE_CONFIG=/fixtures/archives.json','--env','REMISSION_LIVE_EXPORT_ROOT=/exports',
    '--env','REMISSION_RUNTIME_REF=/fixtures/runtime.json','--env','REMISSION_SOURCE_COMMIT='+head,
    '--env','REMISSION_GENERATOR_URL=http://generator:8780',images['service']])
for role,identifier in [('service',service),('generator',generator)]:
    (root/(role+'-selected-state.json')).write_text(command(['docker','inspect',identifier,'--format',CONTAINER_FORMAT])+'\n')
state=dict(prefix=prefix,source_commit=head,images=images,service_container=service,generator_container=generator,
    port=8784,url='http://127.0.0.1:8784',network=network,volumes=volumes,analysis_dispatcher=False,
    fixture_claim='Fresh existing synthetic auth/control fixture only. Interactive generator panel is not a trusted research cohort.')
(root/'deployment.json').write_text(json.dumps(state,indent=2)+'\n')
deadline=time.monotonic()+30
while True:
    try:
        with urllib.request.urlopen(state['url']+'/health',timeout=1) as response:health=json.load(response)
        break
    except OSError:
        if time.monotonic()>deadline:raise
        time.sleep(.2)
(root/'health.json').write_text(json.dumps(health,indent=2)+'\n')
print(json.dumps(dict(prefix=prefix,service=service,generator=generator,url=state['url'],health=health)),flush=True)
