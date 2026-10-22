"""One fresh P2-only namespace. No old deployment/cutover or dispatcher."""
import json,socket,sys,time,uuid,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path('tooling/foundation').resolve()))
from capture import run
from analysis_dispatcher import CONTAINER_FORMAT

root=Path('artifacts/p2/browser-stack-9b73');root.mkdir(parents=True,exist_ok=False)
with socket.socket() as probe:probe.bind(('127.0.0.1',8782))
def command(argv,seconds=60):
    p,m=run(argv,root/'commands',timeout_seconds=seconds)
    if p.returncode:raise RuntimeError('retained stack failure '+m['streams']['stderr']['path'])
    return p.stdout.decode().strip()
images=json.loads(Path('artifacts/p2/copy-r1/images.json').read_bytes())['images']
generator='sha256:bec9b330b57ea28e4b3a7a0c3d3437c71733b5949b6f5b9109baf301c9b20642'
runtime='sha256:ce346feace2ae607ebd574e1bb681d594c9b676c06b56f8ba8d50b858a577faa'
for image in [images['service'],generator,runtime]:assert command(['docker','image','inspect',image,'--format','{{.Id}}'])==image
head=command(['git','rev-parse','HEAD']);prefix='remission-p2-sol-'+uuid.uuid4().hex[:8]
network=prefix+'-app';command(['docker','network','create','--label','remission.task='+prefix,network])
volumes={role:prefix+'-'+role for role in ('database','fixtures','exports')}
mount=lambda role,path,ro=False:['--mount','type=volume,src='+volumes[role]+',dst='+path+(',readonly' if ro else '')]
for volume in volumes.values():command(['docker','volume','create','--label','remission.task='+prefix,volume])
limits=['--cpus','0.5','--memory','1g','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=256m']
all_mounts=[*mount('database','/data'),*mount('fixtures','/fixtures'),*mount('exports','/exports')]
command(['docker','run','--name',prefix+'-permissions','--network','none',*limits,'--cap-add','CHOWN','--user','0:0',*all_mounts,
    '--entrypoint','python',runtime,'-c',"import os;[(os.chmod(p,0o700),os.chown(p,10001,10001)) for p in ['/data','/fixtures','/exports']]"])
command(['docker','run','--name',prefix+'-prepare','--network','none',*limits,'--user','10001:10001',*all_mounts,
    '--mount','type=bind,src='+str(Path.cwd())+',dst=/source,readonly','--workdir','/source',
    '-e','PYTHONDONTWRITEBYTECODE=1','-e','PYTHONPATH=/source','--entrypoint','python',runtime,
    'tooling/foundation/prepare_live_demo.py','--fixture-root','/fixtures','--database','/data/remission.sqlite','--source-commit',head])
command(['docker','run','--detach','--name',prefix+'-generator','--label','remission.task='+prefix,'--network',network,
    '--network-alias','generator',*limits,generator])
url='http://127.0.0.1:8782'
command(['docker','run','--detach','--name',prefix+'-service','--label','remission.task='+prefix,'--network',network,
    '--publish','127.0.0.1:8782:8765',*limits,*mount('database','/data'),*mount('fixtures','/fixtures',True),*mount('exports','/exports'),
    '-e','REMISSION_ORIGIN='+url,'-e','REMISSION_CONTROL_BUNDLE=/fixtures/bundle.json','-e','REMISSION_ARCHIVE_CONFIG=/fixtures/archives.json',
    '-e','REMISSION_LIVE_EXPORT_ROOT=/exports','-e','REMISSION_RUNTIME_REF=/fixtures/runtime.json','-e','REMISSION_SOURCE_COMMIT='+head,
    '-e','REMISSION_GENERATOR_URL=http://generator:8780',images['service']])
deadline=time.monotonic()+20
while True:
    try:
        with urllib.request.urlopen(url+'/health',timeout=1) as r:health=json.load(r)
        assert health['capability']=='LIVE-HOLD-01/1.0.0';break
    except (OSError,ValueError):
        if time.monotonic()>deadline:raise
        time.sleep(.1)
state=dict(prefix=prefix,source_head=head,url=url,port=8782,service_image=images['service'],generator_image=generator,
    network=network,volumes=volumes,service_container=prefix+'-service',generator_container=prefix+'-generator',
    health=health,analysis_dispatcher_started=False,existing_deployments_untouched=True)
for role in ('service','generator'):
    state[role+'_selected_state']=json.loads(command(['docker','inspect',prefix+'-'+role,'--format',CONTAINER_FORMAT]))
(root/'deployment.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps({k:state[k] for k in ('prefix','url','source_head','service_image','generator_image')}))
