import json,sys
from pathlib import Path
sys.path.insert(0,str(Path('tooling/foundation').resolve()))
from capture import run

root=Path('artifacts/p2/copy-r2');root.mkdir(parents=True,exist_ok=False)
def command(argv,seconds=60):
    p,m=run(argv,root/'commands',timeout_seconds=seconds)
    if p.returncode:raise RuntimeError('retained failing command '+m['streams']['stderr']['path'])
    return p.stdout.decode().strip()
bases=dict(service='sha256:0df955d338db2d118c8d705d7d01ea6dbb7c9d188c79618a8c17a605075a4a5d',controls='sha256:24fcd00563071feb11d18f82acb8f85393dd28f6ba4aa2ecfe7ce17d0c13bda8')
for role,image in bases.items():
    assert command(['docker','image','inspect',image,'--format','{{.Id}}'])==image
    command(['docker','tag',image,'remission-p2-sol-'+role+'-base:5c95'])
images={}
for role in bases:
    tag='remission-p2-sol-'+role+':r2'
    command(['docker','build','--file','tooling/foundation/p2-loop.Dockerfile','--target',role,
        '--build-arg','SERVICE_BASE=remission-p2-sol-service-base:5c95','--build-arg','CONTROLS_BASE=remission-p2-sol-controls-base:5c95','--tag',tag,'.'],120)
    images[role]=command(['docker','image','inspect',tag,'--format','{{.Id}}'])
result=dict(source_head=command(['git','rev-parse','HEAD']),bases=bases,images=images)
(root/'images.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
limits=['--network','none','--cpus','0.5','--memory','1g','--read-only','--cap-drop','ALL',
    '--security-opt','no-new-privileges','--tmpfs','/tmp:rw,nosuid,nodev,noexec,size=256m','--user','10001:10001']
for name,tail in [('loop',['-m','unittest','test_nof1_loop.Nof1LoopTests','tests.contracts.test_nof1_clock','-v']),('p1',['/app/run_p1_controls.py'])]:
    container='remission-p2-sol-copied-'+name+'-r2'
    command(['docker','run','--name',container,*limits,'--entrypoint','python',images['controls'],*tail],120)
    print(name+' copied controls PASS',flush=True)
(root/'result.json').write_text(json.dumps(result|dict(loop_and_inherited=True,p1_controls=True,no_fitting=True),indent=2)+'\n')
