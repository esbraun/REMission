import hashlib,json,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tooling/foundation'))
from capture import run
from run_pa3_compile import CONTAINER_FORMAT

evidence=Path(__file__).resolve().parent
def command(argv):
    p,m=run(argv,evidence/'commands',timeout_seconds=60)
    if p.returncode:raise RuntimeError('check failed; retained command '+m['streams']['stderr']['path'])
    return p.stdout

command([sys.executable,'-m','unittest','tests.methods.test_pa3_borrow_profile','tests.methods.test_pa3_compile_deadline','-v'])
# Windows has no resource module. These two host-only watchdog tests import its
# Linux probe but never call it; a deliberately empty import stub fails on use.
script="import sys,types,unittest;sys.modules['resource']=types.ModuleType('resource');s=unittest.defaultTestLoader.loadTestsFromNames(['tests.methods.test_pa3_numba.NumbaContrastTests.test_missing_first_fd_stops_before_native_phase','tests.methods.test_pa3_numba.NumbaContrastTests.test_finished_between_polls_after_deadline_cannot_qualify']);r=unittest.TextTestRunner(verbosity=2).run(s);sys.exit(not r.wasSuccessful())"
command([sys.executable,'-c',script])
name='remission-p1-native-sol-repair-controls-7c20'
selected=json.loads(command(['docker','inspect',name,'--format',CONTAINER_FORMAT]))
assert not selected['State']['Running']
assert set(selected)=={'Id','Image','State','Config','HostConfig','Mounts'}
assert set(selected['Config'])=={'User'}
assert set(selected['HostConfig'])=={'Memory','NanoCpus','NetworkMode','ReadonlyRootfs'}
assert selected['Image']=='sha256:24fcd00563071feb11d18f82acb8f85393dd28f6ba4aa2ecfe7ce17d0c13bda8'
optional=CONTAINER_FORMAT
for key in ['User','Memory','NanoCpus','NetworkMode','ReadonlyRootfs']:
    optional=optional.replace('"'+key+'")','"__missing_capture_control_'+key+'")')
missing=json.loads(command(['docker','inspect',name,'--format',optional]))
assert missing['Config']=={'User':None}
assert all(v is None for v in missing['HostConfig'].values())
assert selected['Id']==missing['Id'] and selected['State']==missing['State']
result=dict(source_head=command(['git','rev-parse','HEAD']).decode().strip(),
    existing_host_controls=7,actual_selected_capture='passed',actual_absent_optional_keys='passed',
    inspect_target=name,inspect_container_id=selected['Id'],no_container_mutations=True,
    no_numerical_execution=True,windows_resource_stub='two watchdog tests import-only; empty stub has no callable attributes')
(evidence/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
