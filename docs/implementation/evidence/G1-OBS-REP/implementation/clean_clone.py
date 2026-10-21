"""Reproduce the committed candidate from an isolated fresh own-source clone."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent / 'clone-attempts'


def main():
    OUT.mkdir(exist_ok=True)
    target = OUT / f'{len(list(OUT.iterdir())):03d}'
    target.mkdir(exist_ok=False)
    commands = []
    def run(command, *, cwd=ROOT):
        n = len(commands)
        started = datetime.now(timezone.utc).isoformat()
        result = subprocess.run(command, cwd=cwd, capture_output=True)
        (target / f'{n:03d}.stdout.log').write_bytes(result.stdout)
        (target / f'{n:03d}.stderr.log').write_bytes(result.stderr)
        commands.append(dict(command=command, cwd=str(cwd), started_at=started, ended_at=datetime.now(timezone.utc).isoformat(), exit_code=result.returncode,
                             stdout_sha256=hashlib.sha256(result.stdout).hexdigest(), stderr_sha256=hashlib.sha256(result.stderr).hexdigest()))
        (target / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n', encoding='utf-8', newline='\n')
        if result.returncode:
            raise RuntimeError(f'clean clone command {n} failed: ' + result.stderr.decode(errors='replace'))
        return result.stdout.decode().strip()
    head = run(['git', 'rev-parse', 'HEAD'])
    with tempfile.TemporaryDirectory(prefix='remission-obs2-portability-') as temporary:
        # Verified explicit own temporary target before recursive cleanup.
        base = Path(temporary).resolve()
        assert base.parent == Path(tempfile.gettempdir()).resolve() and base.name.startswith('remission-obs2-portability-')
        clone = base / 'checkout'
        run(['git', 'clone', '--no-hardlinks', '--config', 'core.autocrlf=false', '--no-checkout', str(ROOT), str(clone)])
        run(['git', 'checkout', '--detach', head], cwd=clone)
        assert run(['git', 'rev-parse', 'HEAD'], cwd=clone) == head
        assert run(['git', 'status', '--porcelain'], cwd=clone) == ''
        paths = run(['git', 'ls-files', 'contracts', 'services', 'tests', 'tooling/foundation', 'web/src'], cwd=clone).splitlines()
        actual = {p: hashlib.sha256((clone / p).read_bytes()).hexdigest() for p in paths if p.endswith(('.py', '.json', '.sql', '.Dockerfile', '.tsx', '.ts', '.mjs', '.css'))}
        (target / 'executed-source.json').write_text(json.dumps(dict(head=head, clone_initially_clean=True, core_autocrlf=False,
             executed_source_bytes_sha256=actual, limitation='Old checkout CRLF transformations are explicit; new source LF attributes and raw evidence bytes are preserved'), indent=2) + '\n', encoding='utf-8', newline='\n')
        docker = ['docker', 'run', '--rm', '--cpus', '2', '--memory', '2g', '--network', 'none', '--read-only', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges:true',
                  '--tmpfs', '/tmp:rw,noexec,nosuid,size=128m', '--mount', f'type=bind,source={clone.as_posix()},target=/app,readonly', '--workdir', '/app', 'remission-foundation-runtime:candidate', 'python']
        for command in [['docs/implementation/evidence/G1-OBS-REP/implementation/schema_checks.py'],
                        ['-m', 'unittest', 'discover', '-s', 'tests/contracts', '-v'],
                        ['-m', 'unittest', 'discover', '-s', 'tests/run_contracts', '-v'],
                        ['-m', 'unittest', 'discover', '-s', 'tests/integration/replay', '-v']]:
            run([*docker, *command])
        run([sys.executable, 'docs/implementation/check-ledger-20261020.py'], cwd=clone)
        baseline = json.loads((clone / 'docs/implementation/evidence/G1-OBS-REP/implementation/v1-byte-inventory-raw.json').read_bytes())
        for item in baseline['files']:
            assert run(['git', 'hash-object', '--path', item['path'], item['path']], cwd=clone) == item['git_blob']
        assert run(['git', 'status', '--porcelain'], cwd=clone) == ''
    print('PASS: isolated clean committed clone; exact executed source hashes; old/new schema and runtime/artifact/DR checks; domain/run/service groups; 635 mappings and original v1 blobs; no checkout mutations')


if __name__ == '__main__':
    main()
