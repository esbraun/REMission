import ipaddress,json,sys,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path('tooling/foundation').resolve()))
from capture import run
from analysis_dispatcher import CONTAINER_FORMAT
root=Path('artifacts/cohort/frontbridge-r1');root.mkdir(exist_ok=False)
state=json.loads(Path('artifacts/cohort/stack-r2/deployment.json').read_text())
def command(argv):
    p,m=run(argv,root/'commands',timeout_seconds=30)
    if p.returncode:raise RuntimeError(m['streams']['stderr']['path'])
    return p.stdout.decode().strip()
chosen=ipaddress.ip_network('10.245.85.0/29');configs=[]
for identifier in command(['docker','network','ls','--quiet']).split():
    configs.extend(json.loads(command(['docker','network','inspect',identifier,'--format','{{json .IPAM.Config}}'])) or [])
routes=command(['powershell','-NoProfile','-Command','Get-NetRoute -AddressFamily IPv4 | Select-Object -ExpandProperty DestinationPrefix']).split()
assert all(not chosen.overlaps(ipaddress.ip_network(r['Subnet'])) for r in configs)
assert all(not chosen.overlaps(ipaddress.ip_network(r)) for r in routes if r!='0.0.0.0/0')
(root/'prefix-check.json').write_text(json.dumps(dict(chosen=str(chosen),configs=configs,host_routes=routes),indent=2)+'\n')
network=state['prefix']+'-frontend'
command(['docker','network','create','--subnet',str(chosen),'--label','remission.task='+state['prefix'],network])
command(['docker','network','connect',network,state['service_container']])
(root/'service-selected-state.json').write_text(command(['docker','inspect',state['service_container'],'--format',CONTAINER_FORMAT])+'\n')
(root/'service-selected-networks.json').write_text(command(['docker','inspect',state['service_container'],'--format','{{json .NetworkSettings.Networks}}'])+'\n')
(root/'generator-selected-networks.json').write_text(command(['docker','inspect',state['generator_container'],'--format','{{json .NetworkSettings.Networks}}'])+'\n')
with urllib.request.urlopen('http://127.0.0.1:8784/health',timeout=5) as response:health=json.load(response)
assert health['database_instance_id']=='2cb3af32-c3d9-4297-b06d-56c3254f323a' and health['authority_generation']==1
(root/'health.json').write_text(json.dumps(health,indent=2)+'\n')
state.update(frontend_network=network,current_health=health,repair='Service-only additional frontend bridge; original container, DB, control and internal generator retained unchanged.')
(root/'deployment.json').write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps(dict(status='host health PASS',service=state['service_container'],frontend_network=network,health=health)),flush=True)
