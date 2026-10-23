"""Render a nonsecret single-VM deployment; never contact Docker or Google Cloud."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex

ROOT = '/opt/remission-simulation'
MOUNT = '/srv/remission'
KEYS = {'service_image', 'generator_image', 'proxy_image', 'source_commit',
        'hostname', 'disk_device', 'disk_uuid'}


def validate(config):
    if set(config) != KEYS or not all(isinstance(v, str) for v in config.values()):
        raise ValueError('exact nonsecret configuration keys required')
    for name in ('service_image', 'generator_image', 'proxy_image'):
        if not re.fullmatch(r'[a-z0-9][a-z0-9./:_-]*@sha256:[a-f0-9]{64}', config[name]):
            raise ValueError(name + ' requires a registry image with immutable digest')
    if not re.fullmatch(r'[a-f0-9]{40}', config['source_commit']):
        raise ValueError('source_commit requires full Git SHA')
    host = config['hostname']
    if (len(host) > 253 or '.' not in host or not re.fullmatch(
            r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?', host)
            or any(not label or len(label) > 63 or label.startswith('-') or label.endswith('-')
                   for label in host.split('.')) or re.fullmatch(r'[0-9.]+', host)
            or host.endswith(('.localhost', '.invalid', '.test', '.example'))):
        raise ValueError('hostname requires the selected public DNS name for trusted HTTPS')
    if not re.fullmatch(r'/dev/disk/by-id/google-[a-z][a-z0-9-]{0,62}', config['disk_device']):
        raise ValueError('disk_device requires exact GCE attached device identity')
    if not re.fullmatch(r'[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}', config['disk_uuid']):
        raise ValueError('disk_uuid requires the operator-observed ext4 filesystem UUID')
    return config


def bind(source, target, readonly=False):
    # Do not let Compose create an empty directory when a required source is missing.
    return {'type': 'bind', 'source': source, 'target': target, 'read_only': readonly,
            'bind': {'create_host_path': False}}


def compose(config):
    validate(config)
    hardened = {'read_only': True, 'cap_drop': ['ALL'],
                'security_opt': ['no-new-privileges:true'],
                'tmpfs': ['/tmp:rw,noexec,nosuid,size=128m'],
                # Never bypass the mount guard after a Docker daemon/VM restart.
                'restart': 'on-failure:5', 'pids_limit': 256,
                'logging': {'driver': 'json-file', 'options': {'max-size': '10m', 'max-file': '3'}}}
    app = {**hardened, 'image': config['service_image'], 'user': '10001:10001',
           'networks': ['private'], 'mem_limit': '2g', 'cpus': 2,
           'environment': {'REMISSION_DATABASE': '/data/remission.sqlite',
               'REMISSION_CONTROL_BUNDLE': '/fixtures/bundle.json',
               'REMISSION_RUNTIME_REF': '/fixtures/runtime.json',
               'REMISSION_LIVE_EXPORT_ROOT': '/exports',
               'REMISSION_SOURCE_COMMIT': config['source_commit'],
               'REMISSION_ORIGIN': 'https://' + config['hostname'],
               'REMISSION_GENERATOR_URL': 'http://generator:8780'},
           'volumes': [bind(MOUNT + '/data', '/data'), bind(MOUNT + '/bootstrap', '/fixtures', True),
                       bind(MOUNT + '/exports', '/exports')],
           'depends_on': {'generator': {'condition': 'service_started'}},
           'healthcheck': {'test': ['CMD', 'python', '-c',
               "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/health',timeout=3).read()"],
               'interval': '10s', 'timeout': '5s', 'retries': 6, 'start_period': '20s'}}
    generator = {**hardened, 'image': config['generator_image'], 'user': '20000:20000',
                 'networks': ['private'], 'mem_limit': '2g', 'cpus': 2}
    proxy = {**hardened, 'image': config['proxy_image'], 'networks': ['private', 'edge'],
             'ports': ['80:80', '443:443'], 'mem_limit': '256m', 'cpus': 1,
             'volumes': [bind(ROOT + '/Caddyfile', '/etc/caddy/Caddyfile', True),
                         bind(MOUNT + '/proxy-data', '/data'), bind(MOUNT + '/proxy-config', '/config')],
             'depends_on': {'app': {'condition': 'service_healthy'}}}
    # Fixed project/service names and scale=1 are part of the one-writer contract.
    return {'name': 'remission-simulation', 'services': {'generator': generator, 'app': app, 'proxy': proxy},
            'networks': {'private': {'internal': True}, 'edge': {}}}


def render(config, destination):
    validate(config)
    destination.mkdir(parents=True, exist_ok=False)
    text = json.dumps(config, sort_keys=True, indent=2) + '\n'
    (destination / 'deployment.json').write_text(text, encoding='utf-8', newline='\n')
    (destination / 'compose.json').write_text(json.dumps(compose(config), indent=2) + '\n', encoding='utf-8', newline='\n')
    (destination / 'Caddyfile').write_text(config['hostname'] + ' {\n    reverse_proxy app:8765\n}\n', encoding='utf-8', newline='\n')
    variables = '\n'.join(k + '=' + shlex.quote(config[v]) for k, v in
                          [('DISK_DEVICE', 'disk_device'), ('DISK_UUID', 'disk_uuid')]) + '\n'
    (destination / 'disk.env').write_text(variables, encoding='utf-8', newline='\n')
    (destination / 'srv-remission.mount').write_text(
        '[Unit]\nDescription=Retained REMission simulation disk\n\n[Mount]\nWhat='
        + config['disk_device'] + '\nWhere=' + MOUNT
        + '\nType=ext4\nOptions=nodev,nosuid\nTimeoutSec=30\n', encoding='utf-8', newline='\n')
    for name in ('disk_guard.py', 'prepare.py', 'startup.sh', 'remission-simulation.service', 'admin.py'):
        (destination / name).write_text(Path(__file__).with_name(name).read_text(encoding='utf-8'), encoding='utf-8', newline='\n')
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir() if p.is_file()}
    (destination / 'manifest.json').write_text(json.dumps(hashes, sort_keys=True, indent=2) + '\n', encoding='utf-8', newline='\n')
    return hashes


def verify_rendered(directory):
    hashes = json.loads((directory / 'manifest.json').read_bytes())
    expected = {'deployment.json', 'compose.json', 'Caddyfile', 'disk.env', 'srv-remission.mount',
                'disk_guard.py', 'prepare.py', 'startup.sh', 'remission-simulation.service', 'admin.py'}
    if set(hashes) != expected:
        raise ValueError('deployment_manifest_file_set_mismatch')
    for name, digest in hashes.items():
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != digest:
            raise ValueError('deployment_manifest_hash_mismatch')
    config = validate(json.loads((directory / 'deployment.json').read_bytes()))
    if json.loads((directory / 'compose.json').read_bytes()) != compose(config):
        raise ValueError('deployment_compose_mismatch')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--verify', type=Path)
    args = parser.parse_args()
    if args.verify:
        verify_rendered(args.verify)
        print(json.dumps({'status': 'manifest_verified'}))
        return
    if args.config is None or args.output is None:
        parser.error('--config and --output required when rendering')
    hashes = render(json.loads(args.config.read_bytes()), args.output)
    print(json.dumps({'status': 'rendered_only', 'files': hashes}, sort_keys=True))


if __name__ == '__main__':
    main()
