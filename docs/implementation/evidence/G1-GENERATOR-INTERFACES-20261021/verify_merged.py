"""Observed read-only merged foundation checks from this interface checkout."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
BASE = '69e6ae9dc5bf85ddbf39976d2ce4ce70bce1ea1e'


def main():
    prior = ROOT / 'docs/implementation/evidence/G1-FOUNDATION-20261021'
    commands = [row['command'] for row in json.loads((prior/'final-integration-check-results.json').read_text(encoding='utf-8'))['checks']]
    for command in commands:
        if command[0].lower().endswith('python.exe'):
            command[0] = sys.executable
        for index, value in enumerate(command):
            if value.startswith('type=bind,source='):
                command[index] = f'type=bind,source={ROOT.as_posix()},target=/workspace,readonly'
    runtime = json.loads((prior/'build-source-and-images.json').read_text(encoding='utf-8'))['images']['runtime']
    commands += [['git','diff','--quiet','3179f3d2fcc7c9f285129b0272e868d413ced089',BASE,'--','services','web','contracts','tests','tooling'],
        ['docker','run','--rm','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges:true','--tmpfs','/tmp:rw,noexec,nosuid,size=64m','--mount',f'type=bind,source={ROOT.as_posix()},target=/workspace,readonly','--workdir','/workspace','--env','PYTHONPATH=/workspace',runtime,'python','-m','unittest','discover','-s','tests/integration/replay','-v']]
    records=[]
    for command in commands:
        start=datetime.now(timezone.utc).isoformat()
        result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
        records.append(dict(command=command,started_utc=start,finished_utc=datetime.now(timezone.utc).isoformat(),exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr))
        print('PASS' if not result.returncode else 'FAIL',command[-1],flush=True)
    (OUT/'merged-foundation-check-results.json').write_text(json.dumps(dict(base=BASE,observed_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),checks=records,limits=['Read-only merged executable source verification; no broad browser or expensive fits repeated']),indent=2)+'\n',encoding='utf-8')
    if any(row['exit_code'] for row in records):sys.exit(1)


if __name__ == '__main__':main()
