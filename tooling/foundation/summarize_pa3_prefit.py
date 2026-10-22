"""Create bounded, source-bound review evidence without modifying frozen runs."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from capture import run
from run_pa3_prefit import reuse_origin


def sha(raw):return hashlib.sha256(raw).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--artifacts',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    commands=[]
    for path in sorted(args.artifacts.rglob('*.json')):
        value=json.loads(path.read_text())
        if not isinstance(value,dict) or 'command' not in value or 'source_snapshot' not in value:continue
        streams={name:dict(data,sha256_verified=sha((path.parent/data['path']).read_bytes())==data['sha256']) for name,data in value['streams'].items()}
        commands.append(dict(path=path.relative_to(args.artifacts).as_posix(),sha256=sha(path.read_bytes()),
            command=value['command'],source_head=value['source_head'],exit=value['exit'],seconds=value['elapsed_seconds'],
            timed_out=value.get('timed_out',False),source_snapshot_sha256=sha(json.dumps(value['source_snapshot'],sort_keys=True).encode()),streams=streams))
    (args.output/'commands-index.json').write_text(json.dumps(commands,indent=2)+'\n')
    for source,target in [('prefit-q16/prefit/result.json','q16-result.json'),('prefit-q64/prefit/result.json','q64-result.json'),
        ('resolution-diagnosis/resolution-diagnosis.json','resolution-diagnosis.json'),('watchdog/result.json','watchdog-result.json'),
        ('prefit-q16/isolation.json','q16-isolation.json'),('prefit-q64/isolation.json','q64-isolation.json')]:
        shutil.copyfile(args.artifacts/source,args.output/target)
    # Public artifacts contain no replay keys; private raw rows stay outside Git.
    public=args.output/'public';shutil.copytree(args.artifacts/'prefit-q16/studies/public',public)
    binding=[]
    deployments={name:json.loads((args.artifacts/name/'deployment.json').read_text()) for name in ('prefit-q16','prefit-q64')}
    # Every image is read by ID, network-none/read-only, and compared with the
    # source snapshot recorded for its actual Docker build command.
    for role,deployment in [('producer',deployments['prefit-q16']),('bridge',deployments['prefit-q16']),('bridge',deployments['prefit-q64'])]:
        image=deployment['images'][role]
        code="from pathlib import Path;import json,hashlib,os;print(json.dumps(dict(uid=os.getuid(),files={p.relative_to('/app').as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/app').rglob('*') if p.is_file() and '__pycache__' not in p.parts},generator_present=Path('/app/services/generator').exists(),foundation_present=Path('/app/services/foundation').exists(),socket_present=Path('/var/run/docker.sock').exists())))"
        outcome,metadata=run(['docker','run','--rm','--network','none','--cpus','2','--memory','2g','--read-only',
            '--cap-drop','ALL','--security-opt','no-new-privileges','--entrypoint','python',image,'-c',code],args.artifacts/'source-binding-commands',timeout_seconds=60)
        if outcome.returncode:raise RuntimeError(metadata)
        observed=json.loads(outcome.stdout)
        build_tag=('studies:candidate' if role=='producer' else 'bridge:candidate' if deployment is deployments['prefit-q16'] else 'bridge-r3:candidate')
        # Match the literal tag anywhere; order-independent command metadata.
        matches=[p for p in (args.artifacts/'build').glob('*.json') if any(str(a).endswith(build_tag) for a in json.loads(p.read_text()).get('command',[]))]
        if len(matches)!=1:raise ValueError('ambiguous image build binding')
        build=json.loads(matches[0].read_text());expected={}
        for name,value in observed['files'].items():
            source='tooling/foundation/qualify_pa3_bridge.py' if name=='qualify_pa3_bridge.py' else name
            if source not in build['source_snapshot']:raise ValueError('unexpected copied source '+source)
            expected[name]=build['source_snapshot'][source]['sha256']
        if observed['files']!=expected:raise ValueError('copied image/source mismatch')
        binding.append(dict(role=role,image=image,source_head=build['source_head'],build_metadata=matches[0].relative_to(args.artifacts).as_posix(),
            build_metadata_sha256=sha(matches[0].read_bytes()),copied_source_matches=True,**observed))
    # Retain both labels and authoritative identities: config digests were
    # mistakenly relayed once before actual engine/container identity readback.
    correction=dict(original_wrong_config_labels=dict(producer='sha256:9288c265fb518739f6ffcfaea0a99e1f1dc880f7efb7be4a86c16b7303b9dcd3',
        bridge='sha256:059793e90a4c202b0539cbdd9f7984cbbf2fc986047413e2924cfea5244c6827',
        tests='sha256:f82244fd45d5c5d7140fd3022f4acb076b822571bf43086b4dff2f4af623bfb6'),
        corrected_actual_engine_ids=dict(producer=deployments['prefit-q16']['images']['producer'],bridge=deployments['prefit-q16']['images']['bridge'],
        tests='sha256:0f1f0f5e4d543ec204833044a0b0dcb8a8b85f20b54fd928dd52e011e320bbd5'),
        authoritative_identity='docker inspect container.Image and docker image inspect .Id; preserve original BuildKit config labels as correction, never relabel runs')
    private=json.loads((args.artifacts/'prefit-q16/studies/private/preparation.json').read_text())
    original=deployments['prefit-q16'];reused=deployments['prefit-q64']
    checked,check_metadata=run(['docker','inspect',original['containers']['producer'],'--format','{{.Image}}'],args.artifacts/'source-binding-commands',timeout_seconds=30)
    if checked.returncode:raise RuntimeError(check_metadata)
    origin=reuse_origin(original,reused['images']['producer'],checked.stdout.decode().strip())
    original_public={p.name:sha(p.read_bytes()) for p in (args.artifacts/'prefit-q16/studies/public').glob('*.json')}
    reused_public={p.name:sha(p.read_bytes()) for p in (args.artifacts/'prefit-q64/studies/public').glob('*.json')}
    if original_public!=reused_public:raise ValueError('reused public summaries changed')
    origin.update(original_deployment_sha256=sha((args.artifacts/'prefit-q16/deployment.json').read_bytes()),
        reused_deployment_sha256=sha((args.artifacts/'prefit-q64/deployment.json').read_bytes()),
        public_summary_files=original_public,reuse_bytes_unchanged=True,
        correction='Original657 run used identical requested/original producer image;511 enforces this origin for differing future requested images. Original deployment files retained unmodified.')
    report=dict(deployments=deployments,source_bindings=binding,image_label_correction=correction,
        reused_producer_origin=origin,
        private_preparation_sha256=sha((args.artifacts/'prefit-q16/studies/private/preparation.json').read_bytes()),
        private_participants=private['private_participants'],unique_replay_namespaces=private['unique_replay_namespaces'],
        local_external_streams_disjoint=private['local_external_streams_disjoint'],
        raw_file_manifests={name:{p.relative_to(args.artifacts/name).as_posix():sha(p.read_bytes()) for p in sorted((args.artifacts/name).rglob('*')) if p.is_file() and p.suffix!='.stdout'} for name in ('prefit-q16','prefit-q64','watchdog','resolution-diagnosis')},
        qualification_scope='Public-model source marginal finite88point suite; no posterior fit, source admission, app usability, recovery or clinical acceptance')
    (args.output/'source-artifacts.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(files={p.relative_to(args.output).as_posix():sha(p.read_bytes()) for p in sorted(args.output.rglob('*')) if p.is_file()})))


if __name__=='__main__':main()
