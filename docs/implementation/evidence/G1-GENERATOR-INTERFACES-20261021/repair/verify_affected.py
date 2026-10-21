"""Affected current-source rerun after level/provenance/runner isolation repairs."""
from datetime import datetime,timezone
import hashlib
import json
import runpy
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent.parent/'repair-levels'


def main():
    if Path.cwd().resolve()!=ROOT.resolve():raise ValueError('verification cwd must match executing checkout')
    helpers=runpy.run_path(str(Path(__file__).with_name('command_paths.py')))
    helpers['owned_path'](OUT,ROOT)
    prior=json.loads((OUT/'repair-check-results.json').read_text());checks=[]
    commands=helpers['rebind_commands']([prior['checks'][index]['command'] for index in (10,11,13,14,7)],ROOT,sys.executable)
    for command in commands:
        start=datetime.now(timezone.utc).isoformat()
        result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
        checks.append(dict(command=command,cwd=ROOT.as_posix(),started_utc=start,finished_utc=datetime.now(timezone.utc).isoformat(),exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr))
        print('PASS' if not result.returncode else 'FAIL',' '.join(command[-4:]),flush=True)
    (OUT/'final-affected-check-results.json').write_text(json.dumps(dict(base=prior['base'],rejected_head=prior['rejected_head'],prior_full_run='repair-check-results.json',reason='Verified symptom/probability truth final levels and reported probability references; both replay runners execute only their own checkout',checks=checks,claim='Current private contract source; current public image bytes and prior18-command integrated results remain separately preserved'),indent=2)+'\n',encoding='utf-8')
    path=OUT/'source-and-images.json';before=path.read_bytes();(OUT/'source-and-images.before-affected-recheck.json').write_bytes(before)
    manifest=json.loads(before);manifest['private_contract_source_sha256']={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'contracts/runs').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    manifest['final_private_qualification']='final-affected-check-results.json; public COPY inputs/images unchanged during affected replay'
    path.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    if any(row['exit_code'] for row in checks):raise SystemExit(1)


if __name__=='__main__':main()
