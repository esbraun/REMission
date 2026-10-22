"""Freeze only authorized original inputs plus an immutable Git archive."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OLD = Path('C:/Users/erics/Documents/Projects/REMission-worktrees/poc-n-source-review-astra-261022')
SOURCE = 'e6d5f4ae94793e25e76f3ecf5368420849066916'
ARCHIVE = HERE / 'source-e6d5.tar'
subprocess.run(['git', 'archive', '--format=tar', '-o', str(ARCHIVE), SOURCE], cwd=REPO, check=True)
source = HERE / 'source'
source.mkdir()
with tarfile.open(ARCHIVE) as archive:
    archive.extractall(source, filter='data')
original = HERE / 'original-run'
manifest = json.loads((original / 'input-manifest.json').read_bytes())
rows = {}
for name, want in manifest['files'].items():
    target = source / name
    if name.startswith('artifacts/user-reports/poc-n-symbolic-e6d5-prep/'):
        data = (OLD / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != want:
            raise ValueError('authorized original-input hash mismatch: ' + name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    got = hashlib.sha256(target.read_bytes()).hexdigest()
    if got != want:
        raise ValueError('immutable archive source mismatch: ' + name)
    rows[name] = dict(bytes=target.stat().st_size, sha256=got)
shutil.copyfile(original / 'input-manifest.json', source / 'artifacts/user-reports/poc-n-symbolic-e6d5-prep/input-manifest.json')
frozen = dict(source=SOURCE, archive_sha256=hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(), files=rows)
(HERE / 'source-freeze.json').write_text(json.dumps(frozen, sort_keys=True, indent=2) + '\n', encoding='utf-8')
print(json.dumps(dict(archive_sha256=frozen['archive_sha256'], verified_files=len(rows))))
