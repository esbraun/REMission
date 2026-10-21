"""Affected current-source rerun after partial count/uncertainty consistency fix."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent


def main():
    prior=json.loads((OUT/'repair-check-results.json').read_text());checks=[]
    for index in (10,11,13,14,7):
        command=prior['checks'][index]['command'];start=datetime.now(timezone.utc).isoformat()
        result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
        checks.append(dict(command=command,started_utc=start,finished_utc=datetime.now(timezone.utc).isoformat(),exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr))
        print('PASS' if not result.returncode else 'FAIL',' '.join(command[-4:]),flush=True)
    (OUT/'final-affected-check-results.json').write_text(json.dumps(dict(base=prior['base'],rejected_head=prior['rejected_head'],prior_full_run='repair-check-results.json',reason='Derived eligible counts/point means/nested uncertainty remain consistent even when symptom precision is pending beside computed event components',checks=checks,claim='Current private contract source; unchanged public image bytes and prior18-command integrated results remain separately preserved'),indent=2)+'\n',encoding='utf-8')
    path=OUT/'source-and-images.json';before=path.read_bytes();(OUT/'source-and-images.before-partial-count-guard.json').write_bytes(before)
    manifest=json.loads(before);manifest['private_contract_source_sha256']={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'contracts/runs').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    manifest['final_private_qualification']='final-affected-check-results.json; public COPY inputs/images unchanged by final private validator guard'
    path.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    if any(row['exit_code'] for row in checks):raise SystemExit(1)


if __name__=='__main__':main()
