import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path('tooling/foundation').resolve()))
from capture import run
from audit_pa3_native_readiness import CONTAINER_FORMAT
root=Path('artifacts/p1/copy-audit-434306c');root.mkdir(parents=True,exist_ok=False)
origin=json.loads(Path('artifacts/p1/copied-434306c/origin.json').read_text())
images=json.loads(Path('artifacts/p1/copied-434306c/images.json').read_text())
def save(name,v):(root/name).write_text(json.dumps(v,sort_keys=True,indent=2)+'\n',encoding='utf-8')
def command(argv):
    p,m=run(argv,root/'commands',timeout_seconds=60)
    if p.returncode:raise RuntimeError('role inventory failed: '+m['streams']['stderr']['path'])
    return p.stdout
common=['--network','none','--cpus','.5','--memory','512m','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=128m']
probe="import hashlib,json,pathlib; print(json.dumps({str(p.relative_to('/app')):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(pathlib.Path('/app').rglob('*')) if p.is_file()},sort_keys=True))"
checks={};states={}
for role in ['service','learner','generator']:
    values={}
    for label,image in [('base',origin['parents'][role]),('new',images[role]['Id'])]:
        name='remission-p1-native-sol-inventory-434306c-'+role+'-'+label
        values[label]=json.loads(command(['docker','run','--name',name,*common,image,'python','-c',probe]))
        states[role+'-'+label]=json.loads(command(['docker','inspect',name,'--format',CONTAINER_FORMAT]))
        save(role+'-'+label+'-inventory.json',values[label])
    if role=='service':
        expected={p for p in values['new'] if p.startswith('services/foundation/')}|{'contracts/domain/'+n+'.py' for n in ['protocol','protocol_analysis','protocol_request','borrowing']}
        assert not any(p.startswith('services/generator/') for p in values['new'])
    elif role=='learner':
        expected={'contracts/domain/'+n+'.py' for n in ['protocol','protocol_analysis','protocol_request','borrowing']}|{'services/learner/'+n+'.py' for n in ['analysis_worker','export_observed','worker']}|{'protocol_probe.py'}
        assert not any(p.startswith(('services/generator/','services/foundation/')) for p in values['new'])
    else:expected={'services/generator/'+n+'.py' for n in ['restricted','restricted_v2','server']}
    differences={p for p in set(values['base'])|set(values['new']) if values['base'].get(p)!=values['new'].get(p)}
    assert differences<=expected,(role,'unexpected changed file',sorted(differences-expected))
    bindings={}
    for path in expected:
        source=Path('tooling/foundation/protocol_probe.py') if path=='protocol_probe.py' else Path(path)
        assert source.is_file() and values['new'][path]=={'bytes':source.stat().st_size,'sha256':hashlib.sha256(source.read_bytes()).hexdigest()},(role,path)
        bindings[path]=values['new'][path]
    parent=json.loads(command(['docker','image','inspect',origin['parents'][role],'--format','{{json .RootFS.Layers}}']))
    assert images[role]['RootFS']['Layers'][:len(parent)]==parent
    checks[role]={'base_files':len(values['base']),'new_files':len(values['new']),'actual_changes':sorted(differences),'physical_bindings':bindings,'complete_parent_layer_prefix':True}
    save('checks.json',checks)
save('actual-inventory-states.json',states)
print(json.dumps({role:{k:v for k,v in check.items() if k!='physical_bindings'} for role,check in checks.items()},sort_keys=True))
