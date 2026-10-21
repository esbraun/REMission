"""Exact accepted-source, locks, raw reviews, coverage and scoped-write audit."""
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[4]
BASE='69e6ae9dc5bf85ddbf39976d2ce4ce70bce1ea1e'
OUT=Path(__file__).resolve().parent


def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)


def main():
    protected=['contracts/domain','contracts/dgp','contracts/artifacts','methods','tests/contracts','tests/library','tests/integration/replay','tooling/library','web','docs/implementation/evidence/G0-LIB','docs/implementation/evidence/G0-TIME-R1','docs/implementation/evidence/G0-CLOSURE-20261021','docs/implementation/evidence/G1-FOUNDATION-20261021','docs/implementation/g1-technical-plan-20261021.md','tooling/foundation/requirements.lock','tooling/foundation/runtime.Dockerfile','tooling/foundation/evaluator.Dockerfile','tooling/foundation/run_stack.py']
    subprocess.check_call(['git','diff','--exit-code',BASE,'--',*protected],cwd=ROOT)
    allowed=['.gitattributes','docs/implementation/check-ledger-20261020.py','docs/implementation/g0-task-test-ledger-20261020.json','docs/implementation/launch-status-20261020.md','docs/implementation/library-qualification.md','docs/implementation/g1-estint-probability-precision-', 'docs/implementation/evidence/G1-GENERATOR-INTERFACES-20261021/','contracts/runs/','tests/run_contracts/','services/foundation/cli.py','services/foundation/replay.py','services/learner/export_observed.py','services/learner/worker.py','tooling/foundation/service.Dockerfile','tooling/foundation/learner.Dockerfile']
    paths=git('diff','--name-only',BASE).decode().splitlines()
    assert all(any(path==prefix or (prefix.endswith(('/', '-')) and path.startswith(prefix)) for prefix in allowed) for path in paths),paths
    raw={
      'foundation-final-ready-review.md':'fbbf95f62dd5d2a2d016caabcd5c22f58bf94268',
      'foundation-final-evidence-manifest.json':'369c9fc71a32117c161dbf4423e4bac193d45a84',
      'probability-plan-ready-review.md':'c68541474c6e63b8f1cf9902c0d8c2b41def100e'}
    for name,blob in raw.items():assert git('hash-object','--no-filters',str(OUT/name)).decode().strip()==blob
    original=json.loads(git('show',BASE+':docs/implementation/g0-task-test-ledger-20261020.json'))
    current=json.loads((ROOT/'docs/implementation/g0-task-test-ledger-20261020.json').read_text())
    assert original['coverage']==current['coverage'] and len(current['coverage'])==635
    for task in current['tasks']:
        before=next(t for t in original['tasks'] if t['id']==task['id'])
        assert all(task[k]==before[k] for k in ('id','test_ids','requirement_ids','depends_on'))
    print('PASS: accepted numerical/domain/DGP/UI/backend tests/locks/raw history unchanged; only bounded shared-contract/admission/evidence paths; all635 rows/task/dependency/test mappings preserved')


if __name__=='__main__':main()
