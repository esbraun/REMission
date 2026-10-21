"""Preserve the immutable ready review in flat blob storage, with its path index."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
REPORT = 'b03e3b54078778d2a7d063ea2cf9cd41e5ccf9a4'
MANIFEST = '825f1d2076fc19e9849a843bcce7be4d9dab7c57'


def main():
    for blob, name in [(REPORT, 'ready-review.md'), (MANIFEST, 'ready-manifest.json')]:
        raw = subprocess.check_output(['git', 'cat-file', 'blob', blob], cwd=ROOT)
        target = OUT / name
        assert not target.exists() or target.read_bytes() == raw
        target.write_bytes(raw)
    manifest = json.loads((OUT / 'ready-manifest.json').read_bytes())
    assert len(manifest['files']) == 960 and len(manifest['commands']) == 29
    (OUT / 'b').mkdir(exist_ok=True)
    blobs = list(dict.fromkeys(item['git_blob'] for item in manifest['files'].values()))
    batch = subprocess.run(['git', 'cat-file', '--batch'], input=('\n'.join(blobs)+'\n').encode(), cwd=ROOT, capture_output=True, check=True).stdout
    position = 0
    for blob in blobs:
        end = batch.index(b'\n', position)
        header = batch[position:end].decode().split()
        assert header[:2] == [blob, 'blob']
        length = int(header[2]); raw = batch[end+1:end+1+length]
        assert hashlib.sha1(b'blob '+str(length).encode()+b'\0'+raw).hexdigest() == blob
        target = OUT / 'b' / blob
        assert not target.exists() or target.read_bytes() == raw
        target.write_bytes(raw)
        position = end+1+length+1
    for path, item in manifest['files'].items():
        raw = (OUT / 'b' / item['git_blob']).read_bytes()
        assert len(raw) == item['bytes'] and hashlib.sha256(raw).hexdigest() == item['sha256'], path
    print(f'PASS: full ready report and 960 original-path artifacts preserved as {len(blobs)} exact flat blobs; 29 UUID captures indexed')


if __name__ == '__main__':
    main()
