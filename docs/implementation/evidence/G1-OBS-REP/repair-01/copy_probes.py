"""Copy only root-supplied immutable reviewer blobs without newline conversion."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent / 'reviewer'
BLOBS = {
    'full-horizon-addendum.md': '6aee8f28012337f1728f5098e5ae4e71b02b32a8',
    'full-horizon-manifest.json': '7c8db98ea52dbe89f83a026d40bea4bd7e938df8',
    'full-horizon-probe.py': '2580ce12ae1c4ee6efad58e137129b2c6ad14847',
    'full-horizon.command.json': 'cc310206fb8a73ea1e7f6a4b8c05259679e4d352',
    'full-horizon.stdout.log': 'ec56c3003432f321e574cad121f46c5cd2fe1bf2',
    'full-horizon.stderr.log': 'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391',
    'changes-requested.md': '405a91e4d3a2a532623d88a2039e848e58e0da95',
    'surviving-evidence-manifest.json': 'cd3f0be230e1c33f80a85971e54274e9decdf450',
    'hold-identity.py': '5b8bef5d0ed5fe749316e5bd5ed8c625d385dc5a',
    'hold-identity.stdout.log': '2039080d735ed187ac94b4d1703bb70d1834e1ec',
    'hold-identity.command.json': '01192dfda3079b87575e953da830ca577c37d883',
    'day85.py': 'ae8f19352ad6ad1fb8411a44a927f245d0217f6e',
    'day85.stdout.log': '353229f42e0a95d1efdf53e9ebb803537b49b89d',
    'day85.command.json': 'bfa88d3e8d229300cd4c039a47eb3138c9c8a9ed',
    'hold-identity.stderr.log': 'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391',
    'day85.stderr.log': 'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391',
}


def main():
    OUT.mkdir(exist_ok=True)
    metadata = []
    for name, blob in BLOBS.items():
        raw = subprocess.check_output(['git', 'cat-file', 'blob', blob], cwd=ROOT)
        target = OUT / name
        if target.exists():
            assert target.read_bytes() == raw
        else:
            target.write_bytes(raw)
        metadata.append(dict(path=target.relative_to(ROOT).as_posix(), git_blob=blob, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
    (OUT.parent / 'reviewer-manifest.json').write_text(json.dumps(dict(candidate='ceb5a5fc786f487045fd948986bc4bb8b8a43bf4', artifacts=metadata), indent=2) + '\n', encoding='utf-8', newline='\n')
    # Publish only surviving originals; the report discloses four overwritten
    # reviewer streams. Their missing bytes are never reconstructed.
    for manifest, folder, count in [('surviving-evidence-manifest.json', 'reviewer-surviving', 192), ('full-horizon-manifest.json', 'reviewer-surviving/full-horizon-addendum', 880)]:
        surviving = json.loads((OUT / manifest).read_bytes())['files']
        assert len(surviving) == count
        destination = OUT.parent / folder
        for name, item in surviving.items():
            path = PurePosixPath(name)
            assert not path.is_absolute() and '..' not in path.parts and '\\' not in name
            target = destination.joinpath(*path.parts)
            assert target.resolve().is_relative_to(destination.resolve())
            if target.exists():
                raw = target.read_bytes()
            else:
                raw = subprocess.check_output(['git', 'cat-file', 'blob', item['git_blob']], cwd=ROOT)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
            assert len(raw) == item['bytes'] and hashlib.sha256(raw).hexdigest() == item['sha256']


if __name__ == '__main__':
    main()
