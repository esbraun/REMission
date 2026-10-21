"""Append-only bounded check capture, always executed in this own worktree."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent / 'checks'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command
    if command and command[0] == '--':
        command = command[1:]
    if not command:
        raise SystemExit('command required')
    assert (ROOT / 'contracts/domain/observed_v2.py').is_file()
    actual = Path(subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], cwd=ROOT).decode().strip()).resolve()
    if actual != ROOT.resolve():
        raise SystemExit('runner root differs from its owning checkout')
    OUT.mkdir(parents=True, exist_ok=True)
    number = len(list(OUT.glob('*.command.json')))
    prefix = OUT / f'{number:03d}'
    if prefix.with_suffix('.command.json').exists():
        raise SystemExit('immutable evidence conflict')
    started = datetime.now(timezone.utc).isoformat()
    source_bytes = {}
    for directory in ['contracts', 'services', 'tests', 'tooling/foundation', 'web/src']:
        for path in (ROOT / directory).rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts and (path.suffix in ('.py', '.json', '.sql', '.Dockerfile', '.tsx', '.ts', '.mjs', '.css')):
                source_bytes[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    result = subprocess.run(command, cwd=ROOT, capture_output=True)
    prefix.with_suffix('.stdout.log').write_bytes(result.stdout)
    prefix.with_suffix('.stderr.log').write_bytes(result.stderr)
    metadata = dict(command=command, cwd=str(ROOT), started_at=started, ended_at=datetime.now(timezone.utc).isoformat(),
                    exit_code=result.returncode, head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
                    dirty_status=subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT).decode(),
                    executed_source_bytes_sha256=source_bytes,
                    stdout_sha256=hashlib.sha256(result.stdout).hexdigest(), stderr_sha256=hashlib.sha256(result.stderr).hexdigest())
    prefix.with_suffix('.command.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(result.stdout.decode('utf-8', errors='replace'))
    print(result.stderr.decode('utf-8', errors='replace'))
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
