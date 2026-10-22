"""Copied, capped, network-none PA3 source preparation and bridge qualification.

No source bind mounts. Each invocation gets new preserved task-private volumes.
The qualifier sees only a separate public-summary volume, never private rows.
"""
import argparse
import json
from pathlib import Path
import uuid
from capture import run

RUNTIME='sha256:ce346feace2ae607ebd574e1bb681d594c9b676c06b56f8ba8d50b858a577faa'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--producer-image',required=True);parser.add_argument('--bridge-image',required=True)
    parser.add_argument('--order',type=int,choices=(16,32,64),default=16)
    args=parser.parse_args();args.evidence.mkdir(parents=True,exist_ok=False)
    prefix='remission-pa3-sol-'+uuid.uuid4().hex[:12]
    def command(argv):
        result,metadata=run(argv,args.evidence/'commands')
        if result.returncode:raise RuntimeError('captured command failed: '+metadata['streams']['stderr']['path'])
        return result.stdout.decode().strip()
    runtime=command(['docker','image','inspect','remission-foundation-runtime:candidate','--format','{{.Id}}'])
    if runtime!=RUNTIME:raise ValueError('runtime tag mismatch')
    images={name:command(['docker','image','inspect',tag,'--format','{{.Id}}'])
            for name,tag in [('producer',args.producer_image),('bridge',args.bridge_image)]}
    volumes={name:prefix+'-'+name for name in ('private-preparation','public-input','bridge-output')}
    for volume in volumes.values():command(['docker','volume','create',volume])
    limits=['--network','none','--cpus','2','--memory','2g','--read-only','--cap-drop','ALL',
            '--security-opt','no-new-privileges','--tmpfs','/tmp:rw,nosuid,size=256m']
    mounts=lambda name,target,readonly=False:['--mount',f'type=volume,src={volumes[name]},dst={target}'+(',readonly' if readonly else '')]
    for name in volumes:
        command(['docker','run','--rm',*limits,'--user','0:0',*mounts(name,'/out'),'--entrypoint','python',RUNTIME,
                 '-c',"from pathlib import Path;Path('/out').chmod(0o777)"])
    producer=prefix+'-producer'
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
    (args.evidence/'deployment.json').write_text(json.dumps(manifest,indent=2)+'\n')
    # Copy the frozen private/public evidence before the numerical stage. These
    # immutable named volumes remain the authoritative originals.
    command(['docker','cp',producer+':/output/studies',str(args.evidence/'studies')])
    command(['docker','run','--name',bridge,*limits,*mounts('public-input','/input',True),
        *mounts('bridge-output','/output'),images['bridge'],'--sources','/input/source-7c97862d.json',
        '--output','/output/prefit','--order',str(args.order)])
    command(['docker','cp',bridge+':/output/prefit',str(args.evidence/'prefit')])
    inspection={}
    for name,container in [('producer',producer),('bridge',bridge)]:
        raw=json.loads(command(['docker','inspect',container]))[0]
        inspection[name]=dict(Id=raw['Id'],Image=raw['Image'],User=raw['Config']['User'],State=raw['State'],
            NetworkMode=raw['HostConfig']['NetworkMode'],ReadonlyRootfs=raw['HostConfig']['ReadonlyRootfs'],
            NanoCpus=raw['HostConfig']['NanoCpus'],Memory=raw['HostConfig']['Memory'],Mounts=raw['Mounts'])
    (args.evidence/'isolation.json').write_text(json.dumps(inspection,indent=2)+'\n')
    print(json.dumps(dict(manifest=manifest,result=json.loads((args.evidence/'prefit/result.json').read_text()))))


if __name__=='__main__':main()
