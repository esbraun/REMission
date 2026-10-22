import json,sys,uuid
from pathlib import Path
sys.path.insert(0,str(Path('tooling/foundation').resolve()))
from capture import run
from analysis_dispatcher import CONTAINER_FORMAT
root=Path('artifacts/cohort/role-network-r1');root.mkdir(exist_ok=False)
state=json.loads(Path('artifacts/cohort/frontbridge-r1/deployment.json').read_text())
def command(argv,expected=0):
    p,m=run(argv,root/'commands',timeout_seconds=30)
    assert p.returncode==expected,m['streams']
    return p.stdout.decode().strip()
networks=json.loads(command(['docker','inspect',state['generator_container'],'--format','{{json .NetworkSettings.Networks}}']))
assert set(networks)=={state['network']}
address=networks[state['network']]['IPAddress']
common=['--cpus','2','--memory','2g','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=256m']
code="""import json,os,urllib.request,urllib.error
assert os.getuid()==10002
request=urllib.request.Request('http://GENERATOR_IP:8780/generate',data=json.dumps(dict(seed=1,index=0,patient_id='own-network-control',through_day=0,actions=[])).encode(),headers={'Content-Type':'application/json'})
reachable=False;count=None
try:
    with urllib.request.urlopen(request,timeout=2) as response:count=len(json.load(response)['records']);reachable=True
except (urllib.error.URLError,TimeoutError,ConnectionError):pass
print(json.dumps(dict(reachable=reachable,observed_records=count)),flush=True)
assert not reachable,'private generator reachable'
""".replace('GENERATOR_IP',address)
results={}
for label,network,expected in [('actual-none','none',0),('positive-network-exposure',state['network'],1)]:
    identifier=command(['docker','create','--name','remission-cohort-sol-'+label+'-'+uuid.uuid4().hex[:6],'--network',network,*common,state['images']['learner'],'python','-c',code])
    selected=json.loads(command(['docker','inspect',identifier,'--format',CONTAINER_FORMAT]))
    assert selected['HostConfig']['NetworkMode']==network and not selected['Mounts']
    (root/(label+'-created.json')).write_text(json.dumps(selected,indent=2)+'\n')
    actual=command(['docker','start','--attach',identifier],expected)
    result=json.loads(actual);assert result['reachable']==bool(expected)
    terminal=json.loads(command(['docker','inspect',identifier,'--format',CONTAINER_FORMAT]));assert terminal['State']['ExitCode']==expected
    (root/(label+'-terminal.json')).write_text(json.dumps(terminal,indent=2)+'\n')
    results[label]=result
(root/'result.json').write_text(json.dumps(dict(image=state['images']['learner'],results=results),indent=2)+'\n')
print(json.dumps(results))
