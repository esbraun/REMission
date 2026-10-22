"""Copied-image source/role probe against this task's actual private generator."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
import uuid
from live_roles import copied

COMMON = ['--cpus', '2', '--memory', '2g', '--read-only', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--tmpfs', '/tmp:rw,noexec,nosuid,size=128m']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--deployment', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    build = json.loads(args.build.read_bytes()); deployment = json.loads(args.deployment.read_bytes())
    args.evidence.mkdir(parents=True, exist_ok=True)
    commands = []
    def command(argv):
        start = time.monotonic()
        result = subprocess.run(argv, capture_output=True)
        commands.append(dict(command=argv, exit=result.returncode, seconds=time.monotonic()-start,
                             stdout=result.stdout.decode(errors='replace'), stderr=result.stderr.decode(errors='replace')))
        (args.evidence/'commands.json').write_text(json.dumps(commands, indent=2)+'\n', encoding='utf-8')
        if result.returncode: raise RuntimeError('boundary probe failed; inspect commands.json')
        return result.stdout.decode()
    for role, uid in [('service',10001), ('learner',10002), ('generator',20000)]:
        expected = copied(role)
        code = "import os,json,hashlib;from pathlib import Path;expected="+repr(expected)+";assert os.getuid()=="+str(uid)+";assert {p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in expected}==expected;print(json.dumps(dict(uid=os.getuid(),copied_files=len(expected))))"
        command(['docker','run','--rm','--network','none',*COMMON,build['images'][role],'python','-c',code])
    generator = json.loads(command(['docker','inspect',deployment['generator_container']]))[0]
    assert generator['Image'] == build['images']['generator']
    assert not generator['Mounts'] and not generator['HostConfig']['PortBindings']
    address = generator['NetworkSettings']['Networks'][deployment['network']]['IPAddress']
    # The actual service is the only running application consumer of generator RPC.
    code = """import json,sqlite3,urllib.request
from pathlib import Path
from services.foundation.workflow import history,patient_clock
from services.foundation.store import instant,canonical
assert not Path('/app/services/generator').exists()
db=sqlite3.connect('file:/data/remission.sqlite?mode=ro',uri=True);db.row_factory=sqlite3.Row
patients=[r for r in db.execute('SELECT * FROM patients') if 'simulation' in json.loads(r['state_json'])]
assert patients,'generate a panel through the app before probing'
p=max(patients,key=lambda r:json.loads(r['state_json'])['simulation']['day'])
projection=history(db,p['id']).project(patient_clock(p,instant(p['cutoff']))).model_dump(mode='json')
assert all(r.get('seed') is None for r in projection['records']) and 'simulation' not in projection
Path('/exports/poc-boundary-observed.json').write_text(canonical(projection))
payload=dict(seed=1,index=0,patient_id='boundary-positive',through_day=0,actions=[])
request=urllib.request.Request('http://generator:8780/generate',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
with urllib.request.urlopen(request,timeout=3) as response: product=json.load(response)
assert set(product)=={'name','records'} and len(product['records'])==2
print(json.dumps(dict(service_generator_rpc=True,observed_records=len(projection['records']),day=json.loads(p['state_json'])['simulation']['day'])))
"""
    command(['docker','exec',deployment['service_container'],'python','-c',code])
    probe = """import importlib.util,json,os,urllib.request
from pathlib import Path
from contracts.domain.boundaries import LearnerHistory
assert os.getuid()==10002 and importlib.util.find_spec('services.generator') is None
assert not Path('/app/services/generator').exists() and not Path('/data/remission.sqlite').exists()
projection=LearnerHistory.model_validate_json(Path('/observed/poc-boundary-observed.json').read_bytes())
assert all(getattr(r,'seed',None) is None for r in projection.records)
try:
 urllib.request.urlopen(os.environ['GENERATOR_URL'],timeout=1)
except OSError:
 print(json.dumps(dict(uid=os.getuid(),generator_rpc_denied=True,generator_source=False,service_database=False,typed_observed_records=len(projection.records))))
else:
 raise AssertionError('learner reached private generator')
"""
    command(['docker','run','--rm','--name','remission-poc13-boundary-'+uuid.uuid4().hex[:8], '--network','none',*COMMON,
             '--env','GENERATOR_URL=http://'+address+':8780/generate',
             '--mount','type=volume,source='+deployment['volumes']['exports']+',target=/observed,readonly',
             build['images']['learner'],'python','-c',probe])
    (args.evidence/'result.json').write_text(json.dumps(dict(status='passed', source_head=build['source_head'],
        images=build['images'],url=deployment['url'],runtime=build['runtime'],generator_no_mount_or_host_port=True,
        service_rpc=True,learner_network='none',learner_public_projection_only=True),indent=2)+'\n',encoding='utf-8')
    print('Copied source, actual service RPC, learner source/mount/network denial and observed-only consumption passed.')


if __name__ == '__main__': main()
