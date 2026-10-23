"""Fail closed before Docker when the expected durable filesystem is absent."""
import hashlib
import json
from pathlib import Path
import stat
import subprocess
from prepare import validate, verify_rendered


def output(*command):
    return subprocess.check_output(command, text=True).strip()


def block_device(path):
    return stat.S_ISBLK(Path(path).stat().st_mode)


def check(config, mount=Path('/srv/remission')):
    validate(config)
    device, identity = config['disk_device'], config['disk_uuid']
    if not block_device(device):
        raise RuntimeError('expected_block_device_missing')
    if (output('blkid', '-s', 'UUID', '-o', 'value', device) != identity
            or output('blkid', '-s', 'TYPE', '-o', 'value', device) != 'ext4'):
        raise RuntimeError('expected_disk_identity_mismatch')
    # --mountpoint, rather than --target, rejects a directory on the boot disk.
    actual_uuid = output('findmnt', '--noheadings', '--output', 'UUID', '--mountpoint', str(mount))
    actual_source = output('findmnt', '--noheadings', '--output', 'SOURCE', '--mountpoint', str(mount))
    if actual_uuid != identity or Path(actual_source).resolve() != Path(device).resolve():
        raise RuntimeError('expected_disk_not_mounted')
    for name in ('data', 'bootstrap', 'exports', 'proxy-data', 'proxy-config'):
        path = mount / name
        if path.is_symlink() or not path.is_dir() or path.stat().st_dev != mount.stat().st_dev:
            raise RuntimeError('durable_directory_missing_or_redirected')
    for name in ('data/remission.sqlite', 'data/remission.sqlite.admission.lock',
                 'bootstrap/bundle.json', 'bootstrap/runtime.json', 'bootstrap/bootstrap.sha256'):
        path = mount / name
        if path.is_symlink() or not path.is_file() or path.stat().st_dev != mount.stat().st_dev:
            raise RuntimeError('durable_artifact_missing_or_redirected')
        if name != 'data/remission.sqlite.admission.lock' and not path.stat().st_size:
            raise RuntimeError('durable_artifact_empty')
    hashes = (mount / 'bootstrap/bootstrap.sha256').read_text(encoding='utf-8').splitlines()
    names = set()
    for line in hashes:
        digest, name = line.split('  ', 1)
        if name not in {'bundle.json', 'runtime.json', 'simulation.json'} or name in names:
            raise RuntimeError('unexpected_bootstrap_checksum_entry')
        names.add(name)
        path = mount / 'bootstrap' / name
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise RuntimeError('bootstrap_checksum_mismatch')
    if names != {'bundle.json', 'runtime.json', 'simulation.json'}:
        raise RuntimeError('incomplete_bootstrap_checksums')


if __name__ == '__main__':
    verify_rendered(Path('/opt/remission-simulation'))
    check(json.loads(Path('/opt/remission-simulation/deployment.json').read_bytes()))
