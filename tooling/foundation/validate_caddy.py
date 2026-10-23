"""One frozen offline Caddy check; stdlib adapter to analysis_lifecycle, no pull."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analysis_lifecycle as life

ROOT = Path(__file__).resolve().parents[2]
INPUTS = ROOT / 'docs/implementation/evidence/caddy-validation-prep-20261023'
IMAGE = 'docker.io/library/caddy@sha256:04913b1da43339a40ad1ea87827d70a576ac5aa6cf674c6e24fdca675887533a'
IMAGE_FORMAT = '{"Id":{{json .Id}},"Os":{{json .Os}},"Architecture":{{json .Architecture}},"RepoDigests":{{json .RepoDigests}}}'
FIELDS = dict(Id='.Id', Image='.Image', User='.Config.User', Labels='.Config.Labels',
              Healthcheck='.Config.Healthcheck', Path='.Path', Args='.Args', RestartCount='.RestartCount', State='.State')
FIELDS.update({key: '.HostConfig.' + key for key in (
    'Memory', 'MemorySwap', 'NanoCpus', 'PidsLimit', 'ReadonlyRootfs', 'Privileged',
    'CapAdd', 'CapDrop', 'AutoRemove', 'PublishAllPorts', 'SecurityOpt', 'Tmpfs',
    'NetworkMode', 'PortBindings', 'RestartPolicy')})
FIELDS['Mounts'] = '.Mounts'
CONTAINER_FORMAT = '{' + ','.join('"' + key + '":{{json ' + path + '}}' for key, path in FIELDS.items()) + '}'
TMPFS = {path: 'rw,noexec,nosuid,size=16m' for path in ('/tmp', '/data', '/config')}
WORK = ('caddy version\n'
        'caddy validate --config /inputs/ipv4.Caddyfile --adapter caddyfile 1>&2\n'
        'echo REMISSION_IPV4_VALIDATED\n'
        'caddy validate --config /inputs/dns.Caddyfile --adapter caddyfile 1>&2\n'
        'echo REMISSION_DNS_VALIDATED\n')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def sources():
    paths = [Path(__file__), Path(life.__file__), ROOT / 'tooling/foundation/cloud/prepare.py']
    paths += sorted(INPUTS.iterdir())
    return {str(p.resolve()): sha(p.read_bytes()) for p in paths if p.is_file()}


def check_inputs():
    renderer = runpy.run_path(str(ROOT / 'tooling/foundation/cloud/prepare.py'))
    configs = json.loads((INPUTS / 'inputs.json').read_bytes())
    if set(configs) != {'ipv4', 'dns'}:
        raise ValueError('exact IPv4 and DNS renderer cases required')
    for case, host in (('ipv4', '8.8.8.8'), ('dns', 'simulation.example.org')):
        config = renderer['validate'](configs[case])
        if config['hostname'] != host or config['proxy_image'] != IMAGE:
            raise ValueError('offline input identity changed')
        if (INPUTS / (case + '.Caddyfile')).read_bytes() != renderer['caddyfile'](config).encode():
            raise ValueError('Caddyfile is not exact renderer output')


def create(name):
    argv = ['docker', 'create', '--pull', 'never', '--platform', 'linux/amd64',
            '--name', name, '--label', 'remission.task=' + name, '--network', 'none',
            '--user', '65532:65532', '--cpus', '0.5', '--memory', '128m',
            '--memory-swap', '128m', '--pids-limit', '64', '--read-only',
            '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--restart', 'no', '--no-healthcheck']
    for path, options in TMPFS.items():
        argv += ['--tmpfs', path + ':' + options]
    for case in ('ipv4', 'dns'):
        argv += ['--mount', 'type=bind,source=' + str((INPUTS / (case + '.Caddyfile')).resolve())
                 + ',target=/inputs/' + case + '.Caddyfile,readonly']
    return argv + ['--entrypoint', '/bin/sh', IMAGE, '-ec', WORK]


def plan(name, folder):
    check_inputs()
    if re.fullmatch('remission-caddy-[a-f0-9]{12}', name) is None:
        raise ValueError('unique task name required')
    commit = life.command(['git', '-C', str(ROOT), 'rev-parse', 'HEAD']).stdout.decode().strip()
    return dict(source_commit=commit, root=str(ROOT), name=name, evidence=str(folder.resolve()),
                physical_sources=sources(), image=IMAGE, create_argv=create(name),
                image_format=IMAGE_FORMAT, container_format=CONTAINER_FORMAT,
                workload_seconds=45, external_seconds=100, attempts=1,
                acquisition_proposal=dict(argv=['docker', 'pull', '--platform', 'linux/amd64', IMAGE],
                    timeout_seconds=120, external_seconds=140, attempts=1, authorized=False))


def authorized(path, authorization):
    raw = path.read_bytes(); value = json.loads(raw)
    expected = dict(authorized=True, scope='one-offline-caddy-validation', plan_sha256=sha(raw),
                    attempts=1, retain_resources=True, image_pull=False, network=False, cloud=False)
    if json.dumps(json.loads(authorization.read_bytes()), sort_keys=True) != json.dumps(expected, sort_keys=True):
        raise ValueError('root authorization must match this exact frozen plan')
    if value != plan(value['name'], path.parent):
        raise ValueError('frozen source, paths, commit or argv changed')
    return value


def image_identity(value):
    # Config.User is optional image metadata; the container has an explicit user.
    if (not isinstance(value, dict) or value.get('Os') != 'linux' or value.get('Architecture') != 'amd64'
            or re.fullmatch('sha256:[a-f0-9]{64}', value.get('Id', '')) is None
            or not isinstance(value.get('RepoDigests'), list)
            or not {IMAGE, IMAGE.removeprefix('docker.io/library/')} & set(value['RepoDigests'])):
        raise ValueError('selected official linux amd64 image association missing')
    return value['Id']


def mount_source(path):
    value = path.replace('\\', '/')
    for prefix in ('/run/desktop/mnt/host/', '/host_mnt/'):
        if value.startswith(prefix) and re.match('[a-zA-Z]/', value[len(prefix):]):
            value = value[len(prefix)] + ':' + value[len(prefix) + 1:]
    return value.lower() if re.match('[a-zA-Z]:/', value) else value


def audit(value, cid, image, name):
    life.checked_state(value, cid)
    expected = dict(Image=image, User='65532:65532',
        Healthcheck={'Test': ['NONE']}, Path='/bin/sh', Args=['-ec', WORK], Memory=134217728, MemorySwap=134217728,
        NanoCpus=500000000, PidsLimit=64, ReadonlyRootfs=True, Privileged=False,
        CapAdd=None, CapDrop=['ALL'], AutoRemove=False, PublishAllPorts=False,
        SecurityOpt=['no-new-privileges'], Tmpfs=TMPFS, NetworkMode='none',
        RestartPolicy={'Name': 'no', 'MaximumRetryCount': 0})
    if value['State']['Status'] != 'created':
        raise ValueError('prestart audit requires created state')
    if not isinstance(value.get('Labels'), dict) or value['Labels'].get('remission.task') != name:
        raise ValueError('task label missing; other labels may come from the pinned official image')
    for key, item in expected.items():
        if value.get(key) != item or type(value.get(key)) is not type(item):
            raise ValueError('prestart mismatch: ' + key)
    if value.get('PortBindings') not in (None, {}):
        raise ValueError('unexpected published port')
    mounts = value['Mounts']
    actual = {(mount_source(m['Source']), m['Destination'], m['Type'], m['RW'])
              for m in mounts if m['Type'] != 'tmpfs'}
    wanted = {(mount_source(str((INPUTS / (case + '.Caddyfile')).resolve())),
               '/inputs/' + case + '.Caddyfile', 'bind', False) for case in ('ipv4', 'dns')}
    if actual != wanted or len([m for m in mounts if m['Type'] != 'tmpfs']) != 2:
        raise ValueError('unexpected bind/anonymous/named volume')
    if any(m['Destination'] not in TMPFS or m['RW'] is not True for m in mounts if m['Type'] == 'tmpfs'):
        raise ValueError('unexpected tmpfs')


def worker(path, authorization):
    frozen = authorized(path, authorization)
    folder = path.parent / 'attempt'; folder.mkdir(exist_ok=False)
    deadline = time.monotonic() + 45; cid = None; failure = None; terminal = None; creating = False
    try:
        selected = json.loads(life.command(['docker', 'image', 'inspect', '--format', IMAGE_FORMAT, IMAGE],
                                         deadline=deadline, cap=5).stdout)
        image = image_identity(selected); life.save(folder / 'image.json', selected)
        creating = True
        result = life.command(frozen['create_argv'], deadline=deadline, cap=10)
        cid = life.require_cid(result.stdout.decode().strip())
        life.save(folder / 'created.json', dict(cid=cid, argv=frozen['create_argv']))
        observed = json.loads(life.command(['docker', 'inspect', '--format', CONTAINER_FORMAT, cid],
                                          deadline=deadline, cap=3).stdout)
        life.save(folder / 'prestart.json', observed); audit(observed, cid, image, frozen['name'])
        terminal = life.supervise(cid, folder / 'lifecycle', deadline)
        lines = (folder / 'lifecycle/attach.stdout').read_text(encoding='utf-8').splitlines()
        if (len(lines) != 3 or not re.fullmatch(r'v2\.11\.7(?: .*)?', lines[0])
                or lines[1:] != ['REMISSION_IPV4_VALIDATED', 'REMISSION_DNS_VALIDATED']):
            raise ValueError('released version or both configuration validations unconfirmed')
        authorized(path, authorization)
    except BaseException as error:
        failure = repr(error)
        if creating and cid is None: failure += '; STOP UNCONFIRMED: create returned no auditable literal CID'
    finally:
        if cid is not None:
            try:
                if failure is not None: life.stop_owned(cid)
                observed = life.inspect(cid)
                if not life.stopped(observed): raise life.StopUnconfirmed('owned container remains live')
                if failure is None and observed != terminal:
                    raise ValueError('final state differs from independently verified terminal receipt')
                terminal = observed
            except BaseException as error:
                terminal = None; failure = (failure or '') + '; STOP UNCONFIRMED ' + repr(error)
        life.save(folder / 'result.json', dict(cid=cid, terminal=terminal, failure=failure))
    if failure is not None: raise RuntimeError(failure)


def launch(path, authorization):
    authorized(path, authorization)
    folder = path.parent / 'launch'; folder.mkdir(exist_ok=False)
    argv = [sys.executable, '-P', '-B', str(Path(__file__).resolve()), '--worker', str(path),
            '--authorization', str(authorization)]
    child = None; failure = None; code = None
    try:
        with (folder / 'stdout').open('wb') as out, (folder / 'stderr').open('wb') as err:
            child = subprocess.Popen(argv, stdout=out, stderr=err,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            life.save(folder / 'child.json', dict(pid=child.pid, argv=argv))
            code = child.wait(timeout=100)
    except BaseException as error:
        failure = 'STOP UNCONFIRMED ' + repr(error)
    finally:
        code = life.reap(child)
        life.save(folder / 'terminal.json', dict(pid=child.pid if child else None,
                  returncode=code, failure=failure, reaped=child is not None and child.returncode is not None))
    if failure is not None or code != 0:
        raise RuntimeError(failure or 'Caddy validation worker failed; retain evidence')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--freeze', type=Path); mode.add_argument('--launch', type=Path)
    mode.add_argument('--worker', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--name'); parser.add_argument('--authorization', type=Path)
    args = parser.parse_args()
    if args.freeze:
        frozen = plan(args.name, args.freeze); args.freeze.mkdir(parents=True, exist_ok=False)
        life.save(args.freeze / 'plan.json', frozen)
        print(sha((args.freeze / 'plan.json').read_bytes()))
    elif args.authorization is None:
        parser.error('--authorization required')
    elif args.launch: launch(args.launch.resolve(), args.authorization.resolve())
    else: worker(args.worker.resolve(), args.authorization.resolve())


if __name__ == '__main__': main()
