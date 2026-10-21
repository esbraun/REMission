"""Task-private actual ec18 drain/new-volume cutover and browser deployment."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import uuid
from capture import run

ROOT=Path(__file__).resolve().parents[2]
RUNTIME='sha256:ce346feace2ae607ebd574e1bb681d594c9b676c06b56f8ba8d50b858a577faa'
OLD='sha256:82f5b9c4ea1f13a0bee5fe1a852a220fba16752d5aa21df8fa3726b8c483d6a8'
COMMON=['--cpus','2','--memory','2g','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--tmpfs','/tmp:rw,noexec,nosuid,size=128m']


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8769)
    parser.add_argument('--service-image',required=True);parser.add_argument('--learner-image',required=True)
    parser.add_argument('--evidence',type=Path,required=True);args=parser.parse_args()
    args.evidence.mkdir(parents=True,exist_ok=True);captures=[]
    prefix='remission-g1-live-hold-20261021-'+uuid.uuid4().hex[:8]
    def command(argv,check=True):
        result,metadata=run(argv,args.evidence/'c');captures.append(metadata)
        (args.evidence/'deployment-commands.json').write_text(json.dumps(captures,indent=2)+'\n',encoding='utf-8')
        if check and result.returncode:raise RuntimeError('command failed: '+metadata['streams']['stderr']['path'])
        return result
    head=command(['git','rev-parse','HEAD']).stdout.decode().strip()
    for image in [RUNTIME,OLD,args.service_image,args.learner_image]:command(['docker','image','inspect',image])
    network=prefix+'-app';label='remission.task='+prefix
    command(['docker','network','create','--label',label,network])
    volumes={k:prefix+'-'+k for k in ['historical','database','fixtures','exports']}
    mount=lambda role,path,ro=False:['--mount',f'type=volume,source={volumes[role]},target={path}'+(',readonly' if ro else '')]
    for role,name in volumes.items():
        command(['docker','volume','create','--label',label,name])
        command(['docker','run','--rm','--network','none',*COMMON,'--cap-add','CHOWN','--user','0:0',*mount(role,'/owned'),RUNTIME,
            'python','-c',"import os;os.chmod('/owned',0o700);os.chown('/owned',10001,10001)"])
    command(['docker','run','--rm','--network','none',*COMMON,*mount('historical','/data'),OLD,
        'python','-m','services.foundation.cli','seed','--database','/data/remission.sqlite'])
    old_name=prefix+'-old';service_name=prefix+'-service'
    url='http://127.0.0.1:'+str(args.port)
    command(['docker','run','--detach','--name',old_name,'--label',label,'--network',network,
        '--publish',f'127.0.0.1:{args.port}:8765',*COMMON,*mount('historical','/data'),'--env','REMISSION_ORIGIN='+url,OLD,
        'python','-m','uvicorn','services.foundation.server:app','--host','0.0.0.0','--port','8765','--no-access-log'])
    def health(expected):
        deadline=time.monotonic()+20
        while True:
            try:
                with urllib.request.urlopen(url+'/health',timeout=1) as response:value=json.load(response)
                if expected is None or value.get('capability')==expected:return value
            except (OSError,ValueError):pass
            if time.monotonic()>deadline:raise RuntimeError('health did not reach expected current capability')
            time.sleep(.1)
    old_health=health(None)
    command(['docker','inspect',old_name])
    command(['docker','update','--restart=no',old_name])
    command(['docker','stop','--time','10',old_name])
    old_inventory=json.loads(command(['docker','inspect',old_name]).stdout)[0]
    if old_inventory['State']['Running'] or old_inventory['HostConfig']['RestartPolicy']['Name']!='no':
        raise RuntimeError('old supervisor did not quiesce')
    if command(['docker','ps','--quiet','--filter','volume='+volumes['historical']]).stdout.strip():
        raise RuntimeError('old database volume still has an active process')
    # The only source mount belongs to this offline provisioning/audit process.
    command(['docker','run','--rm','--network','none',*COMMON,'--user','10001:10001','-e','PYTHONDONTWRITEBYTECODE=1','-e','PYTHONPATH=/source',
        '--mount',f'type=bind,source={ROOT},target=/source,readonly','-w','/source',*mount('historical','/historical'),
        *mount('database','/data'),*mount('fixtures','/fixtures'),RUNTIME,'python','tooling/foundation/prepare_live_demo.py',
        '--fixture-root','/fixtures','--database','/data/remission.sqlite','--historical-source','/historical/remission.sqlite','--source-commit',head])
    # Exact copied source audit without a source mount in the runtime image.
    files=[*ROOT.joinpath('services/foundation').glob('*.py'),*ROOT.joinpath('services/foundation/migrations').glob('*.sql'),
        *[ROOT/'contracts/service'/f for f in ['__init__.py','live_hold.py','live_safety.py','live_safety_admission.py','bindings-v1.json']]]
    expected={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    probe="import hashlib,json,os,pathlib; expected=json.loads(os.environ['EXPECTED_HASHES']); actual={p:hashlib.sha256(pathlib.Path('/app',p).read_bytes()).hexdigest() for p in expected}; assert actual==expected,(actual,expected); print(json.dumps({'uid':os.getuid(),'source_sha256':actual},sort_keys=True))"
    command(['docker','run','--rm','--network','none',*COMMON,'--env','EXPECTED_HASHES='+json.dumps(expected),args.service_image,'python','-c',probe])
    command(['docker','run','--detach','--name',service_name,'--label',label,'--network',network,
        '--publish',f'127.0.0.1:{args.port}:8765',*COMMON,*mount('database','/data'),*mount('fixtures','/fixtures',True),*mount('exports','/exports'),
        '--env','REMISSION_ORIGIN='+url,'--env','REMISSION_CONTROL_BUNDLE=/fixtures/bundle.json','--env','REMISSION_ARCHIVE_CONFIG=/fixtures/archives.json',
        '--env','REMISSION_LIVE_EXPORT_ROOT=/exports','--env','REMISSION_RUNTIME_REF=/fixtures/runtime.json','--env','REMISSION_SOURCE_COMMIT='+head,args.service_image])
    current_health=health('LIVE-HOLD-01/1.0.0')
    # A stale launch retains its old volume/port configuration; the new current route owns that port.
    stale=command(['docker','start',old_name],check=False)
    if stale.returncode==0:raise RuntimeError('stale current-route launch unexpectedly succeeded')
    old_after=json.loads(command(['docker','inspect',old_name]).stdout)[0]
    if old_after['State']['Running']:raise RuntimeError('old worker remains running')
    denial="from pathlib import Path; import os,json; assert not Path('/data/remission.sqlite.admission.lock').exists(); assert not Path('/current/remission.sqlite').exists(); print(json.dumps({'uid':os.getuid(),'new_authority_volume_access':False,'current_route':False}))"
    command(['docker','run','--rm','--network','none',*COMMON,*mount('historical','/data',True),OLD,'python','-c',denial])
    inventory=json.loads(command(['docker','inspect',service_name]).stdout)[0]
    if any(m['Name']==volumes['historical'] for m in inventory['Mounts'] if m.get('Type')=='volume'):
        raise RuntimeError('new current service still mounts old database')
    state=dict(prefix=prefix,source_commit=head,service_image=args.service_image,learner_image=args.learner_image,
        runtime_image=RUNTIME,old_image=OLD,url=url,port=args.port,network=network,volumes=volumes,
        old_container=old_name,service_container=service_name,old_health=old_health,current_health=current_health,
        old_stopped=True,old_restart_disabled=True,new_private_volume=True,source_hashes=expected,
        fixture_claim='contract_fixture only; upstream scientific producer not qualified',browser_cases='not yet executed')
    (args.evidence/'deployment.json').write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(state,indent=2))


if __name__=='__main__':main()
