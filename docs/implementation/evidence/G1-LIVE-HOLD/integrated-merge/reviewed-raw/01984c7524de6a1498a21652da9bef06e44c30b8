"""Bounded read-only checks with unique raw captures; no historical output writes."""
import argparse,json
from pathlib import Path
import uuid
from capture import run

ROOT=Path(__file__).resolve().parents[2]
RUNTIME='sha256:ce346feace2ae607ebd574e1bb681d594c9b676c06b56f8ba8d50b858a577faa'
CHECKS={
 'domain':[['-m','unittest','discover','-s','tests/contracts','-v']],
 'runs':[['-m','unittest','discover','-s','tests/run_contracts','-v']],
 'service':[['-m','unittest','discover','-s','tests/integration/replay','-v']],
 'artifacts':[['-m','unittest','discover','-s','tests/library','-v'],['-m','unittest','discover','-s','tests/library/dr','-v']],
 'schemas':[['-m',module,'--check'] for module in ['contracts.domain.export','contracts.dgp.export','contracts.runs.export','contracts.domain.export_v2','contracts.runs.export_v2','contracts.service.export']],
 'runtime':[['-m','pip','check'],['tooling/foundation/qualify.py']],
}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--group',choices=CHECKS,action='append',required=True)
    parser.add_argument('--evidence',type=Path,required=True);args=parser.parse_args()
    checks=[]
    for group in args.group:
        for arguments in CHECKS[group]:
            command=['docker','run','--rm','--name','remission-lh-check-'+uuid.uuid4().hex[:12],'--network','none','--cpus','2','--memory','2g','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--tmpfs','/tmp:rw,noexec,nosuid,size=256m',
                '-e','PYTHONDONTWRITEBYTECODE=1','-e','PYTHONPATH=/source','--mount',f'type=bind,source={ROOT.as_posix()},target=/source,readonly','-w','/source',RUNTIME,'python',*arguments]
            result,metadata=run(command,args.evidence)
            checks.append(dict(group=group,metadata=metadata));print(json.dumps(dict(group=group,command=arguments,exit=result.returncode,stdout=metadata['streams']['stdout']['path'],stderr=metadata['streams']['stderr']['path'])),flush=True)
            if result.returncode:
                print(result.stderr.decode(errors='replace'),flush=True)
                raise SystemExit(result.returncode)
    path=args.evidence/(uuid.uuid4().hex+'-checks.json');path.write_text(json.dumps(checks,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
