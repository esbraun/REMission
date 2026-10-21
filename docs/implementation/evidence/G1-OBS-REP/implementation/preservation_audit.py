"""Exact v1 Git bytes and all 635 mappings; no regeneration/normalization."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
BASE = '6bc8bd998e8a0baaef9884998e740665fb5fd7b1'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def main():
    baseline = json.loads((OUT / 'v1-byte-inventory-raw.json').read_bytes())
    checked = []
    for item in baseline['files']:
        path = item['path']
        original = git('show', BASE + ':' + path)
        assert hashlib.sha256(original).hexdigest() == item['git_sha256'], path
        assert git('hash-object', '--path', path, path).decode().strip() == item['git_blob'], path
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == item['working_sha256'], 'original checkout bytes changed: ' + path
        assert not git('diff', BASE, '--', path), path
        checked.append(dict(path=path, git_blob=item['git_blob'], git_sha256=item['git_sha256'], worktree_sha256=item['working_sha256']))
    # Preserve the v1 typed parser and frozen scientific verifier as source too.
    for path in ['contracts/domain/common.py', 'contracts/domain/entities.py', 'contracts/domain/boundaries.py', 'contracts/domain/export.py',
                 'contracts/runs/observed.py', 'contracts/runs/private.py', 'contracts/runs/private_admission.py', 'contracts/runs/export.py',
                 'services/foundation/migrations/001_foundation.sql']:
        assert not git('diff', BASE, '--', path), 'v1 parser/source changed: ' + path
    path = 'docs/implementation/g0-task-test-ledger-20261020.json'
    original = json.loads(git('show', BASE + ':' + path))
    current = json.loads((ROOT / path).read_bytes())
    assert current['coverage'] == original['coverage'] and len(current['coverage']) == 635
    assert current['coverage_counts'] == original['coverage_counts']
    for before, after in zip(original['tasks'], current['tasks']):
        assert before['id'] == after['id']
        for key in ['test_ids', 'requirement_ids', 'depends_on']:
            assert before[key] == after[key]
    import base64
    envelope = json.loads((OUT.parent / 'R1/source-evidence.json').read_bytes())
    for item in envelope['artifacts']:
        raw = base64.b64decode(item['base64'])
        assert len(raw) == item['byte_length'] and hashlib.sha256(raw).hexdigest() == item['raw_sha256']
        assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == item['git_blob_sha1']
        if item['name'] == 'original-proposal':
            assert (ROOT / 'docs/implementation/g1-observed-representation-proposal-20261021.md').read_bytes() == raw
    accepted = json.loads((OUT / 'accepted-source-manifest.json').read_bytes())
    for item in accepted['artifacts']:
        raw = (ROOT / item['path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == item['sha256'] and len(raw) == item['bytes']
    result = dict(status='passed', base=BASE, head=git('rev-parse', 'HEAD').decode().strip(), original_v1_files=checked,
                  coverage_entries=635, original_task_test_dependencies_unchanged=True, original_and_accepted_plan_bytes_unchanged=True)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
