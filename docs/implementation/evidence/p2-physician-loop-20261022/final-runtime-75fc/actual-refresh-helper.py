import json,sys,time,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path('tooling/foundation').resolve()))
from capture import run
from analysis_dispatcher import CONTAINER_FORMAT

root=Path('artifacts/p2/browser-refresh-75fc');root.mkdir(parents=True,exist_ok=False)
old=json.loads(Path('artifacts/p2/browser-stack-9b73/deployment.json').read_bytes())
new=json.loads(Path('artifacts/p2/copy-r2/images.json').read_bytes())
prefix=old['prefix'];name=old['service_container'];image=new['images']['service']
def command(argv):
    p,m=run(argv,root/'commands',timeout_seconds=60)
    if p.returncode:raise RuntimeError('retained refresh failure '+m['streams']['stderr']['path'])
    return p.stdout.decode().strip()
before=json.loads(command(['docker','inspect',name,'--format',CONTAINER_FORMAT]))
assert before['Image']==old['service_image'] and before['State']['Running']
assert {m['Name'] for m in before['Mounts']}==set(old['volumes'].values())
(root/'old-running-selected.json').write_text(json.dumps(before,indent=2)+'\n')
command(['docker','stop','--time','10',name]);command(['docker','rename',name,name+'-9b73'])
volumes=old['volumes']
mount=lambda role,path,ro=False:['--mount','type=volume,src='+volumes[role]+',dst='+path+(',readonly' if ro else '')]
command(['docker','run','--detach','--name',name,'--label','remission.task='+prefix,'--network',old['network'],
    '--publish','127.0.0.1:8782:8765','--cpus','0.5','--memory','1g','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges',
    '--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=256m',*mount('database','/data'),*mount('fixtures','/fixtures',True),*mount('exports','/exports'),
    '-e','REMISSION_ORIGIN='+old['url'],'-e','REMISSION_CONTROL_BUNDLE=/fixtures/bundle.json','-e','REMISSION_ARCHIVE_CONFIG=/fixtures/archives.json',
    '-e','REMISSION_LIVE_EXPORT_ROOT=/exports','-e','REMISSION_RUNTIME_REF=/fixtures/runtime.json','-e','REMISSION_SOURCE_COMMIT='+new['source_head'],
    '-e','REMISSION_GENERATOR_URL=http://generator:8780',image])
deadline=time.monotonic()+20
while True:
    try:
        with urllib.request.urlopen(old['url']+'/health',timeout=1) as r:health=json.load(r)
        assert health['capability']=='LIVE-HOLD-01/1.0.0';break
    except (OSError,ValueError):
        if time.monotonic()>deadline:raise
        time.sleep(.1)
after=json.loads(command(['docker','inspect',name,'--format',CONTAINER_FORMAT]))
assert after['Image']==image and after['Mounts']==before['Mounts']
state=old|dict(source_head=new['source_head'],service_image=image,service_selected_state=after,health=health,
    retained_old_service=name+'-9b73',generator_unchanged=True,only_own_p2_service_replaced=True)
(root/'deployment.json').write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps(dict(source_head=new['source_head'],service_image=image,actual_container_id=after['Id'],prefix=prefix,url=old['url'])))
