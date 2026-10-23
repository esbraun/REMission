"""One explicitly authorized CS-T1 attempt; host stdlib only, retain all resources.

--freeze prepares a reviewable plan without Docker. --execute requires root's
authorization of its exact SHA256. Reuses accepted literal-CID lifecycle code.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import time
import zlib

# The operator is launched with -P; admit only its frozen sibling directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import analysis_lifecycle as life

ROOT = Path(__file__).resolve().parents[2]
IMAGES = {
    'fixture': 'sha256:a950cdb0dd9b3bbdeb176c6da71903180406a9bf2160ea3d23faf4be3c0f5e72',
    'generator': 'sha256:d64907d76a2810d2e6cad8acaa012f3df132ced69bfe2636c7eb07f7090b4eee',
}
PARENT = 'sha256:ce346feace2ae607ebd574e1bb681d594c9b676c06b56f8ba8d50b858a577faa'
BUDGETS = dict(fixture_seconds=180, generator_seconds=240, parent_seconds=300,
               external_seconds=400, cleanup_seconds=60)
PRIVATE_NETWORK = dict(subnet='10.253.240.0/28', gateway='10.253.240.1')
IMAGE_FORMAT = '{"Id":{{json .Id}},"Os":{{json .Os}},"Architecture":{{json .Architecture}},"User":{{json .Config.User}}}'
# A base image may omit Config.User entirely (the default root user). Parent
# admission requires identity/platform only; role images still require exact UID.
PARENT_IMAGE_FORMAT = '{"Id":{{json .Id}},"Os":{{json .Os}},"Architecture":{{json .Architecture}}}'
# Selection happens in Docker, before stdout; never emit complete Config/Env.
CONTAINER_FORMAT = '{"Id":{{json .Id}},"Image":{{json .Image}},"User":{{json .Config.User}},"Labels":{{json .Config.Labels}},"Path":{{json .Path}},"Args":{{json .Args}},"RestartCount":{{json .RestartCount}},"State":{{json .State}},"Memory":{{json .HostConfig.Memory}},"MemorySwap":{{json .HostConfig.MemorySwap}},"NanoCpus":{{json .HostConfig.NanoCpus}},"PidsLimit":{{json .HostConfig.PidsLimit}},"ReadonlyRootfs":{{json .HostConfig.ReadonlyRootfs}},"Privileged":{{json .HostConfig.Privileged}},"CapAdd":{{json .HostConfig.CapAdd}},"CapDrop":{{json .HostConfig.CapDrop}},"AutoRemove":{{json .HostConfig.AutoRemove}},"PublishAllPorts":{{json .HostConfig.PublishAllPorts}},"SecurityOpt":{{json .HostConfig.SecurityOpt}},"Tmpfs":{{json .HostConfig.Tmpfs}},"NetworkMode":{{json .HostConfig.NetworkMode}},"PortBindings":{{json .HostConfig.PortBindings}},"RestartPolicy":{{json .HostConfig.RestartPolicy}},"Mounts":{{json .Mounts}},"Networks":{{json .NetworkSettings.Networks}}}'
NETWORK_FORMAT = '{"Id":{{json .Id}},"Name":{{json .Name}},"Driver":{{json .Driver}},"Internal":{{json .Internal}},"Labels":{{json .Labels}},"IPAM":[{{range $i,$c := .IPAM.Config}}{{if $i}},{{end}}{"Subnet":{{json (index $c "Subnet")}},"Gateway":{{json (index $c "Gateway")}}}{{end}}]}'
ATTACHMENT_FORMAT = '{"Id":{{json .Id}},"Networks":{{json .NetworkSettings.Networks}}}'

# Runs inside each existing image before any work. No repo/source overlay can
# satisfy these hashes: every admitted application byte must come from /app.
QUALIFY = '''import base64,hashlib,importlib,json,os,platform,runpy,sys,zlib
from pathlib import Path
role,packed=sys.argv[1:]
closure=json.loads(zlib.decompress(base64.b64decode(packed)))
expected=closure['files']
uid=10001 if role=='fixture' else 20000
assert sys.platform=='linux' and platform.machine()=='x86_64'
assert os.getuid()==uid and os.getgid()==uid
root=Path('/app')
actual={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
generated={p:sha for p,sha in actual.items() if p.startswith('/app/web/dist/')}
source={p:sha for p,sha in actual.items() if p not in generated}
assert source==expected,'image_application_bytes_mismatch'
assert all(not p.is_symlink() for p in root.rglob('*')),'unexpected_application_symlink'
if role=='fixture':
    assert '/app/web/dist/index.html' in generated and any(p.endswith('.js') for p in generated),'missing_built_frontend'
else:
    assert not generated,'frontend_in_generator'
for forbidden in ('services/learner','services/evaluator','evaluation','methods','analysis_dispatcher.py'):
    assert not (root/forbidden).exists(),'forbidden_source_present'
if role=='fixture':
    assert not (root/'services/generator').exists(),'generator_source_in_service'
    assert not (root/'contracts/dgp').exists(),'dgp_source_in_service'
    importlib.import_module('services.foundation.app')
else:
    assert not (root/'services/foundation').exists(),'service_source_in_generator'
    importlib.import_module('services.generator.server')
assert not any(m.split('.')[0] in ('numpy','scipy','pymc','pytensor','statsmodels') for m in sys.modules),'scientific_module_imported'
print(json.dumps(dict(qualification='passed',role=role,uid=uid,gid=uid,platform='linux/amd64',files=len(source),closure_sha256=hashlib.sha256(json.dumps(source,sort_keys=True,separators=(',',':')).encode()).hexdigest(),generated_dist_observed=generated,generated_dist_status='first observed inventory; no preknown independent asset hashes')),flush=True)
if role=='fixture':
    sys.argv=['/qualification/linux_simulation_fixture.py']
    runpy.run_path(sys.argv[0],run_name='__main__')
else:
    os.execv(sys.executable,[sys.executable,'-B','-m','services.generator.server'])
'''


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def physical_sources():
    paths = sorted((ROOT / 'tooling/foundation/cloud').iterdir())
    paths += [ROOT / 'tests/deployment/linux_simulation_fixture.py', Path(__file__),
              ROOT / 'tooling/foundation/analysis_lifecycle.py']
    return {str(p.resolve()): digest(p.read_bytes()) for p in paths if p.is_file()}


def workload(role, expected):
    packed = base64.b64encode(zlib.compress(canonical(expected), 9)).decode()
    return ['python', '-B', '-c', QUALIFY, role, packed]


def create_argv(plan, role):
    prefix = plan['prefix']; network = prefix + '-private'
    uid = '10001:10001' if role == 'fixture' else '20000:20000'
    argv = ['docker', 'create', '--name', prefix + '-' + role, '--label', 'remission.task=' + prefix,
            '--network', network, '--user', uid, '--cpus', '2', '--memory', '2g', '--memory-swap', '2g',
            '--pids-limit', '256', '--read-only', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
            '--tmpfs', '/tmp:rw,noexec,nosuid,size=256m', '--env', 'PYTHONDONTWRITEBYTECODE=1',
            '--env', 'PYTHONPATH=/deployment:/app' if role == 'fixture' else 'PYTHONPATH=/app']
    if role == 'generator':
        argv += ['--network-alias', 'generator']
    else:
        argv += ['--mount', 'type=bind,source=' + plan['cloud_source'] + ',target=/deployment,readonly',
                 '--mount', 'type=bind,source=' + plan['fixture_source'] + ',target=/qualification/linux_simulation_fixture.py,readonly',
                 '--env', 'REMISSION_GENERATOR_URL=http://generator:8780',
                 '--env', 'QUALIFICATION_SOURCE_COMMIT=' + plan['source_commit'],
                 '--env', 'QUALIFICATION_SERVICE_IMAGE=' + IMAGES['fixture'],
                 '--env', 'QUALIFICATION_GENERATOR_IMAGE=' + IMAGES['generator']]
    return argv + [IMAGES[role]] + workload(role, plan['closures'][role])


def network_create_argv(plan):
    return ['docker', 'network', 'create', '--internal',
            '--subnet', plan['private_network']['subnet'], '--gateway', plan['private_network']['gateway'],
            '--label', 'remission.task=' + plan['prefix'], plan['prefix'] + '-private']


def validate_closures(closures):
    if set(closures) != set(IMAGES):
        raise ValueError('exact fixture and generator closures required')
    for role, value in closures.items():
        if set(value) != {'image', 'source_commit', 'build_manifest_sha256', 'files'} or value['image'] != IMAGES[role]:
            raise ValueError('wrong closure identity/schema')
        if re.fullmatch('[0-9a-f]{40}', value['source_commit']) is None or re.fullmatch('[0-9a-f]{64}', value['build_manifest_sha256']) is None:
            raise ValueError('unbound build provenance')
        if not value['files']:
            raise ValueError('empty image closure')
        for path, sha in value['files'].items():
            if not path.startswith('/app/') or '..' in path.split('/') or re.fullmatch('[0-9a-f]{64}', sha) is None:
                raise ValueError('invalid image source closure')


def freeze(closures_path, output, prefix):
    if re.fullmatch('remission-cloud-fixture-[a-f0-9]{12}', prefix) is None:
        raise ValueError('unique literal fixture prefix required')
    closures = json.loads(closures_path.read_bytes()); validate_closures(closures)
    head = life.command(['git', '-C', str(ROOT), 'rev-parse', 'HEAD']).stdout.decode().strip()
    if life.command(['git', '-C', str(ROOT), 'status', '--porcelain']).stdout:
        raise ValueError('commit candidate before freezing execution')
    plan = dict(version=1, prefix=prefix, source_commit=head, root=str(ROOT.resolve()),
                cloud_source=str((ROOT / 'tooling/foundation/cloud').resolve()),
                fixture_source=str((ROOT / 'tests/deployment/linux_simulation_fixture.py').resolve()),
                physical_sources=physical_sources(), closures=closures, parent_image=PARENT,
                budgets=BUDGETS, private_network=PRIVATE_NETWORK, attempts=1)
    plan['create_argv'] = {role: create_argv(plan, role) for role in IMAGES}
    plan['network_create_argv'] = network_create_argv(plan)
    output.mkdir(parents=True, exist_ok=False)
    life.save(output / 'plan.json', plan)
    print(json.dumps(dict(plan=str(output / 'plan.json'), sha256=digest((output / 'plan.json').read_bytes()))))


def authorize(plan_path, auth_path):
    raw = plan_path.read_bytes(); plan = json.loads(raw); auth = json.loads(auth_path.read_bytes())
    if auth != dict(authorized=True, scope='one-local-CS-T1-fixture', plan_sha256=digest(raw), attempts=1,
                    retain_resources=True, cloud=False, training=False):
        raise ValueError('root authorization does not match the exact one-attempt plan')
    if plan['root'] != str(ROOT.resolve()) or plan['physical_sources'] != physical_sources():
        raise ValueError('frozen physical candidate changed')
    if (plan['cloud_source'] != str((ROOT / 'tooling/foundation/cloud').resolve())
            or plan['fixture_source'] != str((ROOT / 'tests/deployment/linux_simulation_fixture.py').resolve())):
        raise ValueError('mount source outside frozen candidate')
    if life.command(['git', '-C', str(ROOT), 'rev-parse', 'HEAD']).stdout.decode().strip() != plan['source_commit']:
        raise ValueError('candidate commit changed')
    validate_closures(plan['closures'])
    if (plan['budgets'] != BUDGETS or plan.get('private_network') != PRIVATE_NETWORK
            or plan['attempts'] != 1 or plan['parent_image'] != PARENT
            or re.fullmatch('remission-cloud-fixture-[a-f0-9]{12}', plan['prefix']) is None):
        raise ValueError('execution bounds/identity changed')
    if (plan['create_argv'] != {role: create_argv(plan, role) for role in IMAGES}
            or plan.get('network_create_argv') != network_create_argv(plan)):
        raise ValueError('frozen argv changed')
    return plan


def mount_source(path):
    value = path.replace('\\', '/')
    for prefix in ('/run/desktop/mnt/host/', '/host_mnt/'):
        if value.startswith(prefix) and re.match('[a-zA-Z]/', value[len(prefix):]):
            value = value[len(prefix)] + ':' + value[len(prefix) + 1:]
    return value.lower() if re.match('[a-zA-Z]:/', value) else value


def audit_network(value, network_id, plan):
    expected = dict(Id=network_id, Name=plan['prefix'] + '-private', Driver='bridge',
                    Internal=True, Labels={'remission.task': plan['prefix']},
                    IPAM=[dict(Subnet=plan['private_network']['subnet'],
                               Gateway=plan['private_network']['gateway'])])
    if value != expected or type(value.get('Internal')) is not bool:
        raise ValueError('network identity/IPAM mismatch')


def audit_container(value, cid, plan, role, network_id):
    life.checked_state(value, cid)
    if value['State']['Status'] != 'created':
        raise ValueError('prestart audit requires created container')
    expected = dict(Image=IMAGES[role], User='10001:10001' if role == 'fixture' else '20000:20000',
                    Labels={'remission.task': plan['prefix']}, Memory=2147483648, MemorySwap=2147483648,
                    NanoCpus=2000000000, PidsLimit=256, ReadonlyRootfs=True, CapDrop=['ALL'],
                    Privileged=False, CapAdd=None, AutoRemove=False, PublishAllPorts=False,
                    SecurityOpt=['no-new-privileges'], Tmpfs={'/tmp': 'rw,noexec,nosuid,size=256m'},
                    NetworkMode=plan['prefix'] + '-private', RestartPolicy={'Name': 'no', 'MaximumRetryCount': 0})
    for key, item in expected.items():
        if value.get(key) != item or type(value.get(key)) is not type(item):
            raise ValueError('prestart resource mismatch: ' + role + ':' + key)
    argv = workload(role, plan['closures'][role])
    if value.get('Path') != argv[0] or value.get('Args') != argv[1:] or value.get('PortBindings') not in ({}, None):
        raise ValueError('prestart command/port mismatch')
    mounts = {(mount_source(m['Source']), m['Destination'], m['Type'], m['RW']) for m in value['Mounts'] if m['Type'] != 'tmpfs'}
    for mount in value['Mounts']:
        if mount['Type'] == 'tmpfs' and (mount['Destination'] != '/tmp' or mount['RW'] is not True):
            raise ValueError('unexpected tmpfs mount')
    expected_mounts = set() if role == 'generator' else {
        (mount_source(plan['cloud_source']), '/deployment', 'bind', False),
        (mount_source(plan['fixture_source']), '/qualification/linux_simulation_fixture.py', 'bind', False)}
    # Docker reports tmpfs in HostConfig.Tmpfs, independently from bind Mounts.
    if mounts != expected_mounts:
        raise ValueError('prestart mounts mismatch')
    networks = value['Networks']
    # Moby initializes endpoint configuration at create; it allocates the actual
    # endpoint on start. Bind the configured name to the separately audited ID;
    # reject foreign populated IDs, then audit allocated IDs after execution.
    if set(networks) != {plan['prefix'] + '-private'} or next(iter(networks.values()))['NetworkID'] not in ('', network_id):
        raise ValueError('prestart network mismatch')
    if role == 'generator' and 'generator' not in next(iter(networks.values())).get('Aliases', []):
        raise ValueError('missing private generator alias')


class Generator:
    """The one fixture-owned service, with intentional stop distinguished from exit."""
    def __init__(self, cid, folder, deadline):
        self.cid = cid; self.folder = folder; self.deadline = deadline
        self.nonce = secrets.token_hex(24); self.watch = None; self.attach = None
        self.streams = []; self.intentional = False

    def start(self):
        self.folder.mkdir(exist_ok=False)
        for name in ('watchdog.stdout', 'watchdog.stderr', 'attach.stdout', 'attach.stderr'):
            self.streams.append((self.folder / name).open('wb'))
        self.watch = subprocess.Popen([sys.executable, '-P', '-B', str(Path(life.__file__).resolve()),
            '--watchdog-cid', self.cid, '--folder', str(self.folder), '--deadline', str(self.deadline), '--nonce', self.nonce],
            stdout=self.streams[0], stderr=self.streams[1],
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        arm_deadline = min(self.deadline, time.monotonic() + 5)
        while True:
            life.check_deadline(arm_deadline)
            if self.watch.poll() is not None:
                raise RuntimeError('generator watchdog exited before start')
            ready = self.folder / 'watchdog-ready.json'
            if ready.exists():
                if json.loads(ready.read_bytes()) != dict(cid=self.cid, nonce=self.nonce, deadline=self.deadline, pid=self.watch.pid):
                    raise ValueError('foreign generator arm receipt')
                break
            time.sleep(.05)
        self.check()
        self.attach = subprocess.Popen(['docker', 'start', '--attach', self.cid],
            stdout=self.streams[2], stderr=self.streams[3],
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

    def check(self):
        life.check_deadline(self.deadline)
        if self.watch.poll() is not None or (self.attach is not None and self.attach.poll() is not None):
            raise RuntimeError('generator completed before intentional stop')

    def finish(self):
        self.check()
        before = life.inspect(self.cid, deadline=self.deadline)
        if not before['State']['Running']:
            raise RuntimeError('generator stopped before fixture completed')
        self.intentional = True
        life.save(self.folder / 'intentional-stop.json', dict(cid=self.cid, reason='fixture completed', before=before))
        cleanup = life.stop_owned(self.cid)
        # Both completion orders converge on the same typed terminal receipt.
        for child in (self.watch, self.attach):
            child.wait(timeout=min(3, max(.001, self.deadline - time.monotonic())))
        terminal = life.inspect(self.cid, deadline=self.deadline)
        life.receipt(self.folder / 'watchdog-terminal.json', self.cid, self.nonce, self.deadline, terminal)
        state = terminal['State']
        if self.watch.returncode != 0 or self.attach.returncode not in (0, state['ExitCode']) or state['Status'] != 'exited' or state['OOMKilled'] or state['Dead']:
            raise RuntimeError('generator intentional-stop receipt failed')
        life.save(self.folder / 'supervision.json', dict(cid=self.cid, intentional_stop=True,
                  terminal=terminal, cleanup=cleanup, returncodes=dict(watchdog=self.watch.returncode, attach=self.attach.returncode)))

    def reap(self):
        try:
            return {name: life.reap(child) for name, child in (('watchdog', self.watch), ('attach', self.attach))}
        finally:
            for stream in self.streams:
                stream.close()


def execute(plan_path, auth_path):
    plan = authorize(plan_path, auth_path)
    folder = plan_path.parent / 'attempt'
    folder.mkdir(exist_ok=False)  # An attempt is never retried or overwritten.
    start = time.monotonic(); parent_deadline = start + 300
    owned = {}; service = None; failure = None; unconfirmed = False; events = []
    sequence = 0

    def command(argv, cap=15):
        nonlocal sequence
        sequence += 1
        try:
            result = life.command(argv, check=False, deadline=parent_deadline, cap=cap)
            life.save(folder / ('command-%03d.json' % sequence), dict(argv=argv, returncode=result.returncode,
                      stdout=result.stdout.decode(errors='replace'), stderr=result.stderr.decode(errors='replace')))
        except BaseException as error:
            life.save(folder / ('command-%03d.json' % sequence), dict(argv=argv, failure=repr(error)))
            raise
        if result.returncode:
            raise RuntimeError('captured command failed: command-%03d.json' % sequence)
        return result.stdout.decode().strip()
    try:
        life.save(folder / 'execution.json', dict(plan_sha256=digest(plan_path.read_bytes()),
                  authorization_sha256=digest(auth_path.read_bytes()), start_monotonic=start,
                  parent_deadline=parent_deadline, generator_deadline=start + 240,
                  fixture_limit_seconds=180, external_limit_seconds=400))
        parent = json.loads(command(['docker', 'image', 'inspect', '--format', PARENT_IMAGE_FORMAT, PARENT]))
        if parent['Id'] != PARENT or parent['Os'] != 'linux' or parent['Architecture'] != 'amd64':
            raise ValueError('foundation parent identity/platform mismatch')
        for role, image in IMAGES.items():
            value = json.loads(command(['docker', 'image', 'inspect', '--format', IMAGE_FORMAT, image]))
            if value != dict(Id=image, Os='linux', Architecture='amd64', User='10001:10001' if role == 'fixture' else '20000:20000'):
                raise ValueError('image identity/platform/user mismatch')
        network_id = life.require_cid(command(plan['network_create_argv']))
        network = json.loads(command(['docker', 'network', 'inspect', '--format', NETWORK_FORMAT, network_id]))
        audit_network(network, network_id, plan)
        for role in ('generator', 'fixture'):
            cid = life.require_cid(command(plan['create_argv'][role])); owned[role] = cid
            life.save(folder / (role + '-cid.json'), dict(cid=cid))
            value = json.loads(command(['docker', 'inspect', '--format', CONTAINER_FORMAT, cid], cap=3))
            audit_container(value, cid, plan, role, network_id)
        rebound = json.loads(command(['docker', 'network', 'inspect', '--format', NETWORK_FORMAT, plan['prefix'] + '-private']))
        audit_network(rebound, network_id, plan)
        if rebound != network:
            raise ValueError('configured network name no longer identifies owned network')
        service = Generator(owned['generator'], folder / 'generator', start + 240)
        if plan['physical_sources'] != physical_sources():
            raise ValueError('physical candidate changed before start')
        service.start()
        fixture_deadline = min(time.monotonic() + 180, start + 225)
        life.supervise(owned['fixture'], folder / 'fixture', fixture_deadline, on_poll=service.check)
        for cid in owned.values():
            attached = json.loads(command(['docker', 'inspect', '--format', ATTACHMENT_FORMAT, cid], cap=3))
            networks = attached['Networks']
            if (attached['Id'] != cid or set(networks) != {plan['prefix'] + '-private'}
                    or next(iter(networks.values()))['NetworkID'] != network_id):
                raise ValueError('allocated task network mismatch')
        service.finish()
    except BaseException as error:
        failure = repr(error)
    finally:
        # Existing lifecycle stop/kill/inspect commands each have short independent
        # caps. Two exact CIDs plus reaping fit the reserved 60-second cleanup.
        for role, cid in owned.items():
            try:
                try:
                    observed = life.inspect(cid)
                except Exception as error:
                    events.append(dict(role=role, observation_error=repr(error)))
                    observed = None
                if observed is None or not life.stopped(observed):
                    events.append(dict(role=role, stop=life.stop_owned(cid)))
                terminal = life.inspect(cid)
                if not life.stopped(terminal):
                    raise life.StopUnconfirmed('owned resource is still live')
                events.append(dict(role=role, terminal=terminal))
            except BaseException as error:
                unconfirmed = True; events.append(dict(role=role, stop_error=repr(error)))
        if service is not None:
            try:
                events.append(dict(generator_reaped=service.reap()))
            except BaseException as error:
                unconfirmed = True; events.append(dict(reap_error=repr(error)))
        if plan['physical_sources'] != physical_sources():
            failure = failure or 'physical candidate changed during execution'
        result = dict(status='STOP UNCONFIRMED' if unconfirmed else 'failed' if failure else 'passed',
                      failure=failure, owned=owned, events=events, resources_retained=True,
                      elapsed_seconds=time.monotonic() - start)
        life.save(folder / 'result.json', result)
    if unconfirmed:
        raise life.StopUnconfirmed('STOP UNCONFIRMED; preserve exact resources and evidence')
    if failure:
        raise RuntimeError(failure)
    print(json.dumps(result))


def launch(plan_path, auth_path):
    authorize(plan_path, auth_path)
    folder = plan_path.parent / 'hostwatch'; folder.mkdir(exist_ok=False)
    argv = [sys.executable, '-P', '-B', str(Path(__file__).resolve()), '--execute', str(plan_path),
            '--authorization', str(auth_path)]
    with (folder / 'operator.stdout').open('wb') as out, (folder / 'operator.stderr').open('wb') as err:
        child = subprocess.Popen(argv, stdout=out, stderr=err,
                                 creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        life.save(folder / 'launch.json', dict(argv=argv, pid=child.pid, seconds=400))
        timed_out = False
        try:
            code = child.wait(timeout=400)
        except subprocess.TimeoutExpired:
            timed_out = True; child.kill(); code = child.wait(timeout=2)
        life.save(folder / 'terminal.json', dict(pid=child.pid, exit=code, process_reaped=True,
                  timeout=timed_out, status='STOP UNCONFIRMED' if timed_out else 'parent reaped'))
    if timed_out:
        raise life.StopUnconfirmed('STOP UNCONFIRMED; external timeout; retain watchdog and container evidence')
    if code:
        raise RuntimeError('fixture operator failed; retained evidence')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--freeze', type=Path, metavar='CLOSURES_JSON')
    mode.add_argument('--execute', type=Path, metavar='PLAN_JSON')
    mode.add_argument('--launch', type=Path, metavar='PLAN_JSON')
    parser.add_argument('--output', type=Path); parser.add_argument('--prefix')
    parser.add_argument('--authorization', type=Path)
    args = parser.parse_args()
    if args.freeze:
        if args.output is None or args.prefix is None:
            parser.error('--freeze requires --output and --prefix')
        freeze(args.freeze, args.output, args.prefix)
    else:
        if args.authorization is None:
            parser.error('--execute requires --authorization')
        (launch if args.launch else execute)(args.launch or args.execute, args.authorization)
