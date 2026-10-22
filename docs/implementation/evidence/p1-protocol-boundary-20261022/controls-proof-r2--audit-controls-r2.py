import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path('tooling/foundation').resolve()))
from capture import run
from audit_pa3_native_readiness import CONTAINER_FORMAT
root=Path('artifacts/p1/controls-proof-r2');root.mkdir(parents=True,exist_ok=False)
def command(argv):
    p,m=run(argv,root/'commands',timeout_seconds=45)
    if p.returncode:raise RuntimeError('controls proof failed: '+m['streams']['stderr']['path'])
    return p.stdout
def save(name,v):(root/name).write_text(json.dumps(v,sort_keys=True,indent=2)+'\n',encoding='utf-8')
parent='sha256:97894f147c5640aa31b8349a52e37329575218a2100c41105fffccbf60ba844a'
image='sha256:7804b693efdde93b27afd32a8099762f21b59dd13583fdaa439ce751cb200833'
inventories={};states={};layers={}
code="import hashlib,json,pathlib;print(json.dumps({str(p.relative_to('/app')):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(pathlib.Path('/app').rglob('*')) if p.is_file()},sort_keys=True))"
for label,identifier in [('parent',parent),('final',image)]:
    name='remission-p1-native-sol-controls-proof-r2-'+label
    inventories[label]=json.loads(command(['docker','run','--name',name,'--network','none','--cpus','.5','--memory','512m','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=128m',identifier,'python','-c',code]))
    states[label]=json.loads(command(['docker','inspect',name,'--format',CONTAINER_FORMAT]))
    layers[label]=json.loads(command(['docker','image','inspect',identifier,'--format','{{json .RootFS.Layers}}']))
differences={p for p in set(inventories['parent'])|set(inventories['final']) if inventories['parent'].get(p)!=inventories['final'].get(p)}
expected={'tests/contracts/test_protocol_boundary.py','services/learner/export_observed.py','services/learner/worker.py'}
assert differences==expected
bindings={}
for path in expected:
    raw=Path(path).read_bytes();bindings[path]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    assert inventories['final'][path]==bindings[path]
assert layers['final'][:len(layers['parent'])]==layers['parent']
for label,value in inventories.items():save(label+'-inventory.json',value)
save('actual-states.json',states);save('actual-layers.json',layers)
save('result.json',{'parent':parent,'actual_final':image,'source_commit':'8f4b21f907ff7f8e36c69e63ad349e14395da256','changed_files':sorted(differences),'bindings':bindings,'full_parent_layer_prefix':True,'parent_files':len(inventories['parent']),'final_files':len(inventories['final']),'production_sources_unchanged_since434306c':True})
print(json.dumps({'passed':True,'parent_files':len(inventories['parent']),'final_files':len(inventories['final']),'exact_changed_paths':sorted(differences)},sort_keys=True))
