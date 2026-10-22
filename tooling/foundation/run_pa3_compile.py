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
NUMBA_PHASES=('guided-gradient','guided-native-logp-gradient','guided-logp','original-logp','original-gradient','local-logp','changed-logp')
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
    if 'guided-native-logp-gradient' in rows:
        native=rows['guided-native-logp-gradient'];separate=rows['guided-gradient']
        if native['value_variable_order']!=separate['value_variable_order']:raise ValueError('native/separate coordinate ordering mismatch')
        mapping=native['native_coordinate_map']
        if [m['name'] for m in mapping]!=separate['value_variable_order'] or mapping[0]['start']!=0 or mapping[-1]['stop']!=47:
            raise ValueError('native coordinate map mismatch')
        for a,b in zip(mapping,mapping[1:]):
            if a['stop']!=b['start']:raise ValueError('native coordinate gap/overlap')
        for point,(actual,expected) in enumerate(zip(native['values'],separate['values'],strict=True)):
            for a,b in zip(actual,expected,strict=True):close(a,b,1e-5,1e-4)
            close(native['native_logp'][point],rows['guided-logp']['values'][point],1e-8)


def phase_row(path,phase,contrast):
    row=json.loads(path.read_bytes())
    if row['status']!='evaluated':raise ValueError('phase did not publish evaluation')
    if contrast and phase in NUMBA_PHASES[:2] and not row.get('independent_fd',{}).get('passed'):
        raise ValueError('first contrast/native FD gate missing; stop before next phase')
    return row


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--image',required=True);parser.add_argument('--evidence',type=Path,required=True)
    policies=parser.add_mutually_exclusive_group();policies.add_argument('--numba-policy',type=Path);policies.add_argument('--cvm-policy',type=Path)
    args=parser.parse_args();args.evidence.mkdir(parents=True,exist_ok=False)
    def command(argv,seconds=60):
        outcome,metadata=run(argv,args.evidence/'commands',timeout_seconds=seconds)
        if outcome.returncode:raise RuntimeError('captured command failed: '+metadata['streams']['stderr']['path'])
        return outcome.stdout.decode().strip()
    def write(name,value):(args.evidence/name).write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n')
    policy_path=args.numba_policy or args.cvm_policy
    policy=json.loads(policy_path.read_bytes()) if policy_path else None
    if policy and (policy['id']!=('pa3-cvm-target-qualification-v1' if args.cvm_policy else 'pa3-numba-fusion-contrast-v1') or policy['version']!='1.0.0' or
                   (policy['phase_seconds'],policy['suite_seconds'])!=(PHASE_SECONDS,SUITE_SECONDS)):
        raise ValueError('unfrozen numba contrast policy/deadlines')
    phases=NUMBA_PHASES if policy else PHASES
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
    volumes=dict(input=prefix+'-input',**{phase:prefix+'-'+phase for phase in phases})
    for volume in volumes.values():command(['docker','volume','create',volume])
    rows={}
    if policy:
        if {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in input_dir.iterdir()}!=policy['input_files']:raise ValueError('contrast input freeze mismatch')
        mapped=ROOT/policy['coordinates_file']
        if hashlib.sha256(mapped.read_bytes()).hexdigest()!=policy['coordinates_sha256']:raise ValueError('coordinate map freeze mismatch')
        rows['coordinates']=json.loads(mapped.read_bytes())
        volumes['coordinates']=policy['readonly_volumes']['coordinates']
    limits=['--network','none','--cpus','2','--memory','2g','--read-only','--cap-drop','ALL',
        '--security-opt','no-new-privileges','--tmpfs','/tmp:rw,nosuid,size=512m']
    if policy:limits[-1]='/tmp:rw,exec,nosuid,nodev,size=512m'
    mount=lambda volume,path,ro=False:['--mount',f'type=volume,src={volume},dst={path}'+(',readonly' if ro else '')]
    transfer=prefix+'-transfer'
    # Root is used only for this offline, public-file custody transfer.
    script="from pathlib import Path;root=Path('/input');[(p.chmod(0o444)) for p in root.iterdir()];root.chmod(0o555);[(Path('/out')/str(i)).chmod(0o777) for i in range(7)]"
    transfer_mounts=[*mount(volumes['input'],'/input')]
    for index,phase in enumerate(phases):transfer_mounts+=mount(volumes[phase],'/out/'+str(index))
    command(['docker','create','--name',transfer,*limits,'--user','0:0',*transfer_mounts,'--entrypoint','python',RUNTIME,'-c',script])
    command(['docker','cp',str(input_dir)+ '/.',transfer+':/input/'])
    command(['docker','start','--attach',transfer])
    manifest=dict(source_head=command(['git','rev-parse','HEAD']),prefix=prefix,image=image,runtime=RUNTIME,volumes=volumes,
        phase_seconds=PHASE_SECONDS,suite_seconds=SUITE_SECONDS,phases=list(phases),
        input_files={p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in input_dir.iterdir()},
        limits=dict(cpu=2,memory_bytes=2147483648,network='none',readonly_root=True,uid='10002:10002'),
        target_rule='Unchanged exact guide/original priors/Q64/optimizer; one model per process. No native NUTS in diagnosis.')
    if policy:
        manifest.update(compilation_policy=policy,compilation_policy_sha256=hashlib.sha256(policy_path.read_bytes()).hexdigest(),
            target_rule='Diagnostic CVM linker/original optimizer, unchanged math/prior/guide/Q64; no NUTS or production change.' if args.cvm_policy else
                        'Diagnostic compile-specific fusion-group exclusion; ordinary NumbaLinker, unchanged math/prior/guide/Q64. No NUTS or production change.',
            reused_coordinates_origin=policy['coordinates_origin'],reference_volumes=policy['readonly_volumes'])
    write('deployment.json',manifest)
    started=time.monotonic();inspections={};results=[]
    for phase in phases:
        remaining=SUITE_SECONDS-(time.monotonic()-started)
        if remaining<=0:
            results.append(dict(phase=phase,status='not-qualified',reason='suite-deadline-before-launch'));break
        limit=min(PHASE_SECONDS,remaining);name=prefix+'-'+phase
        argv=['docker','run','--name',name,*limits,'--user','10002:10002',*mount(volumes['input'],'/input',True),*mount(volumes[phase],'/output')]
        if phase!='coordinates':argv+=mount(volumes['coordinates'],'/mapped',True)
        if policy:
            argv+=mount(policy['readonly_volumes']['guided-logp'],'/reference',True)
            argv+=mount(policy['readonly_volumes']['diagnostic-gradient'],'/diagnostic',True)
        argv+=[image,'--input','/input','--output','/output','--phase',phase,'--seconds',str(limit)]
        if phase!='coordinates':argv+=['--coordinates','/mapped/coordinates.json']
        if policy:argv+=['--cvm-policy' if args.cvm_policy else '--numba-policy','/app/pa3-cvm-policy.json' if args.cvm_policy else '/app/pa3-numba-policy.json',
                         '--reference','/reference/guided-logp.json','--diagnostic-reference','/diagnostic/guided-gradient.json']
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
        try:row=phase_row(directory/(phase+'.json'),phase,bool(policy))
        except (ValueError,KeyError,FileNotFoundError) as error:
            results[-1].update(status='not-qualified',reason=str(error));write('progress.json',results);break
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
