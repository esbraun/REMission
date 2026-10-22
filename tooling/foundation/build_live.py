"""Task-private pinned builds; all child status/source/image bytes are captured."""
import argparse,hashlib,json,uuid
from pathlib import Path
from capture import run

ROOT=Path(__file__).resolve().parents[2]
RUNTIME='sha256:ce346feace2ae607ebd574e1bb681d594c9b676c06b56f8ba8d50b858a577faa'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--allow-pinned-npm-network',action='store_true');args=parser.parse_args()
    args.evidence.mkdir(parents=True,exist_ok=True);prefix='remission-lh-'+uuid.uuid4().hex[:12]
    def command(argv):
        result,metadata=run(argv,args.evidence/'c')
        if result.returncode:raise RuntimeError('captured child failure: '+metadata['streams']['stderr']['path'])
        return result
    def runtime():
        value=command(['docker','image','inspect','remission-foundation-runtime:candidate','--format','{{.Id}}']).stdout.decode().strip()
        if value!=RUNTIME:raise RuntimeError('pinned runtime tag mismatch')
    runtime();head=command(['git','rev-parse','HEAD']).stdout.decode().strip()
    lock=ROOT/'web/package-lock.json';lock_before=lock.read_bytes()
    source={}
    for directory in ['contracts/domain','contracts/runs','contracts/service','methods/visit','services/foundation','services/learner','services/generator','web','tooling/foundation','tests/integration/replay','tests/generator','tests/run_contracts']:
        for path in (ROOT/directory).rglob('*'):
            if path.is_file() and not any(p in ('node_modules','dist','__pycache__') for p in path.parts):
                source[path.relative_to(ROOT).as_posix()]=dict(bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    images={}
    for role,target,dockerfile in [('service','service','service'),('tests','integration-tests','service'),('learner',None,'learner'),('evaluator',None,'evaluator'),('generator',None,'generator')]:
        runtime();tag=prefix+'-'+role+':candidate'
        argv=['docker','build','--network','none','--file','tooling/foundation/'+dockerfile+'.Dockerfile','--tag',tag]
        if target:argv+=['--target',target]
        result,metadata=run([*argv,'.'],args.evidence/'c')
        if result.returncode:
            output=(result.stdout+result.stderr).decode(errors='replace')
            if not (args.allow_pinned_npm_network and dockerfile=='service' and 'npm ci' in output and any(t in output for t in ['EAI_AGAIN','ENOTFOUND','ECONNREFUSED'])):
                raise RuntimeError('captured build failure: '+metadata['streams']['stderr']['path'])
            argv[argv.index('none')]='default'
            command([*argv,'.'])
        images[role]=command(['docker','image','inspect',tag,'--format','{{.Id}}']).stdout.decode().strip()
    if lock.read_bytes()!=lock_before:raise RuntimeError('lock changed during pinned build')
    runtime()
    value=dict(source_head=head,source=source,images=images,prefix=prefix,runtime=RUNTIME,npm_lock_sha256=hashlib.sha256(lock_before).hexdigest(),network_exception='only pinned npm acquisition after captured offline DNS failure when explicitly enabled')
    path=args.evidence/'source-images.json';path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(source_head=head,images=images,prefix=prefix,manifest=str(path))))


if __name__=='__main__':main()
