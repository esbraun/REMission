"""Copied-role light checks only: no model construction, compile or fitted output."""
import hashlib,json,sys,uuid
from pathlib import Path
sys.path.insert(0,str(Path('tooling/foundation').resolve()))
from capture import run
from analysis_dispatcher import CONTAINER_FORMAT
root=Path('artifacts/cohort/role-checks-r3');root.mkdir(exist_ok=False)
(root/'input').mkdir();(root/'output').mkdir()
images=json.loads(Path('artifacts/cohort/roles-r2/images.json').read_text())['images']
inventory=json.loads(Path('docs/implementation/poc-cohort-role-source-inventory-20261022.json').read_text())['roles']
common=['--cpus','2','--memory','2g','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=256m']
numeric=[v.replace('noexec','exec').replace('size=256m','size=512m') for v in common]
records=[]
def command(argv,expected=0):
    p,m=run(argv,root/'commands',timeout_seconds=120)
    records.append(dict(command=m['command'],exit=p.returncode,streams=m['streams']))
    (root/'commands-summary.json').write_text(json.dumps(records,indent=2)+'\n')
    assert p.returncode==expected,(p.returncode,m['streams'])
    return p.stdout.decode().strip()
source=Path('artifacts/cohort/stack-r2/bootstrap-source').resolve()
producer="""from pathlib import Path
from tests.contracts.test_cohort import database,export
from contracts.domain.cohort import CohortHistory,make_cohort_input
from contracts.domain.analysis import canonical,sha
db=database();cohort=export(db);db.close()
Path('/out/interactive.json').write_text(canonical(make_cohort_input(cohort,'cohort-copy-boundary').model_dump(mode='json')))
value=cohort.model_dump(mode='json');value['manifest'].update(scope='research',research_run_id='explicit-contract-fixture',research_execution='contract_fixture');value['manifest_sha256']=sha(value['manifest'])
fixture=CohortHistory.model_validate_json(canonical(value))
Path('/out/fixture.json').write_text(canonical(make_cohort_input(fixture,'cohort-copy-fixture-boundary').model_dump(mode='json')))
print('Two typed diagnostic inputs; renamed archived records, never engine research input or fit evidence.')
"""
command(['docker','run','--rm','--network','none',*common,'--user','10001:10001','--env','PYTHONPATH=/source','--workdir','/source',
    '--mount',f'type=bind,source={source},target=/source,readonly','--mount',f'type=bind,source={(root/"input").resolve()},target=/out',
    'sha256:24fcd00563071feb11d18f82acb8f85393dd28f6ba4aa2ecfe7ce17d0c13bda8','python','-c',producer])
results={}
for role,uid in [('service',10001),('learner',10002)]:
    expected=inventory[role]
    code="import hashlib,importlib.util,json,os,sys;from pathlib import Path;expected="+repr(expected)+";assert os.getuid()=="+str(uid)+";assert {p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in expected}==expected;assert not Path('/app/services/generator').exists();assert not Path('/app/evaluation').exists();assert not Path('/app/contracts/dgp').exists();assert not Path('/data/remission.sqlite').exists();assert not Path('/var/run/docker.sock').exists();"
    if role=='service':code+="import services.foundation.app;assert 'pymc' not in sys.modules;assert 'services.learner' not in sys.modules;"
    else:code+="import services.learner.cohort_worker;assert importlib.util.find_spec('services.foundation') is None;"
    code+="print(json.dumps(dict(role="+repr(role)+",uid=os.getuid(),copied_files=len(expected),private_sources_absent=True)))"
    name='remission-cohort-sol-role-'+role+'-'+uuid.uuid4().hex[:6]
    identifier=command(['docker','create','--name',name,'--network','none',*(numeric if role=='learner' else common),images[role],'python','-c',code])
    selected=json.loads(command(['docker','inspect',identifier,'--format',CONTAINER_FORMAT]))
    assert selected['Image']==images[role] and selected['Config']['User']==f'{uid}:{uid}'
    assert selected['HostConfig']['NetworkMode']=='none' and not selected['Mounts']
    output=command(['docker','start','--attach',identifier])
    (root/(role+'-terminal.json')).write_text(command(['docker','inspect',identifier,'--format',CONTAINER_FORMAT])+'\n')
    results[role]=dict(container=identifier,output=json.loads(output))
denial="""import json,os
from pathlib import Path
from contracts.domain.borrowing import parse_input
from contracts.domain.cohort import require_executable
from services.learner.analysis_worker import run
from services.learner.cohort_worker import run as direct
assert not Path('/app/services/generator').exists(),'private source exposed'
mounts=[line.split() for line in Path('/proc/self/mountinfo').read_text().splitlines()]
assert any(p[4]=='/input' and 'ro' in p[5].split(',') for p in mounts),'public input is not read-only'
denials=[]
for name,reason in [('interactive','qualification'),('fixture','contract fixture')]:
    path=Path('/input')/(name+'.json');value=parse_input(path.read_bytes())
    for stage,call in [('contract',lambda:require_executable(value)),('dispatch',lambda:run(path,Path('/out')/name)),('worker',lambda:direct(value,Path('/out')/(name+'-direct')))]:
        try:call()
        except ValueError as error:
            assert reason in str(error),str(error);denials.append(dict(input=name,stage=stage,reason=str(error)))
        else:raise AssertionError('unqualified cohort was admitted')
assert not any(p.is_file() for p in Path('/out').rglob('*'))
print(json.dumps(dict(typed_inputs=2,denials=denials,results_written=0,models_built=0)))
"""
for variant,expected in [('proper',0),('source-exposed',1),('input-writeable',1)]:
    mounts=['--mount',f'type=bind,source={(root/"input").resolve()},target=/input'+('' if variant=='input-writeable' else ',readonly'),
        '--mount',f'type=bind,source={(root/"output").resolve()},target=/out']
    if variant=='source-exposed':mounts+=['--mount',f'type=bind,source={(source/"services/generator")},target=/app/services/generator,readonly']
    identifier=command(['docker','create','--name','remission-cohort-sol-'+variant+'-'+uuid.uuid4().hex[:6],'--network','none',*numeric,*mounts,images['learner'],'python','-c',denial])
    selected=json.loads(command(['docker','inspect',identifier,'--format',CONTAINER_FORMAT]))
    (root/(variant+'-created.json')).write_text(json.dumps(selected,indent=2)+'\n')
    output=command(['docker','start','--attach',identifier],expected)
    terminal=json.loads(command(['docker','inspect',identifier,'--format',CONTAINER_FORMAT]))
    assert terminal['State']['ExitCode']==expected and not terminal['State']['OOMKilled']
    (root/(variant+'-terminal.json')).write_text(json.dumps(terminal,indent=2)+'\n')
    if variant=='proper':results['closed_boundary']=json.loads(output)
    else:
        stderr=root/'commands'/records[-2]['streams']['stderr']['path']
        assert ('private source exposed' if variant=='source-exposed' else 'public input is not read-only') in stderr.read_text()
        results[variant]='Expected actual denial control failed as required'
(root/'result.json').write_text(json.dumps(dict(source='45d35071036ca3b635ae60e97ca04e924d98f74e',images=images,results=results,no_fit=True),indent=2)+'\n')
print(json.dumps(results),flush=True)
