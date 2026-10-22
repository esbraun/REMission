import hashlib,io,json,subprocess,sys,urllib.request,zipfile
from pathlib import Path
sys.path.insert(0,str(Path('tooling/foundation').resolve()))
from capture import run
from analysis_dispatcher import CONTAINER_FORMAT
root=Path('artifacts/cohort/service-ui-r3');root.mkdir(exist_ok=False)
source=root/'source';source.mkdir()
head='78c01ca6fe1dc46ec6a2e2afcce6ce297d573fdc'
raw=subprocess.check_output(['git','archive','--format=zip',head,'.dockerignore','contracts','methods','services','tooling/foundation','web'])
with zipfile.ZipFile(io.BytesIO(raw)) as z:z.extractall(source)
(root/'source-manifest.json').write_text(json.dumps({p.relative_to(source).as_posix():dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(source.rglob('*')) if p.is_file()},indent=2)+'\n')
state=json.loads(Path('artifacts/cohort/frontbridge-r1/deployment.json').read_text())
def command(argv,timeout=120):
    p,m=run(argv,root/'commands',timeout_seconds=timeout)
    if p.returncode:raise RuntimeError('Preserved new-service command failure: '+m['streams']['stderr']['path'])
    return p.stdout.decode().strip()
assert command(['docker','image','inspect','remission-foundation-runtime:candidate','--format','{{.Id}}'])=='sha256:ce346feace2ae607ebd574e1bb681d594c9b676c06b56f8ba8d50b858a577faa'
tag='remission-cohort-sol-service:78c01ca'
command(['docker','build','--network','none','--file',str(source/'tooling/foundation/service.Dockerfile'),'--target','service','--tag',tag,str(source)],240)
image=command(['docker','image','inspect',tag,'--format','{{.Id}}'])
(root/'image.json').write_text(json.dumps(dict(source=head,image=image,base='sha256:ce346feace2ae607ebd574e1bb681d594c9b676c06b56f8ba8d50b858a577faa'),indent=2)+'\n')
identity="""import json,os,sqlite3
p='/data/remission.sqlite';db=sqlite3.connect('file:'+p+'?mode=ro',uri=True);db.execute('PRAGMA query_only=ON')
print(json.dumps(dict(device=os.stat(p).st_dev,inode=os.stat(p).st_ino,lock_inode=os.stat(p+'.admission.lock').st_ino,counts={t:db.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ['patients','events','bundles','analysis_attempts']})))
"""
before=json.loads(command(['docker','exec',state['service_container'],'python','-c',identity]))
(root/'pre-ui-authority-identity.json').write_text(json.dumps(before,indent=2)+'\n')
command(['docker','stop','--time','10',state['service_container']])
assert not command(['docker','ps','--quiet','--filter','volume='+state['volumes']['database']])
(root/'retained-old-service.json').write_text(command(['docker','inspect',state['service_container'],'--format',CONTAINER_FORMAT])+'\n')
common=['--cpus','2','--memory','2g','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=256m']
mounts=[]
for role,target,ro in [('database','/data',False),('fixtures','/fixtures',True),('exports','/exports',False)]:
    mounts+=['--mount',f'type=volume,source={state["volumes"][role]},target={target}'+(',readonly' if ro else '')]
identifier=command(['docker','create','--name',state['prefix']+'-service-ui-r3','--label','remission.task='+state['prefix'],
    '--network',state['network'],'--publish','127.0.0.1:8784:8765',*common,*mounts,
    '--env','REMISSION_ORIGIN=http://127.0.0.1:8784','--env','REMISSION_CONTROL_BUNDLE=/fixtures/bundle.json',
    '--env','REMISSION_ARCHIVE_CONFIG=/fixtures/archives.json','--env','REMISSION_LIVE_EXPORT_ROOT=/exports',
    '--env','REMISSION_RUNTIME_REF=/fixtures/runtime.json','--env','REMISSION_SOURCE_COMMIT='+head,
    '--env','REMISSION_GENERATOR_URL=http://generator:8780',image])
command(['docker','network','connect',state['frontend_network'],identifier])
command(['docker','start',identifier])
after=json.loads(command(['docker','exec',identifier,'python','-c',identity]));assert after==before
(root/'post-ui-authority-identity.json').write_text(json.dumps(after,indent=2)+'\n')
(root/'selected-state.json').write_text(command(['docker','inspect',identifier,'--format',CONTAINER_FORMAT])+'\n')
old=state['service_container'];state.update(service_container=identifier,retained_old_service=old,service_source=head)
state['images']['service']=image
(root/'deployment.json').write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps(dict(new_service=identifier,image=image,source=head,old_retained=old,authority_identity_unchanged=True)),flush=True)
