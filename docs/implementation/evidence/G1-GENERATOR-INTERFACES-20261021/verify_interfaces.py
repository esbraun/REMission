"""Current interface candidate commands, raw outputs and source/image binding."""
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
BASE='69e6ae9dc5bf85ddbf39976d2ce4ce70bce1ea1e'
RUNTIME='sha256:ce346feace2ae607ebd574e1bb681d594c9b676c06b56f8ba8d50b858a577faa'
IMAGE_PREFIX=os.environ.get('REMISSION_INTERFACE_IMAGE_PREFIX','remission-interfaces')


def main():
    previous=ROOT/'docs/implementation/evidence/G1-FOUNDATION-20261021/final-integration-check-results.json'
    commands=[row['command'] for row in json.loads(previous.read_text())['checks'][:10]]
    for command in commands:
        if command[0].lower().endswith('python.exe'):command[0]=sys.executable
        for index,value in enumerate(command):
            if value.startswith('type=bind,source='):command[index]=f'type=bind,source={ROOT.as_posix()},target=/workspace,readonly'
    container=['docker','run','--rm','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges:true','--tmpfs','/tmp:rw,noexec,nosuid,size=512m','--mount',f'type=bind,source={ROOT.as_posix()},target=/workspace,readonly','--workdir','/workspace','--env','PYTHONPATH=/workspace',RUNTIME]
    commands += [container+['python','-m','contracts.runs.export','--check'],
        container+['python','-m','unittest','discover','-s','tests/run_contracts','-v'],
        container+['python','-m','unittest','discover','-s','tests/integration/replay','-v'],
        [sys.executable,str(OUT/'preservation.py')],
        ['git','diff','--check',BASE],
        ['docker','run','--rm','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges:true','--tmpfs','/tmp:rw,noexec,nosuid,size=64m',f'{IMAGE_PREFIX}-tests:candidate'],
        [sys.executable,str(OUT/'verify_consumers.py')]]
    records=[]
    for command in commands:
        start=datetime.now(timezone.utc).isoformat();result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
        records.append(dict(command=command,started_utc=start,finished_utc=datetime.now(timezone.utc).isoformat(),exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr))
        print('PASS' if result.returncode==0 else 'FAIL',' '.join(command[-4:]),flush=True)
    (OUT/'current-interface-check-results.json').write_text(json.dumps(dict(base=BASE,observed_parent=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),candidate='Exact final commit supplied in handoff; no self-referential hash',checks=records,limits=['Contract/IO fixtures only; no production generator/filter/calibration/truth execution or statistical acceptance','Unchanged costly fits and full browser flows not repeated; accepted foundation retained','Actual producer independence and 60000-filter-per-level throughput/memory/storage preflight remain mandatory later']),indent=2)+'\n',encoding='utf-8')
    sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for prefix in ['contracts/runs','services/foundation','services/learner'] for p in (ROOT/prefix).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    for name in ['tooling/foundation/service.Dockerfile','tooling/foundation/learner.Dockerfile','tooling/foundation/requirements.lock','tooling/library/requirements.lock']:
        sources[name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
    images={name:subprocess.check_output(['docker','image','inspect',f'{IMAGE_PREFIX}-{name}:candidate','--format','{{.Id}}'],cwd=ROOT,text=True).strip() for name in ('service','learner','tests')}
    assert subprocess.check_output(['docker','image','inspect','remission-foundation-runtime:candidate','--format','{{.Id}}'],cwd=ROOT,text=True).strip()==RUNTIME,'qualified runtime tag drift'
    (OUT/'current-source-and-images.json').write_text(json.dumps(dict(base=BASE,runtime=RUNTIME,images=images,source_sha256=sources,source_mount='Own checkout only; consumer probes mount public-only fixture bytes, no checkout',claim='No source/lock change outside owned bounded interface scope; old own/reviewer stacks and DBs untouched'),indent=2)+'\n',encoding='utf-8')
    if any(record['exit_code'] for record in records):raise SystemExit(1)


if __name__=='__main__':main()
