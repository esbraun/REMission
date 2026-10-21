"""Read-only final candidate source/raw/image binding check; no runtime imports."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent


def main():
    manifest = json.loads((OUT / 'raw-manifest.json').read_bytes())
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=ROOT)
    source = manifest['frozen_source_commit']
    assert not git('diff', source, 'HEAD', '--', *manifest['source_scope']), 'candidate changed tested source tree'
    assert not git('diff', 'HEAD', '--', *manifest['source_scope']), 'dirty source tree'
    tree = {}
    for line in git('ls-tree', '-r', 'HEAD', '--', *manifest['source_scope']).decode().splitlines():
        metadata, path = line.split('\t', 1)
        tree[path] = metadata.split()[2]
    assert tree == {p: item['git_blob'] for p, item in manifest['source_files'].items()}
    source_hash = hashlib.sha256(json.dumps(manifest['source_files'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    assert source_hash == manifest['source_map_sha256']
    attributes = (ROOT / '.gitattributes').read_bytes().replace(b'\r\n', b'\n')
    assert hashlib.sha256(attributes).hexdigest() == manifest['final_attributes_sha256']
    for path, item in manifest['raw_artifacts'].items():
        raw = (ROOT / path).read_bytes()
        assert len(raw) == item['bytes'] and hashlib.sha256(raw).hexdigest() == item['sha256'], path
    for role in manifest['curated_roles'].values():
        assert role['network'] == 'none' and not role['source_mount']
        for path, digest in role['exact_source_sha256'].items():
            relative = path.removeprefix('/app/')
            assert digest == manifest['source_files'][relative]['own_checkout_sha256'], relative
    print('PASS: exact tested source tree, declared evidence attributes, all raw bytes and curated own-source image bindings; no self-referential manifest hash')


if __name__ == '__main__':
    main()
