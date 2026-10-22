"""Prepare the existing 8780 service overlay; never deploy or open its database."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

from capture import run

BASE='sha256:35910f5f5d1aa579367a60bf0a6264843b6fca68a8699369c6b7e4a1b863e93e'
SOURCE='4a340baf63fdb0f9a6f4fb065166232dafd10ca3'
LEARNER='sha256:9d2e601f926ae644a041903b076fdb33ff3885be1a0f390137bc61ff461584e1'
GENERATOR='sha256:5d546abd1448e46d5d45ac4a3d98c31899631f968f93d21b163797ff0674ded9'
CHANGES={
    'services/foundation/analysis.py':'/app/services/foundation/analysis.py',
    'services/foundation/analysis_cli.py':'/app/services/foundation/analysis_cli.py',
    'contracts/domain/borrow_runtime.py':'/app/contracts/domain/borrow_runtime.py',
}
LIMITS=['--network','none','--cpus','2','--memory','2g','--read-only','--cap-drop','ALL',
        '--security-opt','no-new-privileges','--tmpfs','/tmp:rw,exec,nosuid,nodev,size=512m','--user','10001:10001']
SCAN="""import hashlib,json;from pathlib import Path
r={}
for p in sorted(Path('/app').rglob('*')):
 if p.is_file():
  b=p.read_bytes();r[str(p)]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
