"""Evidence-only freeze metadata; source commit excludes all later evidence bytes."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
BASE = '6bc8bd998e8a0baaef9884998e740665fb5fd7b1'
SOURCE = 'f049f4bc5b83ff7cc7cfebedff41a5f6fdcf77ae'
OLD = '44d25a06cc8e996eb2b5aeb01c2ff2694ca4d72f'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def write(path, value):
    path.write_text(value, encoding='utf-8', newline='\n')


def prepare():
    blob = 'd57bea21afdf2c4dda209b8491112755cb1fa3ca'
    path = OUT / 'luna-v1-audit-44d25-raw.md'
    raw = git('cat-file', 'blob', blob)
    assert len(raw) == 2659
    path.write_bytes(raw)
    manifest_path = OUT / 'accepted-source-manifest.json'
    manifest = json.loads(manifest_path.read_bytes())
    item = dict(path=path.relative_to(ROOT).as_posix(), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw), git_blob=blob)
    manifest['artifacts'] = [a for a in manifest['artifacts'] if a['path'] != item['path']] + [item]
    write(manifest_path, json.dumps(manifest, indent=2) + '\n')
    text = f'''# OBS-REP-02 frozen implementation candidate

Source commit: `{SOURCE}`; accepted base/integration target: `{BASE}` / `main`; branch: `launch/g1-observed-contracts-20261021`. The final candidate is an evidence-only descendant of this source commit. Verify the final head with the parent handoff and require no runtime/test/container source differences from this source commit. The only later attributes delta declares LF for this README, checkpoint and raw manifest; source/raw byte policies are unchanged. The evidence manifest excludes itself and does not embed the eventual final commit hash, avoiding self-reference. No PR or merge was performed by this worker.

Owner assignment: `gpt-6.1-sol` / `xhigh`. Escalation: difficult dual-version dispatch, full original administrative archive, exact provenance/closure and live authority isolation preserving v1 products/history. Independent effective-model introspection is unavailable; assignment metadata is recorded without substitution. Nonsecret thread: `01a16010-edcd-73d1-a3b2-6849b68f580e`. Own writing checkout: `C:/Users/erics/Documents/Projects/REMission-worktrees/g1-observed-contracts-sol-20261021`. No helpers were spawned by this worker. Source is frozen for independent exact-head review; implementation is not accepted.

Accepted plan is the complete R1 `b2e8adf3ebe95ef94dae7399e2a27b9cc89420ec`, imported documentation-only as `437f063`. The full original plan/changes-requested chain remains byte-exact in `../R1/source-evidence.json`; accepted PLAN ONLY critique blob `247db69414bf153dfe46ca2f734e94d58e9b0480`, Luna inventories and future live-hold locator map remain raw copies indexed by `accepted-source-manifest.json`. The Luna audit in `luna-v1-audit-44d25-raw.md` addresses superseded 44 only; successor preservation is independently recorded by the author's final audit and clean clone.

Implemented source: separate domain/run `2.0.0` profile and explicit version/kind dispatch; signed finite unbounded diary; complete support assignment vectors/context/mechanism/window; exact report/revision outcome links; stage ledgers and independently trusted completion receipts; canonical day0..84 roster/day85 administrative assessment; hold causal/review/dependency chains and stale reconstruction; deterministic identities/full private seed keys; complete original observed/admin replay; migration 002 immutable SQLite archive, authenticated ownership, transactional receipt/cursor and allowlisted clinical subset. Current import rejects an entire independent-hold partition before publication, including legacy entrypoints. Generated consent/approval/resolution never authorizes live actions. All v1 products remain separate.

Successor source repairs inherited private barriers: exact evaluation configuration/roster, result execution/run identity, independently trusted solved calibration, registered calibrated-cell export gating, seed roster, private truth parser/roster and complete-result export/receipt consistency. Four new private-v2 wire tests include actual public export qualification/full keys and positive plus reject cases; no generator/evaluator engine or scientific policy was implemented. `{OLD}` and curated/clone attempt003/000 remain superseded historical evidence; they do not cover the changed private module. Curated004 freshly builds the successor's consumer images and public fixture helper, while exact source clone001 checks the private paths.

Observed on exact source: clean clone001 initially/finally clean with core.autocrlf=false; domain/DGP/TIME 67 passed, run/probability/admission 49 passed, service/replay/SQLite 25 passed; artifact/lineage 11 and DR/OPE 11 passed; old/new schema/dictionary/binding checks, pip/runtime checks, 635 original mappings and all 53 protected v1 Git blobs passed. Curated004 admits v2 public fixtures as actual service UID10001 and learner UID10002, without source mounts, and verifies copied image bytes against own source. Private imports/files/listing/network/write probes deny access, with a positive UID20000 evaluator canary read/HTTP control. Actual curated UID10001 image runs all 25 service/replay tests separately. Source private-v2/DGP/truth implementations are absent from these consumer images; source clone tests cover the private repair. Pinned npm lock/integrities remain accepted-base bytes; build records include installed Node/package versions. Ordinary checks run with 2 CPU/2 GiB, network none, read-only source/root and bounded tmpfs. Registry access was authorized only for pinned npm dependency acquisition during image builds. No visible UI change required browser validation; the curated client build includes typecheck/context tests/build.

Read `checks/*.command.json` for exact commands, executing HEAD, dirty evidence state, raw stream hashes and source byte snapshots; `clone-attempts/001/commands.json` plus `executed-source.json` bind clean-clone commands/bytes; `curated-attempts/004/commands.json` plus `inventory.json` bind images, actual role probes and no-source-mount byte audits. `raw-manifest.json` indexes all preserved raw artifacts and source hashes. Earlier failures remain intact: fixture context/owner attempts, duplicate UTC raw serialization, offline npm acquisition and initial whitespace check. Passed repairs do not erase their raw outputs. Earlier dirty-source runs and source44 results retain their original limited coverage. Final metadata changes are evidence/status only and must be verified against the frozen source tree.

**B-OBS2-LIVE-HOLD / T-OBS2-LIVE-HOLD remains open and mandatory.** The rejection guard implements no live invalidation latch, owned review or clearance service operation; that later task is an acyclic prerequisite for affected current-demo/full G1 acceptance after contract acceptance. Real trusted producer qualification, generator/evaluator/filter/likelihood/calibration execution, full statistics/catalog/presets, G1-G7, human factors, clinical review and clinical validation remain pending. Subjective burden law and independent-hold clearance law remain null/unspecified. Affected producers and likelihood consumers stay HELD until independent contract acceptance, root integration and explicit dispatch. No human or clinical gate is closed.

Frozen generator `9ad8a86f8b81639eb3051292a9d7bfd714bf28dc` and evaluator `6897c36cba0154c700c98f0f4c1dd62ca6b6a850` remain unaccepted recovery checkpoints; their outcome/transition implementations were not read, edited or merged. Existing app/reviewer services, databases and browser state on 8765-8768 were untouched. Only own named curated resources were created and removed. No concrete blocker prevents independent review; the named live-hold and producer/scientific prerequisites remain explicit dependencies. Root alone owns reviewer dispatch, PR and merge.
'''
    write(OUT / 'README.md', text)
    write(OUT / 'checkpoint.md', text.replace('# OBS-REP-02 frozen implementation candidate', '# OBS-REP-02 durable final checkpoint', 1))
    ledger_path = ROOT / 'docs/implementation/g0-task-test-ledger-20261020.json'
    ledger = json.loads(ledger_path.read_bytes())
    supplement = ledger['observed_representation_v2']
    supplement.update(implementation_status='frozen_pending_independent_exact_head_review', source_commit=SOURCE,
                      evidence_manifest='docs/implementation/evidence/G1-OBS-REP/implementation/raw-manifest.json',
                      exact_clone_attempt='001', curated_attempt='004', observed_tests=dict(domain=67, run_contracts=49, service_replay=25, artifact_lineage=11, dr_ope=11))
    tests = {
        'T-OBS2-DIARY': ['tests/contracts/test_observed_v2.py', 'tests/integration/replay/test_observed_v2_archive.py'],
        'T-OBS2-SUPPORT': ['tests/contracts/test_observed_v2.py', 'tests/run_contracts/test_observed_v2.py', 'tests/run_contracts/test_private_v2.py'],
        'T-OBS2-LINKS': ['tests/run_contracts/test_observed_v2.py', 'tests/contracts/test_observed_v2.py'],
        'T-OBS2-HOLD': ['tests/contracts/test_observed_v2.py', 'tests/integration/replay/test_observed_v2_archive.py'],
        'T-OBS2-ARCHIVE': ['tests/integration/replay/test_observed_v2_archive.py', 'tooling/foundation/observed_v2_probe.py'],
        'T-OBS2-COMPAT': ['docs/implementation/evidence/G1-OBS-REP/implementation/preservation_audit.py', 'tests/run_contracts/test_private_v2.py'],
        'T-OBS2-LIVE-HOLD': ['docs/implementation/evidence/G1-OBS-REP/implementation/live-hold-map-raw.md'],
    }
    prefix = OUT.relative_to(ROOT).as_posix() + '/'
    for name, task in supplement['subtasks'].items():
        task['evidence'] = [prefix + 'README.md', prefix + 'raw-manifest.json', *tests[name]]
        task['test_cases'] = []
        for test_path in tests[name]:
            if not Path(test_path).name.startswith('test_'):
                continue
            module = ast.parse((ROOT / test_path).read_bytes())
            task['test_cases'] += [test_path + '::' + node.name + '.' + method.name for node in module.body if isinstance(node, ast.ClassDef)
                                  for method in node.body if isinstance(method, ast.FunctionDef) and method.name.startswith('test_')]
        if name != 'T-OBS2-LIVE-HOLD':
            task['evidence'] += [prefix + 'clone-attempts/001/commands.json', prefix + 'curated-attempts/004/inventory.json',
                                 *[prefix + f'checks/{number:03d}.command.json' for number in [39, 40, 41, 42, 43, 44]]]
    write(ledger_path, json.dumps(ledger, indent=2) + '\n')
    status_path = ROOT / 'docs/implementation/launch-status-20261020.md'
    status = status_path.read_bytes()
    status = status.replace(b'Implementation is in progress/pending exact-code review; affected generator/evaluator producers',
                            ('Source implementation is frozen at `'+SOURCE+'`, with exact-code review pending; affected generator/evaluator producers').encode())
    status_path.write_bytes(status)


def freeze_manifest():
    assert git('rev-parse', 'HEAD').decode().strip() == SOURCE
    scope = ['contracts', 'services', 'tests', 'tooling/foundation', 'web']
    assert git('diff', SOURCE, '--', *scope) == b'', 'frozen source changed'
    original_attributes = git('show', SOURCE + ':.gitattributes')
    attributes = (ROOT / '.gitattributes').read_bytes().replace(b'\r\n', b'\n')
    expected_delta = ('# Final evidence metadata has declared reproducible bytes on every checkout.\n'
                      'docs/implementation/evidence/G1-OBS-REP/implementation/README.md text eol=lf\n'
                      'docs/implementation/evidence/G1-OBS-REP/implementation/checkpoint.md text eol=lf\n'
                      'docs/implementation/evidence/G1-OBS-REP/implementation/raw-manifest.json text eol=lf\n').encode()
    assert attributes == original_attributes.replace(b'\r\n', b'\n') + expected_delta
    tree = git('ls-tree', '-r', SOURCE, '--', *scope).decode().splitlines()
    source = {}
    for line in tree:
        metadata, path = line.split('\t', 1)
        source[path] = dict(git_blob=metadata.split()[2], own_checkout_sha256=hashlib.sha256((ROOT / path).read_bytes()).hexdigest())
    raw = {}
    for path in sorted(OUT.rglob('*')):
        if not path.is_file() or '__pycache__' in path.parts or path.name == 'raw-manifest.json':
            continue
        value = path.read_bytes()
        raw[path.relative_to(ROOT).as_posix()] = dict(bytes=len(value), sha256=hashlib.sha256(value).hexdigest())
    checks = []
    for path in sorted((OUT / 'checks').glob('*.command.json')):
        item = json.loads(path.read_bytes())
        checks.append(dict(path=path.relative_to(ROOT).as_posix(), head=item.get('head'), exit_code=item['exit_code'], command=item['command']))
    inventory = json.loads((OUT / 'curated-attempts/004/inventory.json').read_bytes())
    assert inventory['head'] == SOURCE
    clone = json.loads((OUT / 'clone-attempts/001/executed-source.json').read_bytes())
    assert clone['head'] == SOURCE
    value = dict(accepted_base=BASE, frozen_source_commit=SOURCE, superseded_source_commit=OLD, source_scope=scope, source_files=source,
                 source_attributes_sha256=hashlib.sha256(original_attributes).hexdigest(), final_attributes_sha256=hashlib.sha256(attributes).hexdigest(),
                 evidence_only_attributes_delta=expected_delta.decode(),
                 source_map_sha256=hashlib.sha256(json.dumps(source, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
                 raw_artifacts=raw, check_attempts=checks, curated_roles=inventory['roles'],
                 final_candidate_binding='Evidence-only descendant; verify no source_scope diff from frozen_source_commit. Final HEAD is returned externally to avoid hash cycle.',
                 exclusions=['This manifest excludes its own bytes/hash', 'No production, independent review, live-hold integration, statistical, human or clinical acceptance'])
    write(OUT / 'raw-manifest.json', json.dumps(value, indent=2) + '\n')
    print('PASS: source unchanged; exact source/raw/image manifest written without self-reference')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['prepare', 'manifest'])
    args = parser.parse_args()
    prepare() if args.mode == 'prepare' else freeze_manifest()
