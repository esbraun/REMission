"""H*-only copied learner boundary with positive-control denial probes."""
import argparse
import json
from pathlib import Path
import subprocess
import time
import uuid
from live_roles import copied

ROOT=Path(__file__).resolve().parents[2]
COMMON=['--cpus','2','--memory','2g','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--tmpfs','/tmp:rw,nosuid,size=128m']


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--deployment',type=Path,required=True);parser.add_argument('--evidence',type=Path,required=True);args=parser.parse_args()
    state=json.loads(args.deployment.read_bytes());args.evidence.mkdir(parents=True,exist_ok=True)
    records=[]
    def run(argv,expected=0):
        start=time.monotonic();p=subprocess.run(argv,capture_output=True)
        records.append(dict(command=argv,exit=p.returncode,seconds=time.monotonic()-start,stdout=p.stdout.decode(errors='replace'),stderr=p.stderr.decode(errors='replace')))
        (args.evidence/'commands.json').write_text(json.dumps(records,indent=2)+'\n')
        if p.returncode!=expected:raise RuntimeError('boundary probe failed; see captured commands')
        return p.stdout
    image=state['learner_image'];prefix=state['prefix']+'-hstar-'+uuid.uuid4().hex[:8]
    # The service emits ONLY the already frozen approved input for a current
    # configuration attempt. No DB/private replay envelope enters this volume.
    code="import sqlite3;db=sqlite3.connect('file:/data/remission.sqlite?mode=ro',uri=True);r=db.execute('SELECT request_json FROM analysis_attempts ORDER BY created_at DESC,rowid DESC LIMIT 1').fetchone();assert r;print(r[0])"
    raw=run(['docker','exec',state['service_container'],'python','-c',code])
    (args.evidence/'input.json').write_bytes(raw)
    volume=prefix+'-input';helper=prefix+'-stage'
    run(['docker','volume','create',volume])
    run(['docker','create','--name',helper,'--network','none',*COMMON,'--cap-add','CHOWN','--user','0:0',
         '--mount',f'type=volume,source={volume},target=/input',image,'python','-c',
         "import os;os.chown('/input/input.json',10002,10002);os.chmod('/input/input.json',0o444);os.chmod('/input',0o755)"])
    run(['docker','cp',str((args.evidence/'input.json').resolve()),helper+':/input/input.json'])
    run(['docker','start','--attach',helper]);run(['docker','rm',helper])
    generator=json.loads(run(['docker','inspect',state['generator_container']]))[0]
    address=generator['NetworkSettings']['Networks'][state['network']]['IPAddress']
    expected=copied('learner')
    probe="""import hashlib,importlib.util,json,os,urllib.request,urllib.error
from pathlib import Path
from contracts.domain.analysis import AnalysisInput
assert os.getuid()==10002
assert not Path('/app/services/generator').exists(),'private source exposed'
assert importlib.util.find_spec('services.generator') is None and importlib.util.find_spec('services.foundation') is None
assert not Path('/data/remission.sqlite').exists() and not Path('/var/run/docker.sock').exists()
mounts=[line.split() for line in Path('/proc/self/mountinfo').read_text().splitlines()]
assert any(p[4]=='/input' and 'ro' in p[5].split(',') for p in mounts),'public input is not read-only'
value=AnalysisInput.model_validate_json(Path('/input/input.json').read_bytes())
history=json.dumps(value.history.model_dump(mode='json'))
assert all(('"'+key+'"') not in history for key in ['function','diary_sleep_minutes','source','raw_sha256','state_json','simulation','seed','index','truth','replay'])
expected=json.loads(os.environ['EXPECTED_FILES'])
assert {p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in expected}==expected
request=urllib.request.Request(os.environ['GENERATOR_URL'],data=json.dumps(dict(seed=1,index=0,patient_id='analysis-boundary',through_day=0,actions=[])).encode(),headers={'Content-Type':'application/json'})
try:
 with urllib.request.urlopen(request,timeout=1) as response:reached=True
except urllib.error.HTTPError:reached=True
except (urllib.error.URLError,TimeoutError,ConnectionError):reached=False
assert not reached,'private generator reached'
print(json.dumps(dict(status='passed',uid=os.getuid(),input_hash=value.history_sha256,configuration=value.request.configuration.model_dump(),reduced_history_only=True,source_files=len(expected))))
"""
    def probe_run(network='none',readonly=True,source=False,exit=0):
        mount=f'type=volume,source={volume},target=/input'+(',readonly' if readonly else '')
        return run(['docker','run','--rm','--network',network,*COMMON,'--user','10002:10002',
            '--mount',mount,*(['--mount',f'type=bind,source={ROOT / "services/generator"},target=/app/services/generator,readonly'] if source else []),
            '-e','GENERATOR_URL=http://'+address+':8780/generate','-e','EXPECTED_FILES='+json.dumps(expected),image,'python','-c',probe],exit)
    probe_run(source=True,exit=1);assert 'private source exposed' in records[-1]['stderr']
    probe_run(readonly=False,exit=1);assert 'public input is not read-only' in records[-1]['stderr']
    probe_run(network=state['network'],exit=1);assert 'private generator reached' in records[-1]['stderr']
    summary=json.loads(probe_run())
    summary.update(source_commit=state['source_commit'],learner_image=image,positive_controls=['source','mount-readonly','network'])
    (args.evidence/'result.json').write_text(json.dumps(summary,indent=2)+'\n')
    run(['docker','volume','rm',volume]);print(json.dumps(summary))


if __name__=='__main__':main()
