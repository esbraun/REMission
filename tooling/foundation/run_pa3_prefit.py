"""Copied, capped, network-none PA3 source preparation and bridge qualification.

No source bind mounts. Each invocation gets new preserved task-private volumes.
The qualifier sees only a separate public-summary volume, never private rows.
"""
import argparse
import hashlib
import json
from pathlib import Path
import uuid
from capture import run

RUNTIME='sha256:ce346feace2ae607ebd574e1bb681d594c9b676c06b56f8ba8d50b858a577faa'


def bounded_container(argv, name, evidence, seconds):
    outcome,metadata=run(argv,evidence,timeout_seconds=seconds)
    if metadata['timed_out']:
        stopped,stop_metadata=run(['docker','kill',name],evidence,timeout_seconds=30)
        inspected,inspect_metadata=run(['docker','inspect',name,'--format','{{.State.Running}}'],evidence,timeout_seconds=30)
        if stopped.returncode or inspected.returncode or inspected.stdout.strip()!=b'false':
            raise RuntimeError('timed-out computation termination unconfirmed; preserve live handle '+name)
        run(['docker','logs',name],evidence,timeout_seconds=30)
    return outcome,metadata


def reuse_origin(original, requested_producer, actual_producer):
    if original['images']['producer']!=actual_producer:
        raise ValueError('original producer container/image binding mismatch')
    return dict(image=actual_producer,container=original['containers']['producer'],
        original_host_source_head=original['source_head'],
        requested_unused_producer_image=requested_producer,
        origin_rule='reuse original producer identity; new producer argument is unused and cannot relabel original bytes')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--producer-image',required=True);parser.add_argument('--bridge-image',required=True)
    parser.add_argument('--existing-preparation',type=Path)
    parser.add_argument('--order',type=int,choices=(16,32,64),default=16)
    args=parser.parse_args();args.evidence.mkdir(parents=True,exist_ok=False)
    prefix='remission-pa3-sol-'+uuid.uuid4().hex[:12]
    def command(argv,timeout_seconds=60):
        result,metadata=run(argv,args.evidence/'commands',timeout_seconds=timeout_seconds)
        if result.returncode:raise RuntimeError('captured command failed: '+metadata['streams']['stderr']['path'])
        return result.stdout.decode().strip()
    runtime=command(['docker','image','inspect','remission-foundation-runtime:candidate','--format','{{.Id}}'])
    if runtime!=RUNTIME:raise ValueError('runtime tag mismatch')
    images={name:command(['docker','image','inspect',tag,'--format','{{.Id}}'])
            for name,tag in [('producer',args.producer_image),('bridge',args.bridge_image)]}
    original=json.loads(args.existing_preparation.read_text()) if args.existing_preparation else None
    producer_origin=None
    if original:
        actual=command(['docker','inspect',original['containers']['producer'],'--format','{{.Image}}'])
        producer_origin=reuse_origin(original,images['producer'],actual)
        images['producer']=producer_origin['image']
    volumes={name:(original['volumes'][name] if original and name!='bridge-output' else prefix+'-'+name)
             for name in ('private-preparation','public-input','bridge-output')}
    for name,volume in volumes.items():
        if not original or name=='bridge-output':command(['docker','volume','create',volume])
    limits=['--network','none','--cpus','2','--memory','2g','--read-only','--cap-drop','ALL',
            '--security-opt','no-new-privileges','--tmpfs','/tmp:rw,nosuid,size=256m']
    mounts=lambda name,target,readonly=False:['--mount',f'type=volume,src={volumes[name]},dst={target}'+(',readonly' if readonly else '')]
    for name in volumes:
        if original and name!='bridge-output':continue
        command(['docker','run','--rm',*limits,'--user','0:0',*mounts(name,'/out'),'--entrypoint','python',RUNTIME,
                 '-c',"from pathlib import Path;Path('/out').chmod(0o777)"])
    producer=original['containers']['producer'] if original else prefix+'-producer'
    if not original:
        command(['docker','run','--name',producer,*limits,*mounts('private-preparation','/output'),images['producer'],
                 '--output','/output/studies'])
        # This one-shot custody transfer copies exactly the public summary files.
        command(['docker','run','--rm',*limits,'--user','0:0',*mounts('private-preparation','/prepared',True),
            *mounts('public-input','/input'),'--entrypoint','python',RUNTIME,'-c',
            "from pathlib import Path;import shutil;source=Path('/prepared/studies/public');target=Path('/input');"
            "[(shutil.copyfile(p,target/p.name),(target/p.name).chmod(0o444)) for p in source.glob('*.json')];target.chmod(0o555)"])
    bridge=prefix+'-bridge'
    manifest=dict(prefix=prefix,runtime=runtime,images=images,volumes=volumes,source_head=command(['git','rev-parse','HEAD']),
        source_bundle='source-7c97862d',order=args.order,containers=dict(producer=producer,bridge=bridge),
        boundary='private producer output transferred once to distinct summary-only input volume; input mounted read-only; no source binds')
    manifest['existing_preparation']=str(args.existing_preparation) if original else None
    manifest['existing_preparation_sha256']=hashlib.sha256(args.existing_preparation.read_bytes()).hexdigest() if original else None
    manifest['producer_origin']=producer_origin
    manifest['watchdog_seconds']=1860
    (args.evidence/'deployment.json').write_text(json.dumps(manifest,indent=2)+'\n')
    # Copy the frozen private/public evidence before the numerical stage. These
    # immutable named volumes remain the authoritative originals.
    command(['docker','cp',producer+':/output/studies',str(args.evidence/'studies')])
    manifest['public_summary_files']={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((args.evidence/'studies/public').glob('*.json'))}
    (args.evidence/'deployment.json').write_text(json.dumps(manifest,indent=2)+'\n')
    argv=['docker','run','--name',bridge,*limits,*mounts('public-input','/input',True),
        *mounts('bridge-output','/output'),images['bridge'],'--sources','/input/source-7c97862d.json',
        '--output','/output/prefit','--order',str(args.order)]
    outcome,metadata=bounded_container(argv,bridge,args.evidence/'commands',manifest['watchdog_seconds'])
    command(['docker','cp',bridge+':/output',str(args.evidence/'bridge-output')])
    if not metadata['timed_out']:
        command(['docker','cp',bridge+':/output/prefit',str(args.evidence/'prefit')])
    inspection={}
    for name,container in [('producer',producer),('bridge',bridge)]:
        raw=json.loads(command(['docker','inspect',container]))[0]
        inspection[name]=dict(Id=raw['Id'],Image=raw['Image'],User=raw['Config']['User'],State=raw['State'],
            NetworkMode=raw['HostConfig']['NetworkMode'],ReadonlyRootfs=raw['HostConfig']['ReadonlyRootfs'],
            NanoCpus=raw['HostConfig']['NanoCpus'],Memory=raw['HostConfig']['Memory'],Mounts=raw['Mounts'])
    (args.evidence/'isolation.json').write_text(json.dumps(inspection,indent=2)+'\n')
    if outcome.returncode:
        (args.evidence/'failure.json').write_text(json.dumps(dict(status='not-qualified',reason='external-watchdog' if metadata['timed_out'] else 'process-failure',exit=outcome.returncode,computation_verified_stopped=not inspection['bridge']['State']['Running']))+'\n')
        raise RuntimeError('qualification process failed; retained logs and output')
    print(json.dumps(dict(manifest=manifest,result=json.loads((args.evidence/'prefit/result.json').read_text()))))


if __name__=='__main__':main()
