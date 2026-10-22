import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path('tooling/foundation').resolve()))
from capture import run
from audit_pa3_native_readiness import CONTAINER_FORMAT
root=Path('artifacts/p1/repair-boundary-7c20');root.mkdir(parents=True,exist_ok=False)
images=json.loads(Path('artifacts/p1/repair-copy-7c20/images.json').read_text())
prefix='remission-p1-native-sol-7c20'
def save(name,v):(root/name).write_text(json.dumps(v,sort_keys=True,indent=2)+'\n',encoding='utf-8')
def command(argv,expected=0):
    p,m=run(argv,root/'commands',timeout_seconds=45)
    if p.returncode!=expected:raise RuntimeError('boundary command unexpected status; see '+m['streams']['stderr']['path'])
    return p
def state(name):return json.loads(command(['docker','inspect',name,'--format',CONTAINER_FORMAT]).stdout)
common=['--cpus','.5','--memory','512m','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=128m']
volume=prefix+'-input';network=prefix+'-boundary';generator=prefix+'-generator'
assert not command(['docker','volume','ls','-q','--filter','name=^'+volume+'$']).stdout.strip()
assert not command(['docker','network','ls','-q','--filter','name=^'+network+'$']).stdout.strip()
command(['docker','volume','create','--label','remission.task='+prefix,volume])
helper=prefix+'-stage'
command(['docker','create','--name',helper,'--network','none',*common,'--cap-add','CHOWN','--user','0:0','--mount','type=volume,source='+volume+',target=/input',images['learner']['Id'],'python','-c',"import os;os.chmod('/input',0o755);os.chmod('/input/input.json',0o444);os.chown('/input/input.json',10002,10002)"])
input_path=Path('artifacts/p1/repair-controls-7c20/input.json').resolve()
command(['docker','cp',str(input_path),helper+':/input/input.json'])
command(['docker','start','--attach',helper])
save('stage-state.json',state(helper))
command(['docker','network','create','--label','remission.task='+prefix,network])
command(['docker','run','--detach','--name',generator,'--label','remission.task='+prefix,'--network',network,*common,images['generator']['Id']])
generator_state=state(generator);save('generator-running-state.json',generator_state)
address=generator_state['Networks'][network]['IPAddress']
assert generator_state['Image']==images['generator']['Id'] and generator_state['User']=='20000:20000' and generator_state['Ports']=={} and not generator_state['Mounts']
service=prefix+'-service-purity'
purity="import importlib.util,json,pathlib,sys;import services.foundation.app,services.foundation.protocol;assert importlib.util.find_spec('services.generator') is None;assert not pathlib.Path('/app/services/generator').exists();assert 'pymc' not in sys.modules;print(json.dumps({'service_imports':True,'private_generator_absent':True,'pymc_not_imported':True}))"
command(['docker','run','--name',service,'--network','none',*common,images['service']['Id'],'python','-c',purity])
save('service-purity-state.json',state(service))
states={};outcomes={}
try:
    for label,net,ro,source,exitcode,reason in [('source-exposed','none',True,True,1,'private source exposed'),('input-rw','none',False,False,1,'public input is not read-only'),('connected',network,True,False,1,'private generator reached'),('positive','none',True,False,0,None)]:
        name=prefix+'-probe-'+label
        argv=['docker','run','--name',name,'--network',net,*common,'--user','10002:10002','--mount','type=volume,source='+volume+',target=/input'+(',readonly' if ro else '')]
        if source:argv+=['--mount','type=bind,source='+str(Path('services/generator').resolve())+',target=/app/services/generator,readonly']
        argv+=['--env','P1_GENERATOR_URL=http://'+address+':8780/generate',images['learner']['Id'],'python','/app/protocol_probe.py']
        p=command(argv,expected=exitcode)
        if reason:assert reason in p.stderr.decode(errors='replace')
        else:
            result=json.loads(p.stdout.decode().splitlines()[-1]);assert result['status']=='passed' and not result['execution_admitted']
            save('public-boundary-result.json',result)
        states[label]=state(name)
        assert not states[label]['State']['Running'] and states[label]['State']['ExitCode']==exitcode and not states[label]['State']['OOMKilled']
        outcomes[label]={'expected_exit':exitcode,'actual_exit':states[label]['State']['ExitCode'],'intended_failure_reason':reason,'stdout_sha256':hashlib.sha256(p.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(p.stderr).hexdigest()}
        save('probe-states.json',states);save('probe-outcomes.json',outcomes)
finally:
    command(['docker','stop','--time','10',generator])
    save('generator-terminal-state.json',state(generator))
save('result.json',{'status':'passed','genuine_owned_fixture_input_sha256':hashlib.sha256(json.dumps(json.loads(input_path.read_text()),sort_keys=True,separators=(',',':')).encode()).hexdigest(),'positive_and_three_required_negatives':True,'HTTP_errors_count_as_reachable':True,'no_fit_execution':True,'own_isolated_namespace':prefix,'retained_public_input_volume':volume,'retained_network':network,'no_active8780_resources_used':True})
print(json.dumps({'boundary_positive':True,'negatives':list(outcomes)[:-1],'service_purity':True,'private_generator_terminal':True,'own_namespace':prefix},sort_keys=True))
