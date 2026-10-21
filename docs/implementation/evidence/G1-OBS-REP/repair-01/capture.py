"""Append-only repair checks, confined to this new task checkout."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent


def main():
    actual = Path(subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], cwd=ROOT).decode().strip()).resolve()
    assert ROOT.resolve() == actual, 'repair runner belongs only to its containing checkout'
    commands = OUT / 'checks'
    commands.mkdir(exist_ok=True)
    stem = commands / f'{len(list(commands.glob("*.command.json"))):03d}'
    assert not stem.with_suffix('.command.json').exists()
    command = sys.argv[1:]
    if command and command[0] == '--':
        command = command[1:]
    assert command
    started = datetime.now(timezone.utc).isoformat()
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
    status = subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT).decode()
    paths = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', 'contracts', 'services', 'tests', 'tooling/foundation', 'web'], cwd=ROOT).decode().splitlines()
    snapshots = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths if (ROOT / p).is_file()}
    result = subprocess.run(command, cwd=ROOT, capture_output=True)
    stem.with_suffix('.stdout.log').write_bytes(result.stdout)
    stem.with_suffix('.stderr.log').write_bytes(result.stderr)
    metadata = dict(command=command, cwd=str(ROOT), head=head, dirty_before=status, source_bytes_sha256=snapshots,
                    started_at=started, ended_at=datetime.now(timezone.utc).isoformat(), exit_code=result.returncode,
                    stdout_sha256=hashlib.sha256(result.stdout).hexdigest(), stderr_sha256=hashlib.sha256(result.stderr).hexdigest())
    stem.with_suffix('.command.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(result.stdout.decode('utf-8', errors='replace'))
    print(result.stderr.decode('utf-8', errors='replace'))
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
