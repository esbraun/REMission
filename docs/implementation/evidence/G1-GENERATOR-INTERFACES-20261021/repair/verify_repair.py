"""Full current repair checks; rejected2a author/reviewer evidence is immutable."""
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
import os
import runpy
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent.parent/'repair-levels'
PARENT=OUT.parent
BASE='69e6ae9dc5bf85ddbf39976d2ce4ce70bce1ea1e'
REJECTED='95a48144b936c690aa86e5743a5330a594403521'
RUNTIME='sha256:ce346feace2ae607ebd574e1bb681d594c9b676c06b56f8ba8d50b858a577faa'
PREFIX=os.environ.get('REMISSION_INTERFACE_IMAGE_PREFIX','remission-interfaces-levels-repair')


def run(command):
    start=datetime.now(timezone.utc).isoformat();result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
    return dict(command=command,cwd=ROOT.as_posix(),started_utc=start,finished_utc=datetime.now(timezone.utc).isoformat(),exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr)


def main():
    if Path.cwd().resolve()!=ROOT.resolve():raise ValueError('verification cwd must match executing checkout')
    helpers=runpy.run_path(str(Path(__file__).with_name('command_paths.py')))
    helpers['owned_path'](OUT,ROOT)
    assert subprocess.check_output(['docker','image','inspect','remission-foundation-runtime:candidate','--format','{{.Id}}'],cwd=ROOT,text=True).strip()==RUNTIME
    builds=[]
    for role,file,target in [('service','service.Dockerfile','service'),('learner','learner.Dockerfile',None),('tests','service.Dockerfile','integration-tests')]:
        command=['docker','build','-f','tooling/foundation/'+file]+(['--target',target] if target else [])+['-t',f'{PREFIX}-{role}:candidate','.']
        record=run(command);builds.append(record);(OUT/(role+'-build.log')).write_bytes((record['stdout']+record['stderr']).encode('utf-8'))
        print('PASS' if not record['exit_code'] else 'FAIL','build',role,flush=True)
    (OUT/'build-results.json').write_text(json.dumps(builds,indent=2)+'\n',encoding='utf-8')
    if any(r['exit_code'] for r in builds):raise SystemExit(1)
    prior=json.loads((PARENT/'current-interface-check-results.json').read_text())
    commands=helpers['rebind_commands']([r['command'] for r in prior['checks'][:16]],ROOT,sys.executable)
    for command in commands:
        for index,value in enumerate(command):
            if value=='remission-interfaces-tests:candidate':command[index]=f'{PREFIX}-tests:candidate'
    # Reuse the observed consumer harness with ONLY its output directory/tag
    # redirected in this process; its original committed2a observations stay.
    consumer_code="import importlib.util,os,pathlib; p=pathlib.Path('docs/implementation/evidence/G1-GENERATOR-INTERFACES-20261021/verify_consumers.py'); s=importlib.util.spec_from_file_location('owned_consumer_probe',p); m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.OUT=pathlib.Path("+repr(OUT.relative_to(ROOT).as_posix())+");m.IMAGE_PREFIX="+repr(PREFIX)+";m.main()"
    commands.append([sys.executable,'-c',consumer_code])
    commands += [['git','diff','--quiet',REJECTED,'--',PARENT.relative_to(ROOT).as_posix(),':!'+OUT.relative_to(ROOT).as_posix()+'/**',*[':!'+(PARENT/'repair'/name).relative_to(ROOT).as_posix() for name in ('verify_repair.py','verify_affected.py','command_paths.py')]]]
    checks=[]
    for command in commands:
        record=run(command);checks.append(record);print('PASS' if not record['exit_code'] else 'FAIL',' '.join(command[-4:]),flush=True)
    (OUT/'repair-check-results.json').write_text(json.dumps(dict(base=BASE,rejected_head=REJECTED,checks=checks,claim='Pure interface/IO repair only; actual producer/statistical qualification remains pending'),indent=2)+'\n',encoding='utf-8')
    # Preserve the original adverse script's actual nonzero exit, then a
    # separately labelled continuing adapter rather than editing the original.
    container=prior['checks'][11]['command'][:-7]
    # Explicit command avoids depending on a prior fixture command's suffix.
    container=['docker','run','--rm','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges:true','--tmpfs','/tmp:rw,noexec,nosuid,size=512m','--mount',f'type=bind,source={ROOT.as_posix()},target=/workspace,readonly','--workdir','/workspace','--env','PYTHONPATH=/workspace',RUNTIME,'python']
    observations=[]
    probe_paths=[PARENT/'repair/independent-probes-2a.py',PARENT/'repair/probe_all_mutations.py',OUT/'independent-level-probe-95a.py',OUT/'independent-probability-pilot-probe-95a.py']
    for path in probe_paths:
        name=path.name;record=run(container+[path.relative_to(ROOT).as_posix()]);observations.append(record)
        (OUT/(name+'.postrepair-stdout.log')).write_bytes(record['stdout'].encode('utf-8'))
        (OUT/(name+'.postrepair-stderr.log')).write_bytes(record['stderr'].encode('utf-8'))
        print('OBSERVED',name,'exit',record['exit_code'],flush=True)
    (OUT/'adverse-probe-replay-results.json').write_text(json.dumps(dict(original_script_is_unchanged=True,observations=observations),indent=2)+'\n',encoding='utf-8')
    images={role:subprocess.check_output(['docker','image','inspect',f'{PREFIX}-{role}:candidate','--format','{{.Id}}'],cwd=ROOT,text=True).strip() for role in ('service','learner','tests')}
    roles={}
    for role in images:
        paths=['contracts/runs/'+name for name in ('__init__.py','common.py','observed.py','admission.py','bindings-v1.json')]
        paths += [p.relative_to(ROOT).as_posix() for p in (ROOT/('services/learner' if role=='learner' else 'services/foundation')).rglob('*.py')]
        code='import hashlib,json,pathlib; paths='+repr(paths)+'; print(json.dumps({p:hashlib.sha256((pathlib.Path("/app")/p).read_bytes()).hexdigest() for p in paths}))'
        result=run(['docker','run','--rm','--network','none','--read-only',images[role],'python','-c',code]);actual=json.loads(result['stdout'])
        expected={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths};assert actual==expected
        roles[role]=dict(**result,source_sha256=expected,match=True)
    sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'contracts/runs').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    (OUT/'source-and-images.json').write_text(json.dumps(dict(base=BASE,rejected=REJECTED,runtime=RUNTIME,images=images,actual_public_image_byte_probes=roles,private_contract_source_sha256=sources,claim='Own source only; no old image tags/stacks/ports/DBs modified; private contract modules excluded from consumers'),indent=2)+'\n',encoding='utf-8')
    if any(r['exit_code'] for r in checks) or observations[0]['exit_code']!=1 or any(r['exit_code']!=0 for r in observations[1:]):raise SystemExit(1)


if __name__=='__main__':main()
