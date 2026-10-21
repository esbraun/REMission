"""UUID command evidence; retain failures and exact stdout/stderr bytes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
import uuid


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    args.evidence.mkdir(parents=True, exist_ok=True)
    stem = uuid.uuid4().hex
    start = time.time()
    result = subprocess.run(command, capture_output=True)
    paths = {}
    for name, payload in [('stdout', result.stdout), ('stderr', result.stderr)]:
        path = args.evidence / (stem + '.' + name)
        path.write_bytes(payload)
        paths[name] = dict(path=path.name, bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest())
    metadata = dict(command=command, cwd=str(Path.cwd()), started_unix=start,
                    elapsed_seconds=time.time()-start, exit=result.returncode, streams=paths)
    (args.evidence / (stem + '.json')).write_text(json.dumps(metadata, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(metadata))
    print(result.stdout.decode('utf-8', errors='replace'))
    print(result.stderr.decode('utf-8', errors='replace'))
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
