"""Affected rerun after final private receipt typing; retain full preceding run."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
BASE='69e6ae9dc5bf85ddbf39976d2ce4ce70bce1ea1e'


def main():
    prior=json.loads((OUT/'current-interface-check-results.json').read_text())
    # Private probability types are deliberately absent from consumer images;
    # no public module, Docker COPY input, backend or numerical lock changed.
    commands=[prior['checks'][i]['command'] for i in (10,11,13,14)]
    records=[]
    for command in commands:
        start=datetime.now(timezone.utc).isoformat();result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
        records.append(dict(command=command,started_utc=start,finished_utc=datetime.now(timezone.utc).isoformat(),exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr))
        print('PASS' if result.returncode==0 else 'FAIL',' '.join(command[-4:]),flush=True)
    (OUT/'final-affected-check-results.json').write_text(json.dumps(dict(base=BASE,reason='Bind diagnostic truth receipt types/hashes/full keys/final particle level and pilot producer run; add controlled binding faults',prior_full_run='current-interface-check-results.json',checks=records,limits=prior['limits']),indent=2)+'\n',encoding='utf-8')
    path=OUT/'current-source-and-images.json';manifest=json.loads(path.read_text())
    manifest['source_sha256']={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for prefix in ['contracts/runs','services/foundation','services/learner'] for p in (ROOT/prefix).rglob('*') if p.is_file() and '__pycache__' not in p.parts}|{name:digest for name,digest in manifest['source_sha256'].items() if name.startswith('tooling/')}
    manifest['private_receipt_revision']='Covered by final-affected-check-results; private modules/schemas excluded from curated consumers, whose copied bytes/images are unchanged'
    path.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    if any(record['exit_code'] for record in records):raise SystemExit(1)


if __name__=='__main__':main()
