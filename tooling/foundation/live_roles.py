"""Actual copied-image UID/public-product/private-boundary qualification."""
import argparse,hashlib,json,shlex,uuid
from pathlib import Path
from capture import run

ROOT=Path(__file__).resolve().parents[2]
COMMON=['--cpus','2','--memory','2g','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--tmpfs','/tmp:rw,noexec,nosuid,size=256m']


def copied(role):
    result={};active=role!='service'
    for line in (ROOT/'tooling/foundation'/f'{role}.Dockerfile').read_text().splitlines():
        if line.startswith('FROM remission-foundation-runtime:'):active=True
        elif line.startswith('FROM service AS integration-tests'):break
        if not active or not line.startswith('COPY ') or '--from=' in line:continue
        parts=shlex.split(line)[1:];sources,destination=parts[:-1],parts[-1]
        for source in sources:
            path=ROOT/source
            if path.is_dir():
                for child in path.rglob('*'):
                    if child.is_file() and '__pycache__' not in child.parts:
                        result[destination.rstrip('/')+'/'+child.relative_to(path).as_posix()]=hashlib.sha256(child.read_bytes()).hexdigest()
            else:
                target=destination+path.name if destination.endswith('/') else destination
                result[target]=hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--build',type=Path,required=True);parser.add_argument('--evidence',type=Path,required=True);args=parser.parse_args()
    build=json.loads(args.build.read_bytes());images=build['images'];runtime=build['runtime'];prefix='remission-lh-role-'+uuid.uuid4().hex[:12]
    args.evidence.mkdir(parents=True,exist_ok=True);containers=[];volumes=[];networks=[];commands=[]
    def command(argv,check=True):
        result,metadata=run(argv,args.evidence/'c');commands.append(metadata)
        (args.evidence/'commands.json').write_text(json.dumps(commands,indent=2)+'\n',encoding='utf-8')
        if check and result.returncode:raise RuntimeError('captured role failure: '+metadata['streams']['stderr']['path'])
        return result.stdout.decode().strip()
    mount=lambda name,target,ro=True:['--mount',f'type=volume,source={name},target={target}'+(',readonly' if ro else '')]
    inventory={}
    try:
        for role in ['service','learner','evaluator']:
            expected=copied(role)
            code="import hashlib,json,os;from pathlib import Path;expected="+repr(expected)+";actual={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in expected};assert actual==expected;print(json.dumps(dict(uid=os.getuid(),source=actual,assets={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/app/web/dist').rglob('*') if p.is_file()}),sort_keys=True))"
            actual=json.loads(command(['docker','run','--rm','--network','none',*COMMON,images[role],'python','-c',code]))
            inventory[role]=dict(image=images[role],copied_source=actual)
        truth,public,live=[prefix+'-'+name for name in ['truth','public','live']]
        for name in [truth,public,live]:command(['docker','volume','create',name]);volumes.append(name)
        seed="import os,json;from pathlib import Path,PurePosixPath;p=Path('/truth');(p/'canary.json').write_text('{\"kind\":\"private_foundation_canary\"}');os.chmod(p/'canary.json',0o600);os.chown(p/'canary.json',20000,20000);os.chmod(p,0o700);os.chown(p,20000,20000);os.chown('/public-live',10001,10001);r=Path('/source/docs/implementation/evidence/G1-OBS-REP/integrated');m=json.loads((r/'ready-manifest.json').read_bytes());prefix='curated-attempts/000/public-v2/';count=0\nfor path,item in m['files'].items():\n if path.startswith(prefix):\n  rel=PurePosixPath(path.removeprefix(prefix));assert not rel.is_absolute() and '..' not in rel.parts;t=Path('/public-v2').joinpath(*rel.parts);t.parent.mkdir(parents=True,exist_ok=True);t.write_bytes((r/'b'/item['git_blob']).read_bytes());count+=1\nprint(json.dumps(dict(public_wire_files=count,truth_owner=20000,live_owner=10001)))"
        command(['docker','run','--rm','--network','none',*COMMON,'--cap-add','CHOWN','--user','0:0','--mount',f'type=bind,source={ROOT.as_posix()},target=/source,readonly',*mount(truth,'/truth',False),*mount(public,'/public-v2',False),*mount(live,'/public-live',False),runtime,'python','-c',seed])
        producer="import json,sys,shutil;from pathlib import Path;from dataclasses import replace;sys.path.insert(0,'/app/tests/integration/replay');from test_live_safety_product import LiveSafetyProductTests;case=LiveSafetyProductTests();case.setUp();case.settings=replace(case.settings,source_commit="+repr(build['source_head'])+");case.enter();response,root,authority=case.export();assert response.status_code==200,response.text;target=Path('/public-live/product');shutil.copytree(root,target);Path('/public-live/authority.json').write_text(authority.model_dump_json());[(p.chmod(0o755) if p.is_dir() else p.chmod(0o444)) for p in Path('/public-live').rglob('*')];print(json.dumps(dict(status='actual_foundation_fixture_product',source_commit=authority.source_commit,manifest_sha256=authority.manifest_sha256)));case.tearDown()"
        command(['docker','run','--rm','--network','none',*COMMON,*mount(live,'/public-live',False),images['tests'],'python','-c',producer])
        network=prefix+'-private';command(['docker','network','create','--internal',network]);networks.append(network)
        evaluator=prefix+'-evaluator';command(['docker','run','--detach','--name',evaluator,'--network',network,*COMMON,*mount(truth,'/truth'),images['evaluator']]);containers.append(evaluator)
        state=json.loads(command(['docker','inspect',evaluator]))[0];assert state['Config']['User']=='20000:20000'
        address=state['NetworkSettings']['Networks'][network]['IPAddress']
        command(['docker','exec',evaluator,'python','/app/evaluator_canary.py','read'])
        command(['docker','exec',evaluator,'python','-c',"import urllib.request;assert urllib.request.urlopen('http://127.0.0.1:8766').status==200;print('positive evaluator HTTP control')"])
        for role,uid in [('service','10001:10001'),('learner','10002:10002')]:
            name=prefix+'-'+role;command(['docker','create','--name',name,'--network','none',*COMMON,'--env','OBS2_EVALUATOR_IP='+address,*mount(truth,'/truth'),*mount(public,'/public-v2'),images[role],'python','/app/observed_v2_probe.py']);containers.append(name)
            state=json.loads(command(['docker','inspect',name]))[0]
            assert state['Config']['User']==uid and state['Image']==images[role] and state['HostConfig']['NetworkMode']=='none' and state['HostConfig']['ReadonlyRootfs']
            assert all(m['Type']=='volume' and not m['RW'] for m in state['Mounts'])
            command(['docker','start','--attach',name]);assert command(['docker','inspect','--format','{{.State.ExitCode}}',name])=='0'
            live_probe="import json,os;from pathlib import Path;from contracts.service.live_safety import TrustedLiveSafetyAuthority;from contracts.service.live_safety_admission import verify_live_safety;r=Path('/public-live/product');a=TrustedLiveSafetyAuthority.model_validate_json(Path('/public-live/authority.json').read_bytes());context=verify_live_safety((r/'manifest.json').read_bytes(),r,a);assert context.independent_hold_status=='held';assert len(context.visible_operations)==2;print(json.dumps(dict(uid=os.getuid(),live_status=context.independent_hold_status,source_commit=a.source_commit,manifest_sha256=a.manifest_sha256)))"
            if role=='learner':live_probe+=";from services.learner.worker import dispatch_product;assert dispatch_product(required_product=('LIVE-SAFETY-EXPORT','1.0.0'),worker_capabilities=[('LIVE-SAFETY-EXPORT','1.0.0')],root=r,authority=a).independent_hold_status=='held'"
            command(['docker','run','--rm','--network','none',*COMMON,*mount(live,'/public-live'),images[role],'python','-c',live_probe])
            inventory[role]['runtime_boundary']=dict(uid=uid,network='none',source_mount=False,mounts=state['Mounts'],full85_public=True,live_product=True)
        (args.evidence/'inventory.json').write_text(json.dumps(dict(source_head=build['source_head'],build_manifest=str(args.build),roles=inventory,scope='contract fixtures only; no scientific producer/likelihood or human qualification'),indent=2)+'\n',encoding='utf-8')
        print(json.dumps(dict(status='passed',source_head=build['source_head'],roles=['serviceUID10001','learnerUID10002','evaluatorUID20000'],evidence=str(args.evidence))))
    finally:
        for name in reversed(containers):command(['docker','rm','--force',name],False)
        for name in reversed(networks):command(['docker','network','rm',name],False)
        for name in reversed(volumes):command(['docker','volume','rm',name],False)


if __name__=='__main__':main()
