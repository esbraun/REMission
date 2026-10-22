"""Bounded exact copied-service/source check; never mounts application data."""
import hashlib,json,subprocess
from pathlib import Path

root=Path.cwd();out=root/'artifacts/appt-serving-20261022'
paths=sorted(str(p.relative_to(root)).replace('\\','/') for p in
    [*root.joinpath('services/foundation').glob('*.py'),*root.joinpath('services/foundation/migrations').glob('*.sql'),
     *[root/'contracts/domain'/name for name in ['analysis.py','borrowing.py','borrow_runtime.py','cohort.py','cohort_runtime.py']]])
expected={p:dict(sha256=hashlib.sha256((root/p).read_bytes()).hexdigest(),bytes=(root/p).stat().st_size) for p in paths}
code="import hashlib,json,pathlib; import services.foundation.app; paths="+repr(paths)+"; result={'files':{p:{'sha256':hashlib.sha256(pathlib.Path('/app',p).read_bytes()).hexdigest(),'bytes':pathlib.Path('/app',p).stat().st_size} for p in paths},'forbidden_roles_present':{p:pathlib.Path('/app',p).exists() for p in ['methods','services/learner','services/generator']}}; print(json.dumps(result,sort_keys=True))"
command=['docker','run','--rm','--network','none','--cpus','2','--memory','2g','--read-only','--cap-drop','ALL',
    '--security-opt','no-new-privileges','--tmpfs','/tmp:rw,noexec,nosuid,size=128m',
    'remission-appt-serving-261022-service:c7d6a827','python','-c',code]
result=subprocess.run(command,capture_output=True)
(out/'source-audit.stdout').write_bytes(result.stdout);(out/'source-audit.stderr').write_bytes(result.stderr)
assert result.returncode==0,result.stderr.decode(errors='replace')
actual=json.loads(result.stdout);assert actual['files']==expected
assert not any(actual['forbidden_roles_present'].values())
web={str(p.relative_to(root)).replace('\\','/'):dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
    for p in [*root.joinpath('web/src').glob('*'),root/'web/package.json',root/'web/package-lock.json'] if p.is_file()}
manifest=dict(source_head=subprocess.check_output(['git','rev-parse','HEAD']).decode().strip(),
    service_image=subprocess.check_output(['docker','image','inspect','remission-appt-serving-261022-service:c7d6a827','--format','{{.Id}}']).decode().strip(),
    command=command,exit_code=result.returncode,copied_service=actual,web_source=web)
(out/'source-audit.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print('Exact copied service files/imports/role separation passed; source and UI manifest saved.')
