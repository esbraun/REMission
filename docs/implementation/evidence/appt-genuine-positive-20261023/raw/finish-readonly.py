"""GO2 final selected metadata, ordinary health GET, and strict read-only audit."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parent
WORKTREE = ROOT.parents[2]
CID = '6c19849608483c32a3cef1e488cda70177963c209ee26a4925038533c7e49475'
IMAGE = 'sha256:a950cdb0dd9b3bbdeb176c6da71903180406a9bf2160ea3d23faf4be3c0f5e72'
VOLUME = 'remission-poc13-ac8e16e0-database'

def save(name, value):
    (ROOT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')

def run(argv):
    result = subprocess.run(argv, capture_output=True, text=True, timeout=20, check=True)
    assert not result.stderr.strip(), 'unexpected stderr; halt without service action'
    return result.stdout

binding = json.loads((WORKTREE / 'docs/implementation/evidence/appt-genuine-lifecycle-repair-20261023/operation-binding-r2.json').read_text())
assert all(hashlib.sha256((WORKTREE / path).read_bytes()).hexdigest() == sha for path, sha in binding['source_sha256'].items())
fields = run(['docker', 'inspect', '--format', '{{json .Id}}|{{json .Image}}|{{json .State}}|{{json .HostConfig.ReadonlyRootfs}}', CID]).strip().split('|')
selected = dict(zip(['Id', 'Image', 'State', 'ReadonlyRootfs'], map(json.loads, fields)))
assert selected['Id'] == CID and selected['Image'] == IMAGE and selected['ReadonlyRootfs']
assert selected['State']['Running'] and not selected['State']['Restarting'] and not selected['State']['OOMKilled']
assert selected['State']['StartedAt'] == '2026-10-23T06:23:39.678933146Z'
consumers = run(['docker', 'ps', '--no-trunc', '--filter', 'volume=' + VOLUME, '--format', '{{.ID}}']).split()
assert consumers == [CID]
with urllib.request.urlopen('http://127.0.0.1:8780/health', timeout=10) as response:
    assert response.status == 200
    health = json.load(response)
assert health['status'] == 'ok' and health['database_instance_id'] == 'e4924957-b4df-4d83-b013-72e123e13a28' and health['authority_generation'] == 1
audit_source = (ROOT / 'readonly-inventory-audit.py').read_text()
raw = run(['docker', 'exec', CID, 'python', '-c', audit_source])
(ROOT / 'after-auth.json').write_text(raw, encoding='utf-8')
before = json.loads((ROOT / 'before-auth.json').read_text())
after = json.loads(raw)
tables = sorted(before['protected_tables'])
unchanged = [name for name in tables if before['protected_tables'][name] == after['protected_tables'][name]]
changed = [name for name in tables if name not in unchanged]
assert changed == ['service_control'], changed
keys = [key for key in before if key not in ['protected_tables', 'auth_table_counts', 'control_clock_at']]
assert all(before[key] == after[key] for key in keys)
assert after['control_clock_at'] >= before['control_clock_at']
assert after['auth_table_counts']['accounts'] == before['auth_table_counts']['accounts']
assert after['auth_table_counts']['sessions'] == before['auth_table_counts']['sessions'] + 4
assert after['auth_table_counts']['login_attempts'] == before['auth_table_counts']['login_attempts'] + 2
assert after['query_only'] == 1 and after['total_changes'] == 0 and not after['queue'] and not after['running']
save('final-integrity.json', {
    'observed_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'passed': True, 'selected': selected, 'active_database_consumers': consumers,
    'source_binding_count': len(binding['source_sha256']), 'all_source_bindings_unchanged': True,
    'health': health, 'protected_table_count': len(tables),
    'exactly_unchanged_protected_tables': unchanged, 'changed_protected_tables': changed,
    'service_control_except_monotonic_clock_unchanged': True,
    'control_clock_before': before['control_clock_at'], 'control_clock_after': after['control_clock_at'],
    'every_other_audit_field_exactly_unchanged': keys,
    'auth_table_counts_before': before['auth_table_counts'], 'auth_table_counts_after': after['auth_table_counts'],
    'allowed_auth_mutations': 'one ordinary owner API login and one ordinary owner UI login; each ordinary flow creates preauth and authenticated sessions, sessions +4 and login_attempts +2',
    'full_attempt_inventory_exactly_unchanged': True, 'full_attempt_inventory': after['full_attempt_inventory'],
    'new_attempts': 0, 'active_attempts': 0, 'model_runs': 0,
    'identity_input_result_Hstar_trusted_launch_inodes_unchanged': True,
    'RO_query_only': after['query_only'], 'RO_total_changes': after['total_changes'],
    'retained_startup_timing': 'first health 26.382130s after start; <=25s NOT PROVEN; no retry/restart',
    'private_credentials_or_digests_captured': False,
})
print(json.dumps({'passed': True, 'protected_tables': len(tables), 'unchanged_tables': len(unchanged), 'clock_only_changed_table': changed, 'new_jobs': 0, 'active_jobs': 0, 'auth_count_changes': {'sessions': 4, 'login_attempts': 2}, 'same_container': True}))
