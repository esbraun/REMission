"""UUID command evidence; retain failures and exact stdout/stderr bytes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid


def run(command,evidence):
    evidence=Path(evidence)
    evidence.mkdir(parents=True,exist_ok=True)
    stem = uuid.uuid4().hex
    source_paths=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','--',
        'contracts','services','tests','web/src','web/package.json','web/package-lock.json','tooling/foundation',
        '.gitattributes','.dockerignore','docs/implementation/g0-task-test-ledger-20261020.json']).decode('utf-8').splitlines()
    source_snapshot={}
    for name in sorted(set(source_paths)):
        source=Path(name)
        if source.is_file():
            raw=source.read_bytes();source_snapshot[name]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    head=subprocess.check_output(['git','rev-parse','HEAD']).decode().strip()
    start = time.time()
    result = subprocess.run(command, capture_output=True)
    paths = {}
    for name, payload in [('stdout', result.stdout), ('stderr', result.stderr)]:
        path = evidence / (stem + '.' + name)
        path.write_bytes(payload)
        paths[name] = dict(path=path.name, bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest())
    metadata = dict(command=command, cwd=str(Path.cwd()), started_unix=start,
                    elapsed_seconds=time.time()-start, exit=result.returncode, streams=paths,source_head=head,source_snapshot=source_snapshot)
    (evidence / (stem + '.json')).write_text(json.dumps(metadata, indent=2)+'\n', encoding='utf-8')
    return result,metadata


def main():
    sys.stdout.reconfigure(encoding='utf-8',errors='backslashreplace')
    sys.stderr.reconfigure(encoding='utf-8',errors='backslashreplace')
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    result,metadata=run(command,args.evidence)
    display={k:v for k,v in metadata.items() if k!='source_snapshot'}
    display['source_paths']=len(metadata['source_snapshot'])
    print(json.dumps(display))
    print(result.stdout.decode('utf-8', errors='replace'))
    print(result.stderr.decode('utf-8', errors='replace'))
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
