import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path('tooling/foundation').resolve()))
from capture import run
root=Path('artifacts/p1/copied-434306c');root.mkdir(parents=True,exist_ok=False)
def save(name,v):(root/name).write_text(json.dumps(v,sort_keys=True,indent=2)+'\n',encoding='utf-8')
def command(argv,timeout=120):
    p,m=run(argv,root/'commands',timeout_seconds=timeout)
    if p.returncode:raise RuntimeError('COPY command failed: '+m['streams']['stderr']['path'])
    return p.stdout
assert command(['git','rev-parse','HEAD']).decode().strip()=='434306c5a92eff819916bc74e97d2bd968256a40'
assert not command(['git','status','--short']).strip()
images={}
parents={'service':'sha256:bad33f377d97f52572e182d0973b1f1f56dbc3f1c413de48f20b0458e0906fb7','learner':'sha256:9d2e601f926ae644a041903b076fdb33ff3885be1a0f390137bc61ff461584e1','generator':'sha256:5d546abd1448e46d5d45ac4a3d98c31899631f968f93d21b163797ff0674ded9'}
base_args=[]
for role,identifier in parents.items():
    tag='remission-p1-native-sol-434306c-'+role+'-base:retained'
    command(['docker','tag',identifier,tag])
    assert json.loads(command(['docker','image','inspect',tag,'--format','{{json .Id}}']))==identifier
    base_args+=['--build-arg',role.upper()+'_BASE='+tag]
fmt='{"Id":{{json .Id}},"RootFS":{{json .RootFS}},"User":{{json .Config.User}},"WorkingDir":{{json .Config.WorkingDir}},"Cmd":{{json .Config.Cmd}},"Entrypoint":{{json (index .Config "Entrypoint")}}}'
for role in ['service','learner','generator','controls']:
    tag='remission-p1-native-sol-434306c-'+role+':candidate'
    command(['docker','build','--network','none','--file','tooling/foundation/p1-protocol.Dockerfile',*base_args,'--target',role,'--tag',tag,'.'])
    images[role]=json.loads(command(['docker','image','inspect',tag,'--format',fmt]))
    save('images.json',images)
source={}
for folder in ['contracts/domain','services/foundation','services/learner','services/generator','tests','tooling/foundation']:
    for p in Path(folder).rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts:
            source[p.as_posix()]={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
save('origin.json',{'source_commit':'434306c5a92eff819916bc74e97d2bd968256a40','integration_merge':'a1f20e76e532da60e94b125d21b5049172e4bcd6','base':'045b373a18ad067a3ecd1281d445076aae423a80','COPY_only':True,'source_files':source,'actual_images':{k:v['Id'] for k,v in images.items()},'parents':parents,'production_role_note':'controls explicitly includes private generator/method/test code; production service and learner must exclude generator; learner excludes foundation'})
print(json.dumps({k:v['Id'] for k,v in images.items()},sort_keys=True))
