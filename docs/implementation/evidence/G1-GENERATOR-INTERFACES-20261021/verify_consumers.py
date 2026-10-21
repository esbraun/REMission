"""Observed curated consumer-image admission/denial; no host source mounts."""
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
IMAGE_PREFIX=os.environ.get('REMISSION_INTERFACE_IMAGE_PREFIX','remission-interfaces')


def main():
    task=ROOT/('artifacts/interfaces-consumer-probe-'+uuid.uuid4().hex)
    task.mkdir(parents=True,exist_ok=False)
    generation="""import sys
from pathlib import Path
sys.path.insert(0,'/workspace/tests/run_contracts')
from fixtures import setup
from contracts.runs.admission import admit_export
from contracts.runs.common import canonical
task=Path('/probe');staging=task/'staging';staging.mkdir();destination=task/'observed';destination.mkdir()
fixture=setup(staging);admit_export(fixture['export_raw'],staging,destination,fixture['export_authority'])
(task/'authority.json').write_bytes(canonical(fixture['export_authority'].model_dump(mode='json')))
print('Prepared hand-authored public-only contract fixture; no generator executed')
"""
    command=['docker','run','--rm','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges:true','--tmpfs','/tmp:rw,noexec,nosuid,size=64m','--mount',f'type=bind,source={ROOT.as_posix()},target=/workspace,readonly','--mount',f'type=bind,source={task.as_posix()},target=/probe','--workdir','/workspace','--env','PYTHONPATH=/workspace','sha256:ce346feace2ae607ebd574e1bb681d594c9b676c06b56f8ba8d50b858a577faa','python','-c',generation]
    prepared=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
    (OUT/'current-consumer-fixture-preparation.json').write_text(json.dumps(dict(command=command,exit_code=prepared.returncode,stdout=prepared.stdout,stderr=prepared.stderr),indent=2)+'\n',encoding='utf-8')
    if prepared.returncode:raise SystemExit(prepared.returncode)
    destination=task/'observed';admitted=destination/'contract-run/export-one';authority=task/'authority.json'
    probe="""import importlib,json,os,errno
from pathlib import Path
from contracts.runs.common import ExportAuthority
from contracts.runs.admission import read_admitted
authority=ExportAuthority.model_validate_json(Path('/config/authority.json').read_bytes())
root=Path('/observed/contract-run/export-one')
manifest,partitions=read_admitted(root,authority)
assert len(partitions)==2 and all(not row[3].records for row in partitions)
denied=[]
for module in ['contracts.runs.private','contracts.runs.private_admission','contracts.runs.probability','contracts.runs.export','contracts.dgp','contracts.domain.evaluation','simulation','evaluation.truth']:
 try: importlib.import_module(module)
 except ModuleNotFoundError: denied.append(module)
 else: raise AssertionError('private source import succeeded: '+module)
try: (root/'forged.json').write_text('{}')
except OSError as error: assert error.errno in (errno.EROFS,errno.EACCES)
else: raise AssertionError('observed volume writable')
if os.environ['CONSUMER_ROLE']=='service':
 from services.foundation.store import Store
 from services.foundation.cli import seed
 from services.foundation.replay import replay_export
 store=Store('/tmp/contracts.sqlite');seed(store)
 result=replay_export(store,(root/'manifest.json').read_bytes(),root,authority,batch_size=1)
 assert result['records']==2
 with store.transaction() as db: assert db.execute('SELECT count(*) FROM events').fetchone()[0]==2
else:
 from services.learner.worker import read_run_export
 _,histories=read_run_export(root,authority);assert len(histories)==2
print(json.dumps(dict(role=os.environ['CONSUMER_ROLE'],uid=os.getuid(),observed_partitions=2,equal_time_learner_records=0,denied_private_modules=denied,observed_write='denied',source_checkout_mount=False,fixture_only=True)))
"""
    records=[]
    for role in ['service','learner']:
        image=f'{IMAGE_PREFIX}-{role}:candidate'
        command=['docker','run','--rm','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges:true','--tmpfs','/tmp:rw,noexec,nosuid,size=64m','--env',f'CONSUMER_ROLE={role}','--mount',f'type=bind,source={destination.as_posix()},target=/observed,readonly','--mount',f'type=bind,source={authority.as_posix()},target=/config/authority.json,readonly',image,'python','-c',probe]
        start=datetime.now(timezone.utc).isoformat();result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
        records.append(dict(command=command,started_utc=start,finished_utc=datetime.now(timezone.utc).isoformat(),exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr))
    images={role:subprocess.check_output(['docker','image','inspect',f'{IMAGE_PREFIX}-{role}:candidate','--format','{{.Id}}'],cwd=ROOT,text=True).strip() for role in ['service','learner','tests']}
    (OUT/'current-curated-consumer-results.json').write_text(json.dumps(dict(checks=records,images=images,admitted_fixture=admitted.as_posix(),claim='Hand-authored contract fixture admission only; no generator/truth execution; no existing service/volume/port changed'),indent=2)+'\n',encoding='utf-8')
    if any(row['exit_code'] for row in records):raise SystemExit(1)
    print('PASS: real service/learner identities admit observed artifacts, deny private source imports and observed writes; actual service SQLite replay')


if __name__=='__main__':main()
