"""Recheck exact independently qualified image bytes before own isolated UID probes."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import uuid

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
RUNTIME = 'sha256:ce346feace2ae607ebd574e1bb681d594c9b676c06b56f8ba8d50b858a577faa'


def main():
    ready = json.loads((OUT / 'ready-manifest.json').read_bytes())
    def original(path): return (OUT / 'b' / ready['files'][path]['git_blob']).read_bytes()
    previous = json.loads(original('curated-attempts/000/inventory.json'))['roles']
    evaluator = json.loads(original('curated-attempts/000/015.stdout.log'))[0]['Image']
    images = {role: item['image'] for role, item in previous.items()}
    images.update(evaluator=evaluator, runtime=RUNTIME)
    directory = OUT / 'roles' / uuid.uuid4().hex
    directory.mkdir(parents=True, exist_ok=False)
    commands = []; containers = []; volumes = []; networks = []
    prefix = 'remission-obs2-integrated-sol-' + directory.name[:8]
    label = 'remission.task=obs2-integrated-sol-20261021'
    def run(command, check=True):
        start = datetime.now(timezone.utc).isoformat(); result = subprocess.run(command, cwd=ROOT, capture_output=True)
        number = len(commands)
        (directory / f'{number:03d}.stdout.log').write_bytes(result.stdout); (directory / f'{number:03d}.stderr.log').write_bytes(result.stderr)
        commands.append(dict(command=command, cwd=str(ROOT), start=start, end=datetime.now(timezone.utc).isoformat(), exit_code=result.returncode,
                             stdout_sha256=hashlib.sha256(result.stdout).hexdigest(), stderr_sha256=hashlib.sha256(result.stderr).hexdigest()))
        (directory / 'commands.json').write_bytes((json.dumps(commands, indent=2)+'\n').encode())
        if check and result.returncode: raise RuntimeError('integrated role command failed: '+str(number)+' '+result.stderr.decode(errors='replace'))
        return result.stdout.decode().strip()
    limits = ['--cpus', '2', '--memory', '2g', '--read-only', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges:true', '--tmpfs', '/tmp:rw,noexec,nosuid,size=128m']
    try:
        for role, identifier in images.items():
            assert json.loads(run(['docker', 'image', 'inspect', identifier]))[0]['Id'] == identifier
        # Qualify exact image/probe bytes against the merged checkout BEFORE
        # reuse. These audit containers have no source mounts or network.
        for role, item in previous.items():
            expected = item['exact_source_sha256']
            for path, digest in expected.items():
                assert hashlib.sha256((ROOT / item['source_paths'][path]).read_bytes()).hexdigest() == digest, path
            code = 'import hashlib,json;from pathlib import Path;expected='+repr(expected)+';actual={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in expected};assert actual==expected;print(json.dumps(actual,sort_keys=True))'
            run(['docker', 'run', '--rm', '--name', prefix+'-'+role+'-byte-audit', '--label', label, '--network', 'none', *limits, images[role], 'python', '-c', code])
        canary_hash = hashlib.sha256((ROOT / 'tooling/foundation/evaluator_canary.py').read_bytes()).hexdigest()
        run(['docker', 'run', '--rm', '--name', prefix+'-evaluator-byte-audit', '--label', label, '--network', 'none', *limits, evaluator, 'python', '-c',
             "import hashlib;from pathlib import Path;assert hashlib.sha256(Path('/app/evaluator_canary.py').read_bytes()).hexdigest()=='"+canary_hash+"';print('exact merged evaluator canary bytes')"])
        truth, public = prefix+'-truth', prefix+'-public'
        for name in [truth, public]: run(['docker', 'volume', 'create', '--label', label, name]); volumes.append(name)
        seed = prefix+'-seed'
        code = "import os,json;from pathlib import Path,PurePosixPath;p=Path('/truth');os.chown(p,20000,20000);os.chmod(p,0o700);p.joinpath('canary.json').write_text('{\"kind\":\"private_foundation_canary\"}');os.chown(p/'canary.json',20000,20000);os.chmod(p/'canary.json',0o600);r=Path('/app/docs/implementation/evidence/G1-OBS-REP/integrated');m=json.loads((r/'ready-manifest.json').read_bytes());prefix='curated-attempts/000/public-v2/';count=0\nfor path,item in m['files'].items():\n if path.startswith(prefix):\n  rel=PurePosixPath(path.removeprefix(prefix));assert not rel.is_absolute() and '..' not in rel.parts;t=Path('/public-v2').joinpath(*rel.parts);t.parent.mkdir(parents=True,exist_ok=True);t.write_bytes((r/'b'/item['git_blob']).read_bytes());count+=1\nprint('Seeded unchanged independently qualified public wire files',count)"
        run(['docker', 'create', '--name', seed, '--label', label, '--network', 'none', '--cpus', '2', '--memory', '2g', '--user', '0:0',
             '--mount', f'type=bind,source={ROOT.as_posix()},target=/app,readonly', '--mount', f'type=volume,source={truth},target=/truth', '--mount', f'type=volume,source={public},target=/public-v2',
             RUNTIME, 'python', '-c', code]); containers.append(seed)
        run(['docker', 'start', '--attach', seed]); assert run(['docker', 'inspect', '--format', '{{.State.ExitCode}}', seed]) == '0'
        network = prefix+'-private'
        run(['docker', 'network', 'create', '--internal', '--label', label, network]); networks.append(network)
        name = prefix+'-evaluator'
        run(['docker', 'run', '--detach', '--name', name, '--label', label, '--network', network, *limits, '--mount', f'type=volume,source={truth},target=/truth,readonly', evaluator]); containers.append(name)
        state = json.loads(run(['docker', 'inspect', name]))[0]
        assert state['Config']['User'] == '20000:20000'
        address = state['NetworkSettings']['Networks'][network]['IPAddress']
        run(['docker', 'exec', name, 'python', '/app/evaluator_canary.py', 'read'])
        run(['docker', 'exec', name, 'python', '-c', "import urllib.request;assert urllib.request.urlopen('http://127.0.0.1:8766').status==200;print('positive evaluator HTTP control')"])
        inventory = {}
        for role in ['service', 'learner']:
            name = prefix+'-'+role
            run(['docker', 'create', '--name', name, '--label', label, '--network', 'none', *limits, '--env', 'OBS2_EVALUATOR_IP='+address,
                 '--mount', f'type=volume,source={truth},target=/truth,readonly', '--mount', f'type=volume,source={public},target=/public-v2,readonly', images[role], 'python', '/app/observed_v2_probe.py']); containers.append(name)
            state = json.loads(run(['docker', 'inspect', name]))[0]
            assert state['Image'] == images[role] and state['Config']['User'] == ('10001:10001' if role == 'service' else '10002:10002')
            assert state['HostConfig']['NetworkMode'] == 'none' and state['HostConfig']['ReadonlyRootfs']
            assert all(item['Type'] == 'volume' and not item['RW'] for item in state['Mounts'])
            run(['docker', 'start', '--attach', name]); assert run(['docker', 'inspect', '--format', '{{.State.ExitCode}}', name]) == '0'
            inventory[role] = dict(image=images[role], user=state['Config']['User'], network='none', source_mount=False, mounts=state['Mounts'],
                                   exact_source_sha256=previous[role]['exact_source_sha256'], source_paths=previous[role]['source_paths'])
        (directory / 'inventory.json').write_bytes((json.dumps(dict(merge=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
                     reviewed=ready['head'], roles=inventory, evaluator_image=evaluator, unchanged_independent_wire=True, rebuilt=False), indent=2)+'\n').encode())
        print('PASS: exact independently qualified images match merged runtime/probe bytes; actualUID10001/10002 positive/P2/full85 and private isolation pass; positiveUID20000 controls; no rebuild or source mounts')
    finally:
        for name in reversed(containers): run(['docker', 'rm', '--force', name], check=False)
        for name in reversed(networks): run(['docker', 'network', 'rm', name], check=False)
        for name in reversed(volumes): run(['docker', 'volume', 'rm', name], check=False)


if __name__ == '__main__': main()
