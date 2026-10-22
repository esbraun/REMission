import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path('tooling/foundation').resolve()))
from capture import run
from audit_pa3_native_readiness import CONTAINER_FORMAT
root=Path('artifacts/p1/repair-proof-7c20');root.mkdir(parents=True,exist_ok=False)
images=json.loads(Path('artifacts/p1/repair-copy-7c20/images.json').read_text())
origin=json.loads(Path('artifacts/p1/repair-copy-7c20/origin.json').read_text())
def command(argv):
    p,m=run(argv,root/'commands',timeout_seconds=45)
    if p.returncode:raise RuntimeError('repair inventory failed: '+m['streams']['stderr']['path'])
    return p.stdout
def save(name,v):(root/name).write_text(json.dumps(v,sort_keys=True,indent=2)+'\n',encoding='utf-8')
expected={'service':{'services/foundation/protocol.py','contracts/domain/protocol_analysis.py'},
    'learner':{'contracts/domain/protocol_analysis.py'},'controls':{'services/foundation/protocol.py','contracts/domain/protocol_analysis.py','tests/protocol_fixtures.py','tests/contracts/test_protocol_boundary.py'}}
code="import hashlib,json,pathlib;print(json.dumps({str(p.relative_to('/app')):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(pathlib.Path('/app').rglob('*')) if p.is_file()},sort_keys=True))"
fmt='{"Id":{{json .Id}},"RootFS":{{json .RootFS}},"User":{{json .Config.User}},"WorkingDir":{{json .Config.WorkingDir}},"Cmd":{{json .Config.Cmd}},"Entrypoint":{{json (index .Config "Entrypoint")}}}'
checks={};states={}
for role,paths in expected.items():
    inventories={};metadata={}
    for label,identifier in [('parent',origin['parents'][role]),('new',images[role]['Id'])]:
        name='remission-p1-native-sol-repair-proof-7c20-'+role+'-'+label
        inventories[label]=json.loads(command(['docker','run','--name',name,'--network','none','--cpus','.5','--memory','512m','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=128m',identifier,'python','-c',code]))
        states[role+'-'+label]=json.loads(command(['docker','inspect',name,'--format',CONTAINER_FORMAT]))
        metadata[label]=json.loads(command(['docker','image','inspect',identifier,'--format',fmt]))
        save(role+'-'+label+'-inventory.json',inventories[label])
    changes={p for p in set(inventories['parent'])|set(inventories['new']) if inventories['parent'].get(p)!=inventories['new'].get(p)}
    assert changes==paths
    bindings={p:{'bytes':Path(p).stat().st_size,'sha256':hashlib.sha256(Path(p).read_bytes()).hexdigest()} for p in paths}
    assert all(inventories['new'][p]==bindings[p] for p in paths)
    count=len(metadata['parent']['RootFS']['Layers'])
    assert metadata['new']['RootFS']['Layers'][:count]==metadata['parent']['RootFS']['Layers']
    assert all(metadata['new'][k]==metadata['parent'][k] for k in ['User','WorkingDir','Cmd','Entrypoint'])
    checks[role]={'actual_image':images[role]['Id'],'parent':origin['parents'][role],'exact_changes':sorted(changes),'bindings':bindings,'complete_parent_layer_prefix':True,'launch_config_unchanged':True,'files_count':len(inventories['new'])}
    save('checks.json',checks)
save('actual-states.json',states)
print(json.dumps({k:{f:v for f,v in value.items() if f!='bindings'} for k,value in checks.items()},sort_keys=True))
