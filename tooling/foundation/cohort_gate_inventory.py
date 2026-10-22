"""Stdlib-only static production COPY inventory; never builds or runs a role."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shlex
import subprocess


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    tracked=subprocess.check_output(['git','-C',str(root),'ls-files'],text=True).splitlines()
    def identity(path):
        raw=(root/path).read_bytes()
        blob=subprocess.check_output(['git','-C',str(root),'hash-object','-w',path],text=True).strip()
        canonical=subprocess.check_output(['git','-C',str(root),'cat-file','-p',blob])
        return dict(source=path,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),git_blob=blob,
            git_sha256=hashlib.sha256(canonical).hexdigest(),
            association='exact' if raw==canonical else 'CRLF-LF-only' if raw.replace(b'\r\n',b'\n')==canonical else 'DIFFERENT')
    result=dict(kind='prepared static production role COPY inventory; no build or qualification',
        source_parent=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip(),
        immutable_dependencies='sha256:ce346feace2ae607ebd574e1bb681d594c9b676c06b56f8ba8d50b858a577faa',
        locks={p:identity(p) for p in ['tooling/foundation/requirements.lock','tooling/library/requirements.lock','web/package-lock.json']},
        roles={},host_dispatcher=identity('tooling/foundation/analysis_dispatcher.py'),
        probe_sources={p:identity(p) for p in ['tooling/foundation/consumer_probe.py','tooling/foundation/observed_v2_probe.py']})
    for role in ('learner','service'):
        dockerfile=f'tooling/foundation/{role}.Dockerfile';files={};generated=[]
        stage=role=='learner'
        for line in (root/dockerfile).read_text().splitlines():
            if line.startswith('FROM '):
                if ' AS service' in line:stage=True
                elif ' AS integration-tests' in line:stage=False
                continue
            if not stage or not line.startswith('COPY '):continue
            values=shlex.split(line)[1:]
            if values[0].startswith('--from='):
                generated.append(line);continue
            *sources,destination=values
            for source in sources:
                paths=[p for p in tracked if p.startswith(source)] if source.endswith('/') else [source]
                if not paths:raise ValueError('Empty COPY source '+source)
                for path in paths:
                    target=str(PurePosixPath(destination)/(path[len(source):] if source.endswith('/') else PurePosixPath(path).name)) if destination.endswith('/') else destination
                    if target in files:raise ValueError('Overlapping production COPY '+target)
                    files[target]=identity(path)
        result['roles'][role]=dict(dockerfile=identity(dockerfile),copied=files,generated_copy=generated,
            user='10002:10002' if role=='learner' else '10001:10001',
            no_source_overlays_required=True,actual_image=None,qualification='pending exact source freeze and independent review')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({r:len(v['copied']) for r,v in result['roles'].items()}))


if __name__=='__main__':main()
