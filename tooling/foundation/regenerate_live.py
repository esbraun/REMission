"""Generate only the accepted service contract products in a qualified runtime."""
import json
from pathlib import Path
from capture import run

root=Path(__file__).resolve().parents[2]
command=['docker','run','--rm','--network','none','--cpus','2','--memory','2g','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--tmpfs','/tmp:rw,noexec,nosuid,size=128m','-e','PYTHONDONTWRITEBYTECODE=1','-e','PYTHONPATH=/source','--mount',f'type=bind,source={root.as_posix()},target=/source,readonly','-w','/source','sha256:ce346feace2ae607ebd574e1bb681d594c9b676c06b56f8ba8d50b858a577faa','python','-m','contracts.service.export','--stdout']
result,metadata=run(command,root/'docs/implementation/evidence/G1-LIVE-HOLD/c')
if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace'))
products=json.loads(result.stdout)
for name,value in products.items():
    path=root/'contracts/service'/name
    assert path.resolve().is_relative_to((root/'contracts/service').resolve())
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes((json.dumps(value,sort_keys=True,indent=2,ensure_ascii=True)+'\n').encode())
print(json.dumps(dict(products=sorted(products),capture=metadata['streams']['stdout']['path'])))
