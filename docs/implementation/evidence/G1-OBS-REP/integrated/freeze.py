"""Durable merged verification checkpoint, separate from historical source manifests."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
MERGE = 'ec18cb4020ba239710a3fd615e365d5cd72b4d80'
REVIEWED = '3763f7571a47d8ab421a2f8ad4e36e49fe1cc478'
BASE = '6bc8bd998e8a0baaef9884998e740665fb5fd7b1'
PR = 'https://github.com/esbraun/REMission/pull/18'
REPORT = 'b03e3b54078778d2a7d063ea2cf9cd41e5ccf9a4'
READY_MANIFEST = '825f1d2076fc19e9849a843bcce7be4d9dab7c57'
SCOPE = ['contracts', 'services', 'tests', 'tooling/foundation', 'web']


def git(*args): return subprocess.check_output(['git', *args], cwd=ROOT)
def sha(raw): return hashlib.sha256(raw).hexdigest()
def write(path, value): path.write_text(value, encoding='utf-8', newline='\n')


def prepare():
    text = f'''# OBS-REP-02 integrated engineering verification

[PR18]({PR}) merged reviewed head `{REVIEWED}` onto accepted base `{BASE}` as `{MERGE}`. Independently observed merge parents are exactly those two commits; merged tree `9c1b202743be039283a209c0505c9f60742e611b` equals the reviewed head's entire tree. This checkpoint records verification of that merge, not a new runtime implementation. Own branch `launch/g1-obs2-integrated-verify-20261021`, checkout `C:/Users/erics/Documents/Projects/REMission-worktrees/g1-obs2-integrated-verify-sol-20261021`; verified clean at the merge before work. No runtime/test/container/web source changed. The final verification commit contains evidence, documentation/ledger status and narrow attributes for new evidence only; no PR or merge by this worker.

Assigned `gpt-6.1-sol / xhigh` continuing difficult cross-version provenance/closure and authority isolation. This is assignment metadata; effective-model introspection is unavailable and no substitution occurred. Nonsecret CODEX_THREAD_ID `01a16010-edcd-73d1-a3b2-6849b68f580e`. Root alone assigns helpers; none were spawned. Old author/repair/reviewer/producer/evaluator checkouts and services/DB/browser state on8765-8768 were untouched. No live-hold planning or implementation was started.

The complete refreshed Astra **ready_to_ship, bounded scope only** report is [ready-review.md](ready-review.md), raw Git blob `{REPORT}`, SHA256 `13e7d89744b1c52e5432fcd121a26397a400f180b514156eff9b5f45a1c4b9dc`. Its unchanged [ready-manifest.json](ready-manifest.json), blob `{READY_MANIFEST}`, indexes960 original-path artifacts and29 unique UUID top-level command captures. All960 originals are preserved byte-exact as691 deduplicated flat files in `b/<git_blob>`; the manifest retains original paths, sizes, SHA256 and Git blob IDs. This storage adds no deeper path hierarchy. Raw historical reports/addenda/manifests retain their original source bindings: original implementation f049/ceb5 (194-source map,764 raw artifacts), repair124/3763 (196-source map,1718 raw artifacts). They are checked against their own sources and are not relabeled as the merge's execution evidence.

Observed on merged source:67 domain/DGP/TIME tests,54 run/probability/admission tests,25 service/replay/SQLite tests,11 artifact/library and11 DR/OPE tests passed; all five old/new schema/dictionary/binding exporters, pip check and actual service runtime qualification passed. The unchanged independent complete85 wire/calendar was re-admitted. Native audit verified exact merge parents/tree,196 reviewed source Git blobs, all earlier raw artifact hashes, all53 protected v1 Git blobs/v1 parser source, and exact original635 coverage/task/test/dependency mappings. No v1 regeneration or migration occurred. The final ledger check and diff-whitespace check passed.

The immutable independent private day84/day85 directories from the ready review were reconstructed from their exact indexed blob bytes in bounded temporary storage, then parsed through full `verify_run_v2`/`verify_result_v2` on merged code. Delayed day84 positive passed; correctly keyed/qualified day85 variant rejected specifically with `generated event outside accepted local horizon -14..84`. These authorities/calibration sample files are explicitly contract fixtures, never actual scientific calibration or real producer qualification.

Fresh role verification reused the reviewer's EXACT service `sha256:82f5b9c4ea1f13a0bee5fe1a852a220fba16752d5aa21df8fa3726b8c483d6a8` and learner `sha256:1d30bb4940c403cf2f2a0d239b6c40b8a121375bede14fa58874dd968a9c0795` images. Before reuse, actual copied runtime/probe bytes were compared inside no-source-mount/no-network containers and against this merged checkout. Actual UID10001/10002 then passed ordinary positive, foreign-hold rejection, numeric day85 rejection, the SAME independently authored complete85 wire and private import/read/list/network/write denials. UID20000 evaluator canary file and HTTP controls passed. Consumer mounts were read-only volumes only, networknone, read-only root; no images were rebuilt or qualified dependencies changed. Only uniquely named integrated containers/networks/volumes were created and cleaned. Client build/typecheck evidence remains the independently qualified unchanged-source evidence; no visible UI changed or unrelated browser/human gate closed.

Ordinary containers used2CPU/2GiB, networknone, read-only own source/root, dropped capabilities/no-new-privileges and bounded/tmp. Exact commands/exits/raw stdout/stderr/source byte maps are under unique `c/<uuid>/`; physical image/role commands and inventory under `roles/<uuid>/`. `raw-manifest.json` binds merge source bytes, images, reviewed report/blobs and new captures, excluding its own bytes/final verification commit to avoid a hash cycle. The final commit ID is returned externally. No new integrated check failed.

Portability limitation remains explicit: the independent review's INITIAL deep Windows HTTPS-clone default checkout failed with Filename too long, exit128. Clone-local `git config core.longpaths true` followed by retry passed; no global setting/source correction was used. The existing shorter temporary-clone destination worked. Deep Windows reproduction needs that clone-local prerequisite or a shorter destination; no default deep-checkout success is claimed. Both failure/retry raw captures remain in the full ready-review blob index. Earlier original-review four overwritten streams remain unavailable and were not reconstructed; the original full-horizon addendum's two assembly failures and unsubmitted intermediate-file limitation remain as recorded.

Repository checks are root's PR18 pre-merge observations: rulesets[], protection404/notprotected, statuses/workflows/checkruns[], mergeable=true and exact heads; no configured CI and no bypass. They are attributed to root, not fabricated as this worker's CI execution. The independently ready report plus delegated merged checks establish bounded OBS-REP-02/2.0.0 contracts/archive/admission/current-import rejection-guard engineering acceptance only.

**B-OBS2-LIVE-HOLD / T-OBS2-LIVE-HOLD remains required next engineering.** The current guard is not arrival-time invalidation, owned review or evidence-gated clearance. Root will separately dispatch bounded executable-contract planning with independent critique; this worker did not begin it. Producers/likelihood consumers remain HELD until root explicit dispatch. Actual trusted producer/filter/likelihood/calibration execution, full statistics/catalog/presets/G1-G7 and human-factors/clinical review/clinical validation remain open. Subjective burden and independent-hold clearance laws remain unspecified/null. No human or clinical acceptance is inferred.
'''
    write(OUT / 'README.md', text)
    ledger_path = ROOT / 'docs/implementation/g0-task-test-ledger-20261020.json'
    ledger = json.loads(ledger_path.read_bytes()); status = ledger['observed_representation_v2']
    prefix = OUT.relative_to(ROOT).as_posix()+'/'
    integrated = dict(status='verified_bounded_engineering_integration', pr=PR, reviewed_head=REVIEWED, reviewed_base=BASE, merge_commit=MERGE,
                      ready_report_blob=REPORT, ready_manifest_blob=READY_MANIFEST, checkpoint=prefix+'README.md', evidence_manifest=prefix+'raw-manifest.json',
                      observed_tests=dict(domain=67, run_contracts=54, service_replay=25, artifact_lineage=11, dr_ope=11),
                      source_edits=False, live_hold='required_next_engineering_not_started', consumers='HELD_until_root_explicit_dispatch',
                      repository_preflight=dict(source='root_PR18_merge_preflight_observations', configured_ci=False, bypass=False, rulesets=[], protection='404_not_protected', statuses=[], workflows=[], checkruns=[]))
    status['integrated_verification'] = integrated
    status['implementation_status'] = 'integrated_bounded_engineering_verified'
    status['repair_01']['disposition'] = 'ready_to_ship_bounded_exact_head_then_PR18_integrated'
    for name, task in status['subtasks'].items():
        if name != 'T-OBS2-LIVE-HOLD':
            task['status'] = 'bounded_shared_contract_archive_engineering_integrated'
            for item in [prefix+'README.md', prefix+'raw-manifest.json']:
                if item not in task['evidence']: task['evidence'].append(item)
        else:
            task['status'] = 'required_next_engineering_pending_separate_plan_critique_and_dispatch'
            task['dependency_status'] = {'OBS2-CONTRACT-ACCEPTANCE': 'PR18_bounded_contracts_archive_integrated_verified'}
    write(ledger_path, json.dumps(ledger, indent=2)+'\n')
    for filename, heading in [('launch-status-20261020.md', 'Current OBS-REP-02 integrated state'), ('contracts.md', 'OBS-REP-02 integrated engineering checkpoint')]:
        path = ROOT / 'docs/implementation' / filename; raw = path.read_bytes()
        marker = ('\n# '+heading+'\n').encode()
        if marker in raw: raw = raw[:raw.index(marker)]
        raw += marker+('\n[PR18]('+PR+') merged reviewed `'+REVIEWED+'` / base `'+BASE+'` as `'+MERGE+'`; delegated [integrated verification](evidence/G1-OBS-REP/integrated/README.md) passed. This current status supersedes earlier pending-candidate checkpoints. Acceptance is bounded contracts/archive/rejection-guard engineering only. B-OBS2-LIVE-HOLD remains mandatory next engineering; affected consumers remain HELD for root explicit dispatch and full G1/statistical/human/clinical gates remain open.\n').encode()
        path.write_bytes(raw)


def manifest():
    assert not git('diff', MERGE, '--', *SCOPE)
    source = {line.split('\t', 1)[1]: dict(git_blob=line.split()[2], own_checkout_sha256=sha((ROOT / line.split('\t', 1)[1]).read_bytes()))
              for line in git('ls-tree', '-r', MERGE, '--', *SCOPE).decode().splitlines()}
    raw = {p.relative_to(ROOT).as_posix(): dict(bytes=len(p.read_bytes()), sha256=sha(p.read_bytes())) for p in sorted(OUT.rglob('*'))
           if p.is_file() and '__pycache__' not in p.parts and p.name != 'raw-manifest.json'}
    inventories = [json.loads(p.read_bytes()) for p in (OUT / 'roles').glob('*/inventory.json')]
    assert len(inventories) == 1 and inventories[0]['merge'] == MERGE
    commands = [dict(path=p.relative_to(ROOT).as_posix(), **json.loads(p.read_bytes())) for p in (OUT / 'c').glob('*/command.json')]
    assert commands and all(item['head'] == MERGE and item['exit_code'] == 0 for item in commands)
    value = dict(merge=MERGE, reviewed=REVIEWED, base=BASE, pr=PR, source_scope=SCOPE, source_files=source,
                 merge_tree=git('rev-parse', MERGE+'^{tree}').decode().strip(), reviewed_tree=git('rev-parse', REVIEWED+'^{tree}').decode().strip(),
                 source_map_sha256=sha(json.dumps(source, sort_keys=True, separators=(',', ':')).encode()),
                 ready_report_blob=REPORT, ready_manifest_blob=READY_MANIFEST, indexed_review_artifacts=960, flat_review_blobs=691,
                 raw_artifacts=raw, captures=commands, reused_image_inventory=inventories[0],
                 evidence_only_attributes_diff=git('diff', MERGE, '--', '.gitattributes').decode(),
                 final_binding='Final verification commit is documentation/evidence only; source equality is to MERGE. Self manifest/final commit excluded to avoid cycles.')
    write(OUT / 'raw-manifest.json', json.dumps(value, indent=2)+'\n')
    print('PASS: integrated merge/source/review/image/raw manifest written without historical relabeling or self-reference')


def verify():
    value = json.loads((OUT / 'raw-manifest.json').read_bytes())
    assert not git('diff', MERGE, 'HEAD', '--', *SCOPE) and not git('diff', 'HEAD', '--', *SCOPE)
    for path, item in value['raw_artifacts'].items():
        raw = (ROOT / path).read_bytes(); assert len(raw) == item['bytes'] and sha(raw) == item['sha256'], path
    assert value['merge_tree'] == value['reviewed_tree']
    for role in value['reused_image_inventory']['roles'].values():
        for path, digest in role['exact_source_sha256'].items():
            assert value['source_files'][role['source_paths'][path]]['own_checkout_sha256'] == digest
    print('PASS: exact merged runtime source, all integrated immutable raw bytes and reused physical image/source bindings')


if __name__ == '__main__': {'prepare': prepare, 'manifest': manifest, 'verify': verify}[sys.argv[1]]()
