"""Read-only integrated qualifier; --record explicitly saves command results."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[5]
BASE='f11e90536b635a7db08cfed640445bec197a415c'
PREVIOUS='d84203709b0164a0824913950c1d7cd7be25a2fb'
IMAGE='sha256:be4bbf7978bb318b8c3d2901e8e9510b746aa8554d5c0dbfc8eea5928d9f07f7'


def main():
    p=argparse.ArgumentParser();p.add_argument('--record',action='store_true');a=p.parse_args()
    docker=['docker','run','--rm','--network','none','--mount',f'type=bind,source={ROOT.as_posix()},target=/workspace,readonly',IMAGE]
    commands=[[sys.executable,'-m','pip','check'],
        [sys.executable,'-m','contracts.domain.export','--check'],
        [sys.executable,'-m','contracts.dgp.export','--check'],
        [sys.executable,'-m','contracts.artifacts.ope_export','--check'],
        [sys.executable,'-m','unittest','discover','-s','tests/contracts','-v'],
        [sys.executable,'-m','unittest','discover','-s','tests/library','-v'],
        docker+['python','-m','unittest','discover','-s','tests/library/dr','-v'],
        [sys.executable,'docs/implementation/check-ledger-20261020.py'],
        docker+['python','-c',"import subprocess;subprocess.check_call(['python','-m','pip','check']);subprocess.check_call(['python','-m','tooling.library.check-runtime'])"],
        docker+['python','-m','tooling.library.verify_dr'],
        ['git','diff','--quiet',PREVIOUS,'--','docs/implementation/evidence/G0-LIB',':!docs/implementation/evidence/G0-LIB/DR/**'],
        ['git','diff','--quiet',PREVIOUS,'--','tooling/library/requirements.lock','tooling/library/r-packages.lock.csv','tooling/library/python.Dockerfile','tooling/library/offline-r.Dockerfile'],
        ['git','diff','--quiet',BASE,'--','contracts/domain','contracts/dgp','tests/contracts','docs/implementation/dgp-decisions.md','docs/implementation/workflow-contract.md','docs/implementation/workflow-sketches.md','docs/spec/01-estimands-and-contracts.md','docs/spec/dgp-reference.md'],
        ['git','diff','--check',BASE]]
    results=[]
    for cmd in commands:
        started=datetime.now(timezone.utc).isoformat();r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
        results.append(dict(command=cmd,started_utc=started,finished_utc=datetime.now(timezone.utc).isoformat(),exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr))
        print('PASS' if r.returncode==0 else 'FAIL',' '.join(cmd[1:]))
    if a.record:
        Path(__file__).with_name('check-results.json').write_text(json.dumps(dict(package='G0-LIB-DR',base=BASE,
            candidate='Exact SHA supplied by committed handoff/review; no self-reference',created_utc=datetime.now(timezone.utc).isoformat(),
            contract_python=platform.python_version(),image=IMAGE,checks=results,
            limits=['Bounded actual conditional DR qualification only','Unchanged expensive fits not rerun; historical diagnostic failures retained',
                    'No final G4 statistical/consumer/clinical/human/G0 acceptance']),indent=2)+'\n',encoding='utf-8')
    if any(r['exit_code'] for r in results):raise SystemExit(1)


if __name__=='__main__':main()
