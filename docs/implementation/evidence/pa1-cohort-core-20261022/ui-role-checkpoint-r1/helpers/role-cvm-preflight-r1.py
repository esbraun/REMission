import json,sys
from pathlib import Path
sys.path.insert(0,str(Path('tooling/foundation').resolve()))
from capture import run
from analysis_dispatcher import CONTAINER_FORMAT
root=Path('artifacts/cohort/role-cvm-preflight-r1');root.mkdir(exist_ok=False)
def command(argv,timeout=120):
    p,m=run(argv,root/'commands',timeout_seconds=timeout)
    print(json.dumps(dict(exit=p.returncode,streams=m['streams'])),flush=True)
    return p
image=json.loads(Path('artifacts/cohort/roles-r2/images.json').read_text())['images']['learner']
code="""import json
import pytensor
from pytensor.compile.mode import get_default_mode
from methods.visit.borrow_execution import compilation_options,optimizer_identity
from pytensor.link.c.cvm import CVM
mode=get_default_mode()
result=dict(floatX=pytensor.config.floatX,default_linker=type(mode.linker).__name__,optimizer=optimizer_identity(mode.provided_optimizer),CVM=CVM.__module__+'.'+CVM.__qualname__)
try:compilation_options();result['guard']='PASS'
except ValueError as error:result['guard']='FAIL';result['reason']=str(error)
print(json.dumps(result))
"""
p=command(['docker','create','--name','remission-cohort-sol-cvm-preflight-r1','--network','none','--cpus','2','--memory','2g',
    '--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--tmpfs','/tmp:rw,exec,nosuid,nodev,size=512m',image,'python','-c',code])
assert p.returncode==0
identifier=p.stdout.decode().strip()
p=command(['docker','start','--attach',identifier])
terminal=command(['docker','inspect',identifier,'--format',CONTAINER_FORMAT],30)
(root/'terminal.json').write_bytes(terminal.stdout)
if p.returncode==0:(root/'result.json').write_bytes(p.stdout)
raise SystemExit(p.returncode)
