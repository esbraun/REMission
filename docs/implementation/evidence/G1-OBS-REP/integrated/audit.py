"""Merge-specific source, old history, mappings and immutable review evidence audit."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
MERGE = 'ec18cb4020ba239710a3fd615e365d5cd72b4d80'
REVIEWED = '3763f7571a47d8ab421a2f8ad4e36e49fe1cc478'
BASE = '6bc8bd998e8a0baaef9884998e740665fb5fd7b1'


def git(*args): return subprocess.check_output(['git', *args], cwd=ROOT)
def digest(raw): return hashlib.sha256(raw).hexdigest()


def main():
    parents = git('show', '-s', '--format=%P', MERGE).decode().split()
    assert parents == [BASE, REVIEWED]
    tree = git('rev-parse', MERGE+'^{tree}').decode().strip()
    assert tree == git('rev-parse', REVIEWED+'^{tree}').decode().strip()
    scope = ['contracts', 'services', 'tests', 'tooling/foundation', 'web']
    assert not git('diff', MERGE, '--', *scope), 'merged runtime source changed'
    source_blobs = {line.split('\t', 1)[1]: line.split()[2] for line in git('ls-tree', '-r', MERGE).decode().splitlines()}
    manifests = []
    for path, source in [('implementation', 'f049f4bc5b83ff7cc7cfebedff41a5f6fdcf77ae'), ('repair-01', '124ab096120bf28a055f6413b4f813c83095ada7')]:
        manifest = json.loads((OUT.parent / path / 'raw-manifest.json').read_bytes())
        assert manifest['frozen_source_commit'] == source
        historical_blobs = {line.split('\t', 1)[1]: line.split()[2] for line in git('ls-tree', '-r', source).decode().splitlines()}
        for name, item in manifest['source_files'].items():
            assert historical_blobs[name] == item['git_blob']
            if path == 'repair-01': assert source_blobs[name] == item['git_blob']
        for name, item in manifest['raw_artifacts'].items():
            raw = (ROOT / name).read_bytes()
            assert len(raw) == item['bytes'] and digest(raw) == item['sha256'], name
        manifests.append(dict(path=path, historical_source=source, original_source_files=len(manifest['source_files']), raw_artifacts=len(manifest['raw_artifacts']), current_merge_equal=path == 'repair-01'))
    baseline = json.loads((OUT.parent / 'implementation/v1-byte-inventory-raw.json').read_bytes())
    assert len(baseline['files']) == 53
    for item in baseline['files']: assert source_blobs[item['path']] == item['git_blob']
    for name in ['contracts/domain/common.py', 'contracts/domain/entities.py', 'contracts/domain/boundaries.py', 'contracts/domain/export.py',
                 'contracts/runs/observed.py', 'contracts/runs/private.py', 'contracts/runs/private_admission.py', 'contracts/runs/export.py', 'services/foundation/migrations/001_foundation.sql']:
        assert git('rev-parse', BASE+':'+name) == git('rev-parse', MERGE+':'+name)
    ledger_path = 'docs/implementation/g0-task-test-ledger-20261020.json'
    original = json.loads(git('show', BASE+':'+ledger_path)); ledger = json.loads((ROOT / ledger_path).read_bytes())
    assert ledger['coverage'] == original['coverage'] and len(ledger['coverage']) == 635 and ledger['coverage_counts'] == original['coverage_counts']
    assert len(ledger['tasks']) == len(original['tasks'])
    for before, after in zip(original['tasks'], ledger['tasks'], strict=True):
        for key in ['id', 'test_ids', 'requirement_ids', 'depends_on']: assert before[key] == after[key]
    ready = json.loads((OUT / 'ready-manifest.json').read_bytes())
    assert ready['head'] == REVIEWED and ready['base'] == BASE and ready['disposition'] == 'ready_to_ship'
    assert len(ready['files']) == 960 and len(ready['commands']) == 29
    for path, item in ready['files'].items():
        raw = (OUT / 'b' / item['git_blob']).read_bytes()
        assert len(raw) == item['bytes'] and digest(raw) == item['sha256'], path
    assert digest((OUT / 'ready-review.md').read_bytes()) == '13e7d89744b1c52e5432fcd121a26397a400f180b514156eff9b5f45a1c4b9dc'
    print(json.dumps(dict(status='passed', merge=MERGE, reviewed=REVIEWED, base=BASE, tree=tree, exact_merge_parents=parents,
                         merged_tree_equals_reviewed=True, historical_manifests=manifests, protected_v1=53, exact_original_mappings=635,
                         ready_artifacts=960, ready_uuid_captures=29, runtime_source_unchanged=True), indent=2))


if __name__ == '__main__': main()
