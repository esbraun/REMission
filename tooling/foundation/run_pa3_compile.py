"""Bounded PA3 diagnosis, exact copied graphs, preserved isolated outputs."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time
import uuid
from capture import run

ROOT=Path(__file__).resolve().parents[2]
RUNTIME='sha256:ce346feace2ae607ebd574e1bb681d594c9b676c06b56f8ba8d50b858a577faa'
PHASES=('coordinates','guided-logp','guided-gradient','original-logp','original-gradient','local-logp','changed-logp')
PHASE_SECONDS=600
SUITE_SECONDS=1800


def terminal_reason(state,exit_code,elapsed,limit,timed_out):
    if state['Running']:return 'termination-unconfirmed'
    if state.get('OOMKilled'):return 'oom-killed'
    if timed_out or elapsed>=limit:return 'deadline-exceeded'
    if exit_code or state['ExitCode']:return 'process-failure'
    return None


def close(a,b,atol,rtol=0):
    if not math.isfinite(a) or not math.isfinite(b) or abs(a-b)>atol+rtol*abs(b):
        raise ValueError(f'numerical qualification mismatch: {a} versus {b}')


def qualify(rows):
    """Equal-coordinate FD gradients; density identity includes both Jacobians."""
    for name in ('guided','original'):
        density=rows[name+'-logp'];gradient=rows[name+'-gradient']
        if density['value_variable_order']!=gradient['value_variable_order']:raise ValueError('gradient coordinate ordering mismatch')
        for autodiff,finite in zip(gradient['values'],density['coordinate_finite_difference'],strict=True):
            if len(autodiff)!=len(finite):raise ValueError('gradient coordinate dimension mismatch')
            for a,b in zip(autodiff,finite,strict=True):close(a,b,1e-5,1e-4)
    for index,jacobian in enumerate(rows['coordinates']['log_jacobians']):
        guided=rows['guided-logp']['values'][index];original=rows['original-logp']['values'][index]
        close(guided,original+math.log(80)+jacobian,1e-7)
        local=rows['local-logp']['values'][index]
        expected=rows['original-logp']['independent_source_and_prior_logp'][index]
        close(original-local,expected,1e-8)
        for value in rows['original-logp']['negative_control_logp'][index].values():
            if abs(original-local-value)<1e-6:raise ValueError('omitted/double/reversed negative control failed')
        if abs(rows['changed-logp']['values'][index]-original)<1e-6:raise ValueError('changed source did not change target')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--image',required=True);parser.add_argument('--evidence',type=Path,required=True)
    args=parser.parse_args();args.evidence.mkdir(parents=True,exist_ok=False)
    def command(argv,seconds=60):
        outcome,metadata=run(argv,args.evidence/'commands',timeout_seconds=seconds)
        if outcome.returncode:raise RuntimeError('captured command failed: '+metadata['streams']['stderr']['path'])
        return outcome.stdout.decode().strip()
    def write(name,value):(args.evidence/name).write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n')
    image=command(['docker','image','inspect',args.image,'--format','{{.Id}}'])
    runtime=command(['docker','image','inspect','remission-foundation-runtime:candidate','--format','{{.Id}}'])
    if runtime!=RUNTIME:raise ValueError('pinned runtime mismatch')
    prefix='remission-pa3-compile-'+uuid.uuid4().hex[:12]
    input_dir=args.evidence/'input';input_dir.mkdir()
    for source,name in [(ROOT/'tests/integration/replay/fixtures/pa3-legacy-v0-input.json','input.json'),
        (ROOT/'services/foundation/studies/source-7c97862d.json','sources.json'),
        (ROOT/'tooling/foundation/pa3-compile-points.json','points.json')]:
        (input_dir/name).write_bytes(source.read_bytes())
    frozen=json.loads((input_dir/'points.json').read_bytes())
    if hashlib.sha256((input_dir/'input.json').read_bytes()).hexdigest()!=frozen['input_sha256']:raise ValueError('input freeze mismatch')
    if hashlib.sha256((input_dir/'sources.json').read_bytes()).hexdigest()!=frozen['source_file_sha256']:raise ValueError('source freeze mismatch')
    volumes=dict(input=prefix+'-input',**{phase:prefix+'-'+phase for phase in PHASES})
    for volume in volumes.values():command(['docker','volume','create',volume])
    limits=['--network','none','--cpus','2','--memory','2g','--read-only','--cap-drop','ALL',
        '--security-opt','no-new-privileges','--tmpfs','/tmp:rw,nosuid,size=512m']
    mount=lambda volume,path,ro=False:['--mount',f'type=volume,src={volume},dst={path}'+(',readonly' if ro else '')]
    transfer=prefix+'-transfer'
    # Root is used only for this offline, public-file custody transfer.
    script="from pathlib import Path;root=Path('/input');[(p.chmod(0o444)) for p in root.iterdir()];root.chmod(0o555);[(Path('/out')/str(i)).chmod(0o777) for i in range(7)]"
    transfer_mounts=[*mount(volumes['input'],'/input')]
    for index,phase in enumerate(PHASES):transfer_mounts+=mount(volumes[phase],'/out/'+str(index))
    command(['docker','create','--name',transfer,*limits,'--user','0:0',*transfer_mounts,'--entrypoint','python',RUNTIME,'-c',script])
    command(['docker','cp',str(input_dir)+ '/.',transfer+':/input/'])
    command(['docker','start','--attach',transfer])
    manifest=dict(source_head=command(['git','rev-parse','HEAD']),prefix=prefix,image=image,runtime=RUNTIME,volumes=volumes,
        phase_seconds=PHASE_SECONDS,suite_seconds=SUITE_SECONDS,phases=list(PHASES),
        input_files={p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in input_dir.iterdir()},
        limits=dict(cpu=2,memory_bytes=2147483648,network='none',readonly_root=True,uid='10002:10002'),
        target_rule='Unchanged exact guide/original priors/Q64/optimizer; one model per process. No native NUTS in diagnosis.')
    write('deployment.json',manifest)
    started=time.monotonic();rows={};inspections={};results=[]
    for phase in PHASES:
        remaining=SUITE_SECONDS-(time.monotonic()-started)
        if remaining<=0:
            results.append(dict(phase=phase,status='not-qualified',reason='suite-deadline-before-launch'));break
        limit=min(PHASE_SECONDS,remaining);name=prefix+'-'+phase
        argv=['docker','run','--name',name,*limits,'--user','10002:10002',*mount(volumes['input'],'/input',True),*mount(volumes[phase],'/output')]
        if phase!='coordinates':argv+=mount(volumes['coordinates'],'/mapped',True)
        argv+=[image,'--input','/input','--output','/output','--phase',phase,'--seconds',str(limit)]
        if phase!='coordinates':argv+=['--coordinates','/mapped/coordinates.json']
        before=time.monotonic();outcome,metadata=run(argv,args.evidence/'commands',timeout_seconds=limit)
        elapsed=time.monotonic()-before
        raw=json.loads(command(['docker','inspect',name]))[0]
        if raw['State']['Running']:
            # Stopping the Docker CLI never counts as stopping computation.
            run(['docker','kill',name],args.evidence/'commands',timeout_seconds=30)
            raw=json.loads(command(['docker','inspect',name]))[0]
        state=raw['State']
        inspections[phase]=dict(Id=raw['Id'],Image=raw['Image'],User=raw['Config']['User'],State=state,
            Memory=raw['HostConfig']['Memory'],NanoCpus=raw['HostConfig']['NanoCpus'],NetworkMode=raw['HostConfig']['NetworkMode'],
            ReadonlyRootfs=raw['HostConfig']['ReadonlyRootfs'],Mounts=raw['Mounts'])
        write('isolation.json',inspections)
        if state['Running']:
            write('live-handle.json',dict(container=name,status='termination-unconfirmed',instruction='Preserve and stop this exact owned computation; no terminal qualification published.'))
            raise RuntimeError('actual computation termination unconfirmed: '+name)
        run(['docker','logs',name],args.evidence/'commands',timeout_seconds=30)
        directory=args.evidence/phase
        command(['docker','cp',name+':/output',str(directory)])
        reason=terminal_reason(state,outcome.returncode,elapsed,limit,metadata['timed_out'])
        if time.monotonic()-started>=SUITE_SECONDS:reason=reason or 'suite-deadline-exceeded'
        result=dict(phase=phase,container=name,elapsed_seconds=elapsed,limit_seconds=limit,status='not-qualified' if reason else 'evaluated',reason=reason)
        results.append(result);write('progress.json',results)
        if reason:break
        row=json.loads((directory/(phase+'.json')).read_bytes())
        if row['status']!='evaluated':raise ValueError('phase did not publish evaluation')
        rows[phase]=row
    reason=next((r['reason'] for r in results if r['reason']),None)
    if not reason:
        try:qualify(rows)
        except (ValueError,KeyError) as error:reason=str(error)
    elapsed=time.monotonic()-started
    if elapsed>=SUITE_SECONDS:reason=reason or 'suite-deadline-before-publication'
    result=dict(status='not-qualified' if reason else 'accepted',reason=reason,elapsed_seconds=elapsed,phases=results,
        boundary='Full-target fixed-point/resource diagnosis only; no posterior or fit acceptance.')
    write('result.json',result);print(json.dumps(result))
    if reason:raise SystemExit(1)


if __name__=='__main__':main()
