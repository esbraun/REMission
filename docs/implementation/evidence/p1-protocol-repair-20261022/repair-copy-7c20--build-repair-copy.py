import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path('tooling/foundation').resolve()))
from capture import run
root=Path('artifacts/p1/repair-copy-7c20');root.mkdir(parents=True,exist_ok=False)
def command(argv):
    p,m=run(argv,root/'commands',timeout_seconds=90)
    if p.returncode:raise RuntimeError('repair COPY failed: '+m['streams']['stderr']['path'])
    return p.stdout
assert command(['git','rev-parse','HEAD']).decode().strip()=='7c20a3926b410a3cf7359bde3e1a857dae2de046'
old=json.loads(Path('artifacts/p1/copied-434306c/images.json').read_text())
parents={'service':old['service']['Id'],'learner':old['learner']['Id'],'controls':'sha256:7804b693efdde93b27afd32a8099762f21b59dd13583fdaa439ce751cb200833'}
args=[]
for role,parent in parents.items():
    tag='remission-p1-native-sol-7c20-'+role+'-base:retained';command(['docker','tag',parent,tag])
    assert json.loads(command(['docker','image','inspect',tag,'--format','{{json .Id}}']))==parent
    args+=['--build-arg',role.upper()+'_BASE='+tag]
images={'generator':old['generator']}
for role in parents:
    tag='remission-p1-native-sol-7c20-'+role+':candidate'
    command(['docker','build','--network','none','--file','artifacts/p1/repair-source/COPY.Dockerfile',*args,'--target',role,'--tag',tag,'.'])
    images[role]=json.loads(command(['docker','image','inspect',tag,'--format','{"Id":{{json .Id}},"RootFS":{{json .RootFS}}}']))
    (root/'images.json').write_text(json.dumps(images,sort_keys=True,indent=2)+'\n')
files=['services/foundation/protocol.py','contracts/domain/protocol_analysis.py','tests/protocol_fixtures.py','tests/contracts/test_protocol_boundary.py']
origin={'source_commit':'7c20a3926b410a3cf7359bde3e1a857dae2de046','parents':parents,'source_files':{p:{'bytes':Path(p).stat().st_size,'sha256':hashlib.sha256(Path(p).read_bytes()).hexdigest()} for p in files},'generator_unchanged':old['generator']['Id'],'COPY_only':True}
(root/'origin.json').write_text(json.dumps(origin,sort_keys=True,indent=2)+'\n')
print(json.dumps({k:v['Id'] for k,v in images.items()},sort_keys=True))
