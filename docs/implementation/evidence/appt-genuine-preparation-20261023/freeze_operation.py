"""Generate a review packet from committed procedures; never operate Docker."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
assert Path.cwd().resolve() == ROOT.parents[3]
PREFIX = "remission-poc13-ac8e16e0"
SERVICE = PREFIX + "-service"
BASE = "41056f0c06a2afa1141c33eeb3a934a1969d19bb"
IMAGE = "sha256:a950cdb0dd9b3bbdeb176c6da71903180406a9bf2160ea3d23faf4be3c0f5e72"
OLD_IMAGE = "sha256:bad33f377d97f52572e182d0973b1f1f56dbc3f1c413de48f20b0458e0906fb7"
OLD = PREFIX + "-service-pre-appt-410"
BACKUP = PREFIX + "-appt-backup-410"
FAILED = PREFIX + "-service-failed-appt-410"
PRIVATE = str((Path.cwd() / "artifacts/appt-genuine/private-maintenance-20261023").resolve())
ENVFILE = str(Path(PRIVATE) / "replacement.env")
COMMON = ["--cpus", "2", "--memory", "2g", "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--tmpfs", "/tmp:rw,noexec,nosuid,size=128m", "--user", "10001:10001"]


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def literal_assignment(path, name):
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    return next(ast.literal_eval(n.value) for n in ast.walk(tree) if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == name for t in n.targets))


def save(name, data):
    path = ROOT / name
    assert not path.exists(), str(path)
    path.write_text(data if isinstance(data, str) else json.dumps(data, sort_keys=True, indent=2) + "\n", encoding="utf-8")


maintenance = Path("docs/implementation/evidence/pa3-service-maintenance-20261022")
terminal = Path("docs/implementation/evidence/pa3-native-terminal-20261022/terminal-database-readonly.json")
reference = json.loads(terminal.read_bytes())
sql = literal_assignment(maintenance / "audit_pa3_native_readiness.py", "SQL_AUDIT")
# Retain the accepted transaction/projection/table-hash audit. Do not emit any
# session/key-derived receipt hashes. Full receipt rows remain covered by the
# existing aggregate protected-table hashes.
receipt_start = sql.index("receipts=[]")
receipt_end = sql.index("control=db.execute", receipt_start)
sql = sql[:receipt_start] + "receipts=[]\n" + sql[receipt_end:]
extension = '''
result=json.loads(row['result_json']) if row['result_json'] else None
trusted=json.loads(row['progress_json']).get('trusted_launch')
out['terminal_attempt']={'id':row['job_id'],'patient_id':row['patient_id'],'status':row['status'],'stage':row['stage'],'started_at':row['started_at'],'finished_at':row['finished_at'],'failure_reason':row['failure_reason'],'result_status':result['status'] if result else None,'result_canonical_sha256':sha(result) if result else None,'trusted_launch_sha256':sha(trusted),'owner_matches_expected':row['owner_id']==patient['owner_id']=='alice'}
control_all=dict(db.execute('SELECT * FROM service_control WHERE singleton=1').fetchone())
out['control_clock_at']=control_all.pop('last_receipt_at')
out['control_except_clock_sha256']=sha(control_all)
out.pop('panel')
out['attempt'].pop('numerical_seeds')
out.pop('receipt_identities')
assert out['database_control']==EXPECTED_CONTROL
assert out['terminal_attempt']['owner_matches_expected']
assert row['status']=='completed' and row['stage']=='complete' and result['status']=='completed'
assert sha(result)==EXPECTED_RESULT
assert sha(trusted)==EXPECTED_TRUSTED
assert out['attempt']['immutable_identity_sha256']==EXPECTED_ATTEMPT
assert actual==row['input_sha256']=='3761da9e876d3830106e5edc47a7b5b930764f934facc95c8b6328b84e65e5a2'
assert sha(projected)==row['history_sha256']=='ce5a5a2bbf99405d2457654791f3ac9a263f669770b075ac1dfa1cff0f4ac00c'
assert not out['queue'] and not out['running']
assert out['query_only']==1 and out['total_changes']==0
'''
bindings = "\nEXPECTED_CONTROL=" + repr(reference["database_control"])
bindings += "\nEXPECTED_RESULT=" + repr(reference["terminal_attempt"]["result_canonical_sha256"])
bindings += "\nEXPECTED_TRUSTED=" + repr(sha(reference["terminal_attempt"]["trusted_launch"]))
bindings += "\nEXPECTED_ATTEMPT=" + repr(reference["attempt"]["immutable_identity_sha256"]) + "\n"
end = "db.rollback();db.close();print(canonical(out))"
assert sql.count(end) == 1
sql = sql.replace(end, bindings + extension + "\n" + end)
ast.parse(sql)
save("readonly-terminal.py", sql)
backup = literal_assignment(maintenance / "maintain_pa3_service_once.py", "backup_code")
assert backup.count("/backup/remission-pre-pa3.sqlite") == 1
backup = backup.replace("/backup/remission-pre-pa3.sqlite", "/backup/remission-pre-appt.sqlite")
ast.parse(backup)
save("stock-backup.py", backup + "\n")
create = ["docker", "create", "--name", SERVICE, "--label", "remission.task=" + PREFIX,
          "--network", PREFIX + "-app", "--publish", "127.0.0.1:8780:8765", *COMMON,
          "--restart", "no", "--workdir", "/app"]
for suffix, destination, readonly in [("database", "/data", False), ("exports", "/exports", False), ("fixtures", "/fixtures", True)]:
    create += ["--mount", "type=volume,source=" + PREFIX + "-" + suffix + ",target=" + destination + (",readonly" if readonly else "")]
create += ["--env-file", ENVFILE, IMAGE, "python", "-m", "uvicorn", "services.foundation.server:app", "--host", "0.0.0.0", "--port", "8765", "--no-access-log"]
source_paths = [maintenance / "maintain_pa3_service_once.py", maintenance / "audit_pa3_native_readiness.py",
                maintenance / "verify_pa3_continuity_once.py", Path("tooling/foundation/capture.py"),
                Path("services/foundation/cli.py"), Path("services/foundation/store.py"), terminal]
sources = {str(p).replace("\\", "/"): {"bytes": len(p.read_bytes()), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in source_paths}
save("operation-binding.json", {
    "task_id": "APPT-GENUINE-POSITIVE", "status": "PREPARED_ONLY_REQUIRES_FRESH_ASTRA_REVIEW_AND_ROOT_GO",
    "base": BASE, "source_override": BASE, "old_image": OLD_IMAGE, "new_image": IMAGE,
    "service": SERVICE, "retained_service": OLD, "failed_replacement": FAILED,
    "backup_helper": BACKUP, "private_root": PRIVATE, "temporary_envfile": ENVFILE,
    "predecessor_source_bindings": sources,
    "database_audit_argv": ["docker", "exec", SERVICE, "python", "-c", sql],
    "maintenance_argv": [
        ["docker", "stop", "--time", "10", SERVICE],
        ["docker", "run", "--name", BACKUP, "--network", "none", *COMMON,
         "--mount", "type=volume,source=" + PREFIX + "-database,target=/data",
         "--mount", "type=bind,source=" + PRIVATE + ",target=/backup", OLD_IMAGE, "python", "-c", backup],
        ["docker", "rename", SERVICE, OLD], create,
        ["docker", "start", SERVICE]],
    "rollback_stock_argv_when_applicable": [
        ["docker", "stop", "--time", "10", SERVICE],
        ["docker", "rename", SERVICE, FAILED],
        ["docker", "rename", OLD, SERVICE],
        ["docker", "start", SERVICE]],
    "private_environment_handling": "Reuse predecessor private subprocess inspect in memory only, no capture/stdout/values/digests; preserve every entry and override exactly REMISSION_SOURCE_COMMIT to base. Reject duplicate keys/newlines. Before stop, privately compare effective proposed environment including new image defaults; reject unexpected differences. Temporary envfile only in owner+SYSTEM ACL directory; remove envfile after create. Report count/preservation booleans only. No dispatcher field is added or changed.",
    "credential_input": "After fresh review/root GO only: same narrow RO owner/username lookup and AST literal DEMO_PASSWORDS from current CLI; selected owner alice only. Ordinary /api/session and /api/login. API keeps credentials/cookies/CSRF in memory only. For MCP UI, if necessary write one-task JSON to same ACL directory, open isolated file:// tab, read into browser memory without returning body, close tab before filling main UI, never snapshot credentials, no trace; clear visible password on failure. No credential/token/cookie values or digests in evidence/Git/tool code.",
    "limits": {"inspect_or_audit_seconds": 20, "stop_command_seconds": 30, "backup_seconds": 60, "health_deadline_seconds": 25, "service_cpu": 2, "service_memory_bytes": 2147483648, "service_tmpfs_mib": 128, "restart": "no", "bind": "127.0.0.1:8780", "new_fit_count": 0, "new_analysis_post_count": 0, "new_authority_or_data_volumes": 0},
    "gates": ["Recheck exact initial metadata and absent prospective names/path; only service active on original DB; no active worker/dispatcher launch.",
              "Execute frozen RO audit once; compare every protected table to committed terminal snapshot, exact original control/inodes/request/result/trusted-launch/H* and owner. Any discrepancy stops before maintenance.",
              "Privately prove selected source override is sole environment difference; no private environment streams or digests captured.",
              "Prepare owner+SYSTEM private directory; verify effective ACL before secret/backup writes. It must be new and ignored.",
              "After stopping service verify clean exit0/notOOM and no active DB consumer. Verify SQLite online backup integrity and every protected-table count/hash before rename/create. DB mount RW exists solely for WAL/shm bookkeeping; source query_only and total_changes0.",
              "Before auth: same all protected table hashes, Store/control/database+lock device/inode/generation, same original result/trust and original generator selected state. Same limits/mounts/network/port/Cmd. Health must be ok within deadline.",
              "One ordinary owner login per API/browser context only. Auth may change sessions/login_attempts and monotonic control.last_receipt_at; control_except_clock hash and every protected table except service_control must remain equal.",
              "No automatic retry of backup/create/start/claim; a tool observation timeout is not terminal. Preserve same handle/failures. Stock predecessor rollback is only reviewed stop/retain replacement then original name/start against unchanged original files; never restore backup or replace DB/lock. Stop on rollback failure and retain exact state.",
              "No calls to claim/bind-execution/dispatch/ingest/refresh/approve/advance, no scientific imports on host, no posterior/NPZ reads, no cloud resource operations."]})
print(json.dumps({"prepared_only": True, "frozen_sql_bytes": len(sql.encode()), "new_source_or_runtime_operation": False}))
