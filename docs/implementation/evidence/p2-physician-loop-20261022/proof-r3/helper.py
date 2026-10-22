import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path('tooling/foundation').resolve()))
from capture import run
from analysis_dispatcher import CONTAINER_FORMAT

root=Path('artifacts/p2/proof-r3');root.mkdir(parents=True,exist_ok=False)
build=json.loads(Path('artifacts/p2/copy-r2/images.json').read_bytes())
def command(argv):
    p,m=run(argv,root/'commands',timeout_seconds=60)
    if p.returncode:raise RuntimeError('copy audit failed; retained '+m['streams']['stderr']['path'])
    return p.stdout.decode().strip()
limits=['--network','none','--cpus','0.25','--memory','256m','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--tmpfs','/tmp:rw,nosuid,nodev,noexec,size=64m']
probe="import json,hashlib;from pathlib import Path;r=Path('/app');print(json.dumps({str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(r.rglob('*')) if p.is_file()},sort_keys=True))"
format='{"Id":{{json .Id}},"Layers":{{json .RootFS.Layers}},"User":{{json (index .Config "User")}},"WorkingDir":{{json (index .Config "WorkingDir")}},"Cmd":{{json (index .Config "Cmd")}},"Entrypoint":{{json (index .Config "Entrypoint")}}}'
checks=[]
for role in ('service','controls'):
    old,new=build['bases'][role],build['images'][role]
    inventories=[];states=[]
    for suffix,image in [('parent',old),('new',new)]:
        inventory=json.loads(command(['docker','run','--name','remission-p2-sol-audit-'+role+'-'+suffix+'-r3',*limits,'--entrypoint','python',image,'-c',probe]))
        (root/(role+'-'+suffix+'-inventory.json')).write_text(json.dumps(inventory,indent=2,sort_keys=True)+'\n');inventories.append(inventory)
        states.append(json.loads(command(['docker','image','inspect',image,'--format',format])))
    expected={'services/foundation/'+n:hashlib.sha256((Path('services/foundation')/n).read_bytes()).hexdigest()
        for n in ('app.py','simulation.py','workflow.py','nof1.py','nof1_clock.py')}
    if role=='service':expected.update({'web/dist/'+str(p.relative_to('web/dist')).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('web/dist').rglob('*') if p.is_file()})
    else:
        for name in ('tests/generator/test_nof1_loop.py','tests/contracts/test_nof1_clock.py'):expected[name]=hashlib.sha256(Path(name).read_bytes()).hexdigest()
    changed={p for p in set(inventories[0])|set(inventories[1]) if inventories[0].get(p)!=inventories[1].get(p)}
    assert changed==set(expected),(role,changed,set(expected))
    assert all(inventories[1][p]==sha for p,sha in expected.items())
    assert states[1]['Layers'][:len(states[0]['Layers'])]==states[0]['Layers']
    assert all(states[0][key]==states[1][key] for key in ('User','WorkingDir','Cmd','Entrypoint'))
    if role=='service':assert not any(p.startswith('services/generator/') for p in inventories[1])
    (root/(role+'-selected-images.json')).write_text(json.dumps(states,indent=2)+'\n')
    checks.append(dict(role=role,files_before=len(inventories[0]),files_after=len(inventories[1]),changed=sorted(changed),physical_bindings=expected,parent_layers_preserved=True,selected_config_preserved=True))
containers={}
for role in ('loop','p1'):
    name='remission-p2-sol-copied-'+role+'-r2'
    value=json.loads(command(['docker','inspect',name,'--format',CONTAINER_FORMAT]));containers[name]=value
    assert not value['State']['Running'] and value['State']['ExitCode']==0 and not value['State']['OOMKilled']
    assert value['Image']==build['images']['controls'] and not value['Mounts']
(root/'checks.json').write_text(json.dumps(checks,indent=2)+'\n')
(root/'actual-controls.json').write_text(json.dumps(containers,indent=2)+'\n')
print(json.dumps(dict(source_head=build['source_head'],checks=[{k:v for k,v in c.items() if k!='physical_bindings'} for c in checks],controls_terminal=True)))