print(json.dumps(r,sort_keys=True))
"""
TESTS=[
    'test_borrowing.JointTargetTests.test_real_frozen_pre_v1_input_result_canonical_identity',
    'test_borrowing.BorrowingRoutesTests.test_genuine_pre_v1_stored_receipt_replays_with_optional_defaults',
    'test_borrowing.BorrowingRoutesTests.test_source_admission_receipt_intents_and_guarded_result_sources',
    'test_borrowing.BorrowingRoutesTests.test_host_binding_survives_progress_and_vetoes_forged_completed_execution',
]


def digest(raw):return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--evidence',type=Path,required=True)
    args=parser.parse_args();root=args.evidence
    root.mkdir(parents=True,exist_ok=False)
    def save(name,value):
        (root/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    def command(argv,seconds=60):
        p,m=run(argv,root/'commands',timeout_seconds=seconds)
        if p.returncode:raise RuntimeError(str(m))
        return p.stdout
    head=command(['git','rev-parse','HEAD']).decode().strip()
    # Compare the actual physical copied bytes with the accepted production source,
    # explicitly distinguishing Git LF bytes from Windows checkout bytes.
    source={}
    for name in [*CHANGES,'tooling/foundation/analysis_dispatcher.py']:
        raw=Path(name).read_bytes();git=command(['git','show',SOURCE+':'+name])
        if raw.replace(b'\r\n',b'\n')!=git.replace(b'\r\n',b'\n'):
            raise ValueError('accepted production source differs: '+name)
        source[name]=dict(physical=digest(raw),git=digest(git),source_commit=SOURCE,
            physical_equals_git=raw==git,difference=None if raw==git else 'CRLF/LF only')
    save('source-bindings.json',source)
    (root/'analysis_dispatcher.py').write_bytes(Path('tooling/foundation/analysis_dispatcher.py').read_bytes())
    tag='remission-pa3-sol261022-service-base-5843:candidate'
    command(['docker','tag',BASE,tag])
    assert command(['docker','image','inspect',tag,'--format','{{.Id}}']).decode().strip()==BASE
    service='remission-pa3-sol261022-service-4a:candidate'
    command(['docker','build','--network','none','--build-arg','SERVICE_BASE='+tag,'-f',
        'tooling/foundation/pa3-service-overlay.Dockerfile','-t',service,'.'],180)
    image=command(['docker','image','inspect',service,'--format','{{.Id}}']).decode().strip()
    images={}
    for role,identity in [('base',BASE),('service',image),('learner',LEARNER),('generator',GENERATOR)]:
        item=json.loads(command(['docker','image','inspect',identity]))[0]
        images[role]={key:item[key] for key in ['Id','Created','RootFS']}
        images[role]['config']={key:item['Config'].get(key) for key in ['User','WorkingDir','Entrypoint','Cmd','ExposedPorts']}
    assert images['base']['RootFS']['Layers']==images['service']['RootFS']['Layers'][:len(images['base']['RootFS']['Layers'])]
    assert images['base']['config']==images['service']['config']
    save('images.json',images)
    controls='remission-pa3-sol261022-service-4a:controls'
    command(['docker','build','--network','none','--build-arg','SERVICE_BASE='+service,'-f',
        'tooling/foundation/pa3-service-controls.Dockerfile','-t',controls,'.'],180)
    test_image=command(['docker','image','inspect',controls,'--format','{{.Id}}']).decode().strip()
    save('controls-image.json',json.loads(command(['docker','image','inspect',test_image]))[0])
    prefix='remission-pa3-sol261022-service-4a'
    states={}
    def container(suffix,identity,argv,seconds=60):
        name=prefix+'-'+suffix;start=time.monotonic()
        p,m=run(['docker','run','--name',name,*LIMITS,identity,*argv],root/'commands',timeout_seconds=seconds)
        state=json.loads(command(['docker','inspect',name]))[0]
        if state['State']['Running']:
            command(['docker','kill',name]);state=json.loads(command(['docker','inspect',name]))[0]
        if state['State']['Running']:raise RuntimeError('own container still running '+name)
        elapsed=time.monotonic()-start
        states[suffix]=dict(container=state,command=m,wall_seconds=elapsed)
        save('container-states.json',states)
        if p.returncode or state['State']['ExitCode'] or state['State']['OOMKilled'] or m['timed_out'] or elapsed>seconds:
            raise RuntimeError('failed/late service preparation control '+suffix)
        return p.stdout
    inventories={}
    for role,identity in [('base',BASE),('service',image)]:
        inventories[role]=json.loads(container('inventory-'+role,identity,['python','-c',SCAN]))
        save('inventory-'+role+'.json',inventories[role])
    before=inventories['base'];after=inventories['service']
    changed={name:dict(before=before.get(name),after=after.get(name)) for name in sorted(before.keys()|after.keys()) if before.get(name)!=after.get(name)}
    assert set(changed)==set(CHANGES.values()),set(changed)
    for name,target in CHANGES.items():assert after[target]==source[name]['physical']
    save('changed-paths.json',changed)
    help_output=container('cli-help',image,['python','-m','services.foundation.analysis_cli','--help'])
    assert b'bind-execution' in help_output
    (root/'cli-help.stdout').write_bytes(help_output)
    purity="import sys,importlib.util;from services.foundation.analysis import bind_execution,ingest;assert 'pymc' not in sys.modules;assert importlib.util.find_spec('services.generator') is None;print('consumer-only service imports; private generator absent; no PyMC imported')"
    (root/'purity.stdout').write_bytes(container('purity',image,['python','-c',purity]))
    code="import unittest;names="+repr(TESTS)+";suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(n) for n in names);r=unittest.TextTestRunner(verbosity=2).run(suite);raise SystemExit(not r.wasSuccessful())"
    print('TEMPORARY_DATABASE_CONTROLS '+test_image,flush=True)
    container('tempdb-controls',test_image,['python','-c',code],300)
    old=json.loads(Path('artifacts/pa3/app-8780/deployment.json').read_bytes())
    deployment={key:old[key] for key in ['prefix','port','url','network','volumes','service_container','generator_container','runtime_image']}
    deployment.update(status='prepared_not_deployed',service_image=image,service_source_commit=SOURCE,
        learner_image=LEARNER,source_commit=SOURCE,generator_image=GENERATOR,
        inherited_base_image=BASE,inherited_service_build_source='5843caaa0dd58c5c7f97cbbcd9d1146f00b3b628',
        preparation_observer_commit=head,previous_manifest_physical=digest(Path('artifacts/pa3/app-8780/deployment.json').read_bytes()),
        dispatcher=dict(path='analysis_dispatcher.py',**source['tooling/foundation/analysis_dispatcher.py']['physical'],source_commit=SOURCE),
        activation_requires='separate reviewed maintenance/SQLite protection, oldest-queue audit and explicit root authorization')
    save('deployment-prepared.json',deployment)
    save('result.json',dict(status='prepared_not_deployed',observer_commit=head,production_source=SOURCE,service_image=image,
        controls_image=test_image,tests=TESTS,scope='four non-fitting temp-DB controls, CLI help, consumer purity, full /app inheritance hash audit; no app DB/deploy/claim/fit'))
    manifest={str(p.relative_to(root)).replace('\\','/'):digest(p.read_bytes()) for p in sorted(root.rglob('*')) if p.is_file()}
    save('raw-manifest.json',dict(files=manifest,files_count=len(manifest),status='frozen; no more writes'))
    print(json.dumps(json.loads((root/'result.json').read_bytes()),indent=2),flush=True)


if __name__=='__main__':main()
