"""Unique immutable integrated command captures, bound to this checkout's merge."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent


def main():
    assert Path(subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], cwd=ROOT).decode().strip()).resolve() == ROOT.resolve()
    directory = OUT / 'c' / uuid.uuid4().hex
    directory.mkdir(parents=True, exist_ok=False)
    command = sys.argv[1:]
    if command and command[0] == '--': command = command[1:]
    assert command
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
    paths = subprocess.check_output(['git', 'ls-files', 'contracts', 'services', 'tests', 'tooling/foundation', 'web'], cwd=ROOT).decode().splitlines()
    sources = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}
    source_raw = (json.dumps(sources, indent=2)+'\n').encode()
    (directory / 'sources.json').write_bytes(source_raw)
    start = datetime.now(timezone.utc).isoformat()
    result = subprocess.run(command, cwd=ROOT, capture_output=True)
    (directory / 'stdout.log').write_bytes(result.stdout); (directory / 'stderr.log').write_bytes(result.stderr)
    metadata = dict(command=command, cwd=str(ROOT), head=head, started_at=start, ended_at=datetime.now(timezone.utc).isoformat(), exit_code=result.returncode,
                    dirty_status=subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT).decode(), sources_sha256=hashlib.sha256(source_raw).hexdigest(),
                    stdout_sha256=hashlib.sha256(result.stdout).hexdigest(), stderr_sha256=hashlib.sha256(result.stderr).hexdigest())
    (directory / 'command.json').write_bytes((json.dumps(metadata, indent=2)+'\n').encode())
    print('CAPTURE', directory.relative_to(ROOT).as_posix())
    print(result.stdout.decode('utf-8', errors='replace')); print(result.stderr.decode('utf-8', errors='replace'))
    raise SystemExit(result.returncode)


if __name__ == '__main__': main()
