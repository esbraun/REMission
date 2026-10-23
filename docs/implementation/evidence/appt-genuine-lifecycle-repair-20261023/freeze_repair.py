"""Freeze the single-helper repair from reviewed44 inputs; no Docker calls."""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OLD = ROOT / 'docs/implementation/evidence/appt-genuine-preparation-20261023'
binding = json.loads((OLD / 'operation-binding.json').read_bytes())
metadata = json.loads((OLD / 'selected-current-metadata.json').read_bytes())
backup = binding['maintenance_argv'][1]
assert backup[:2] == ['docker', 'run']
source = backup[-1]
assert (OLD / 'stock-backup.py').read_text(encoding='utf-8') == source + '\n'
create = ['docker', 'create', '--restart', 'no', *backup[2:]]
state = ROOT / 'artifacts/appt-genuine/maintenance-410'
paths = [ROOT / relative for relative in binding['predecessor_source_bindings']]
paths += [HERE / 'guarded_backup.py', HERE / 'test_guarded_backup.py',
          ROOT / 'tooling/foundation/analysis_lifecycle.py',
          OLD / 'operation-binding.json', OLD / 'readonly-terminal.py', OLD / 'stock-backup.py']
sources = {str(path.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(path.read_bytes()).hexdigest()
           for path in paths}
plan_path = HERE / 'operation-binding-r2.json'
plan = dict(task_id='APPT-GENUINE-POSITIVE', repair='P1-backup-helper-lifecycle-only',
    status='PREPARED_ONLY_FRESH_ASTRA_REVIEW_AND_ROOT_GO_REQUIRED',
    base='41056f0c06a2afa1141c33eeb3a934a1969d19bb',
    supersedes_operation_head='44fbff41c69aefce6c366f9c0689401813c9423b',
    finding_report_blob='1b5ad0b7c5fbf9a52f251fc8af370be99d8612f7',
    predecessor_binding='docs/implementation/evidence/appt-genuine-preparation-20261023/operation-binding.json',
    source_sha256=sources, old_image=binding['old_image'], new_image=binding['new_image'],
    original_cid=metadata['containers'][binding['service']]['Id'],
    service=binding['service'], retained_service=binding['retained_service'],
    failed_replacement=binding['failed_replacement'], database_volume='remission-poc13-ac8e16e0-database',
    private_root=binding['private_root'], temporary_envfile=binding['temporary_envfile'],
    backup_source=source, backup_create_argv=create,
    replacement_create_argv=binding['maintenance_argv'][3],
    backup_evidence_root=str(state / 'backup'), preflight_path=str(state / 'preflight.json'),
    terminal_reference='docs/implementation/evidence/pa3-native-terminal-20261022/terminal-database-readonly.json',
    result_sha256='850ffce701dd32587bf2b8cc2abd8121a574b4dddc16a8910b261fc4ceb6faa1',
    unchanged_scope='All first-RO baseline, original authority/owner/patient/result/trusted-launch/H*, private ACL/environment/credential input, authenticated API/browser/historical-cutoff, no-job/no-fit and cloud exclusions remain as reviewed44. Old raw backup-run/unchecked rollback argv are superseded; use only this guarded adapter for backup and subsequent transitions/recovery.',
    sequence_before_adapter=['Fresh root assignment and exact reviewed head/base/sole executor;',
        'unchanged selected-resource/name/path and no-active-controller/worker guards;',
        'unchanged frozen first RO audit; save preflight.json and enforce all protected-table/control bindings;',
        'unchanged effective-environment/source-only override and private ACL-before-write gates;',
        'unchanged one stop of original service, then verify clean terminal/no other active DB consumer.'],
    sequence_after_adapter=['backup', 'rename-original', 'create-replacement', 'start-replacement',
        'unchanged before-auth health/resource/source/control/inode/protected-table verification;',
        'unchanged later owner API/browser qualification only after its assigned GO.'],
    limits=dict(absolute_backup_create_prearm_start_terminal_seconds=60,
        backup_create_client_cap_seconds=10, prestart_selected_inspect_seconds=3,
        lifecycle_prearm_ack_seconds=5, lifecycle_stop_seconds=4,
        lifecycle_kill_seconds=4, lifecycle_independent_inspect_seconds=3,
        lifecycle_process_reap_wait_seconds=2, lifecycle_per_handle_reap_max_seconds=4,
        database_consumer_inspect_seconds=3,
        forward_command_seconds=15, recovery_rename_seconds=5, recovery_start_seconds=10),
    failure_rule='No start before exact literal-CID/nonce/deadline/live-PID ACK. Existing supervision stops/kills/inspects same CID and reaps both handles. Every subsequent action freshly validates typed terminal exited/dead, Runningfalse/PID0, matching supervision and integer reaped returncodes, then no other active original-DB consumer. A created/unstarted helper or missing/reap-failed/unobservable proof blocks recovery. Any STOP UNCONFIRMED receipt latches halt: no later rename/start/retry. No implicit exception recovery. Explicit one-use recover-original preserves failed resources and may restart only through the same barrier; never restore a backup.',
    cli={mode: [sys.executable, '-P', '-B', str(HERE / 'guarded_backup.py'), '--plan', str(plan_path),
                '--execute-after-reviewed-preflight', mode]
         for mode in ['backup', 'rename-original', 'create-replacement', 'start-replacement', 'recover-original']})
assert not plan_path.exists()
plan_path.write_text(json.dumps(plan, sort_keys=True, indent=2) + '\n', encoding='utf-8')
print(json.dumps(dict(prepared_only=True, path=str(plan_path), sha256=hashlib.sha256(plan_path.read_bytes()).hexdigest(),
                     executable_sha256=sources[str((HERE / 'guarded_backup.py').relative_to(ROOT)).replace('\\', '/')],
                     lifecycle_sha256=sources['tooling/foundation/analysis_lifecycle.py'])))
