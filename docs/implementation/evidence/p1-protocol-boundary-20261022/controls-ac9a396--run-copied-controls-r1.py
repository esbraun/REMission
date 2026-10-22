import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path('tooling/foundation').resolve()))
from capture import run
from audit_pa3_native_readiness import CONTAINER_FORMAT
root=Path('artifacts/p1/controls-ac9a396');root.mkdir(parents=True,exist_ok=False)
parent,metadata=run(['docker','image','inspect','remission-p1-native-sol-434306c-controls:candidate','--format','{{json .Id}}'],root/'commands',timeout_seconds=30)
assert json.loads(parent.stdout)=='sha256:97894f147c5640aa31b8349a52e37329575218a2100c41105fffccbf60ba844a'
build,metadata=run(['docker','build','--network','none','--file','artifacts/p1/controls-ac9a396.Dockerfile','--tag','remission-p1-native-sol-ac9a396-controls:candidate','.'],root/'commands',timeout_seconds=60)
assert build.returncode==0
resolved,metadata=run(['docker','image','inspect','remission-p1-native-sol-ac9a396-controls:candidate','--format','{{json .Id}}'],root/'commands',timeout_seconds=30)
image=json.loads(resolved.stdout)
name='remission-p1-native-sol-controls-ac9a396'
argv=['docker','run','--name',name,'--network','none','--cpus','.5','--memory','1g','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=256m','--user','10001:10001','--env','MPLCONFIGDIR=/tmp/matplotlib','--env','PYTENSOR_FLAGS=base_compiledir=/tmp/pytensor,floatX=float64',image,'python','/app/run_p1_controls.py']
p,m=run(argv,root/'commands',timeout_seconds=180)
if p.returncode==124:
    run(['docker','stop','--time','10',name],root/'commands',timeout_seconds=30)
state_result,state_meta=run(['docker','inspect',name,'--format',CONTAINER_FORMAT],root/'commands',timeout_seconds=30)
state=json.loads(state_result.stdout)
(root/'actual-state.json').write_text(json.dumps(state,sort_keys=True,indent=2)+'\n')
assert not state['State']['Running'],'owned controls did not terminate'
assert p.returncode==0 and state['State']['ExitCode']==0 and not state['State']['OOMKilled'],'copied controls failed; retain exact streams'
line=next(json.loads(s) for s in p.stdout.decode().splitlines() if s.startswith('{') and json.loads(s).get('kind')=='p1-owned-v2-boundary-fixture')
raw=(json.dumps(line['input'],sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
(root/'input.json').write_bytes(raw)
result={'status':'passed','actual_image':image,'container':name,'tests':'copied suite; exact test count/timing in original stderr','public_owned_input_sha256':hashlib.sha256(json.dumps(line['input'],sort_keys=True,separators=(',',':')).encode()).hexdigest(),'physical_input_sha256':hashlib.sha256(raw).hexdigest(),'purpose':line['input']['purpose'],'family':line['input']['family'],'cohort_count':len(line['input']['cohort']),'elapsed_seconds':m['elapsed_seconds'],'no_model_execution':True,'no_source_or_data_mounts':not state['Mounts']}
(root/'result.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
print(json.dumps(result,sort_keys=True))
