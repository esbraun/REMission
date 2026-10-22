"""One capped diagnostic gradient, frozen old inputs RO, new output only."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import uuid
from capture import run
from run_pa3_compile import terminal_reason,RUNTIME

ROOT=Path(__file__).resolve().parents[2]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--image',required=True);parser.add_argument('--evidence',type=Path,required=True)
    args=parser.parse_args();args.evidence.mkdir(parents=True,exist_ok=False);started=time.monotonic()
    def write(name,value):(args.evidence/name).write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n')
    def command(argv,seconds=30):
        outcome,metadata=run(argv,args.evidence/'commands',timeout_seconds=seconds)
        if outcome.returncode:raise RuntimeError('captured command failed: '+metadata['streams']['stderr']['path'])
        return outcome.stdout.decode().strip()
    policy_path=ROOT/'tooling/foundation/pa3-monitor-policy.json';policy=json.loads(policy_path.read_bytes())
    if (policy['phase_seconds'],policy['suite_seconds'])!=(600,1800):raise ValueError('unfrozen diagnosis deadlines')
    image=command(['docker','image','inspect',args.image,'--format','{{.Id}}'])
    if command(['docker','image','inspect','remission-foundation-runtime:candidate','--format','{{.Id}}'])!=RUNTIME:
        raise ValueError('runtime tag mismatch')
    prefix='remission-pa3-monitor-'+uuid.uuid4().hex[:12];volume=prefix+'-output';container=prefix+'-gradient'
    command(['docker','volume','create',volume])
    limits=['--network','none','--cpus','2','--memory','2g','--read-only','--cap-drop','ALL',
        '--security-opt','no-new-privileges','--tmpfs','/tmp:rw,nosuid,size=512m']
    mount=lambda name,path,ro=False:['--mount',f'type=volume,src={name},dst={path}'+(',readonly' if ro else '')]
    command(['docker','run','--rm',*limits,'--user','0:0',*mount(volume,'/output'),'--entrypoint','python',RUNTIME,
        '-c',"from pathlib import Path;Path('/output').chmod(0o777)"])
    manifest=dict(source_head=command(['git','rev-parse','HEAD']),image=image,original_input_image=policy['original_image'],runtime=RUNTIME,
        prefix=prefix,container=container,output_volume=volume,readonly_volumes={k:policy['volumes'][k] for k in ['input','coordinates','guided-logp']},
        policy=policy,policy_file_sha256=hashlib.sha256(policy_path.read_bytes()).hexdigest(),
        boundary='Diagnostic MonitorMode linker only, unchanged default optimizer/target; no NUTS, production timeliness or full-target acceptance.')
    write('deployment.json',manifest)
    remaining=policy['suite_seconds']-(time.monotonic()-started)
    if remaining<=0:raise TimeoutError('suite deadline before launch; no computation started')
    limit=min(policy['phase_seconds'],remaining)
    argv=['docker','run','--name',container,*limits,'--user','10002:10002',
        *mount(policy['volumes']['input'],'/input',True),*mount(policy['volumes']['coordinates'],'/mapped',True),
        *mount(policy['volumes']['guided-logp'],'/reference',True),*mount(volume,'/output'),image,
        '--input','/input','--output','/output','--phase','guided-gradient','--seconds',str(limit),
        '--coordinates','/mapped/coordinates.json','--monitor-policy','/app/pa3-monitor-policy.json','--reference','/reference/guided-logp.json']
    phase_started=time.monotonic();outcome,metadata=run(argv,args.evidence/'commands',timeout_seconds=limit)
    phase_elapsed=time.monotonic()-phase_started
    raw=json.loads(command(['docker','inspect',container]))[0]
    if raw['State']['Running']:
        run(['docker','kill',container],args.evidence/'commands',timeout_seconds=30)
        raw=json.loads(command(['docker','inspect',container]))[0]
    state=raw['State']
    isolation=dict(Id=raw['Id'],Image=raw['Image'],State=state,User=raw['Config']['User'],Memory=raw['HostConfig']['Memory'],
        NanoCpus=raw['HostConfig']['NanoCpus'],NetworkMode=raw['HostConfig']['NetworkMode'],ReadonlyRootfs=raw['HostConfig']['ReadonlyRootfs'],Mounts=raw['Mounts'])
    write('isolation.json',isolation)
    if state['Running']:
        write('live-handle.json',dict(container=container,status='termination-unconfirmed',instruction='Stop exact owned computation; no terminal qualification published.'))
        raise RuntimeError('actual computation termination unconfirmed: '+container)
    run(['docker','logs',container],args.evidence/'commands',timeout_seconds=30)
    command(['docker','cp',container+':/output',str(args.evidence/'output')])
    reason=terminal_reason(state,outcome.returncode,phase_elapsed,limit,metadata['timed_out'])
    if time.monotonic()-started>=policy['suite_seconds']:reason=reason or 'suite-deadline-exceeded'
    phase=None
    if reason is None:
        phase=json.loads((args.evidence/'output/guided-gradient.json').read_bytes())
        if phase['status']!='evaluated' or not phase.get('independent_fd',{}).get('passed') or not phase['trace']['finished']:
            reason='incomplete-gradient-or-FD-check'
    result=dict(status='not-qualified' if reason else 'evaluated-gradient-diagnostic-only',reason=reason,
        elapsed_seconds=time.monotonic()-started,phase_elapsed_seconds=phase_elapsed,phase_limit_seconds=limit,
        independent_fd=phase.get('independent_fd') if phase else None,trace=phase.get('trace') if phase else None,
        scope=manifest['boundary'])
    if result['elapsed_seconds']>=policy['suite_seconds']:
        reason='suite-deadline-before-publication';result.update(status='not-qualified',reason=reason)
    write('result.json',result);print(json.dumps(result))
    if reason:raise SystemExit(1)


if __name__=='__main__':main()
