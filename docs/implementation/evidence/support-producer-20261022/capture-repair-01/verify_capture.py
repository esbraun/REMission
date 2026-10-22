"""Stdlib-only assertions over the actual repaired UNIT capture; no Docker calls."""
import ast
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[5]
FOLDER = Path(__file__).resolve().parent
HARNESS = 'docs/implementation/evidence/support-producer-20261022/run_unit_batch.py'
PRE_REPAIR = 'b5b170d0bb065d35cbff5c0fe3872702c0ce04fe'


def read(name):
    return json.loads((FOLDER / name).read_bytes())


def no_environment(value):
    if isinstance(value, dict):
        assert not {'Config', 'Env'}.intersection(value), value.keys()
        for child in value.values():
            no_environment(child)
    elif isinstance(value, list):
        for child in value:
            no_environment(child)


capture = read('container-terminal.json')
command = read('command.json')
ready = read('watchdog-ready.json')
watchdog = read('watchdog-terminal.json')
result = read('result.json')
cid = (FOLDER / 'cid.txt').read_text().strip()
assert re.fullmatch('[0-9a-f]{64}', cid)
assert set(capture) == {
    'Id', 'Image', 'State', 'User', 'WorkingDir', 'ReadonlyRootfs', 'NetworkMode',
    'NanoCpus', 'Memory', 'MemorySwap', 'PidsLimit', 'CapAdd', 'CapDrop',
    'SecurityOpt', 'Tmpfs', 'Mounts',
}
no_environment(capture)
assert capture['Id'] == ready['cid'] == watchdog['cid'] == result['cid'] == cid
assert capture['Image'] == 'sha256:ce346feace2ae607ebd574e1bb681d594c9b676c06b56f8ba8d50b858a577faa'
assert capture['User'] == '10002:10002' and capture['WorkingDir'] == '/src'
assert capture['ReadonlyRootfs'] is True and capture['NetworkMode'] == 'none'
assert capture['NanoCpus'] == 2_000_000_000
assert capture['Memory'] == capture['MemorySwap'] == 2_147_483_648
assert capture['PidsLimit'] == 64 and not capture['CapAdd']
assert capture['CapDrop'] == ['ALL']
assert capture['SecurityOpt'] == ['no-new-privileges']
assert capture['Tmpfs'] == {'/tmp': 'rw,exec,size=512m,mode=1777'}
assert len(capture['Mounts']) == 1
mount = capture['Mounts'][0]
assert mount['Type'] == 'bind' and mount['Destination'] == '/src' and mount['RW'] is False
assert mount['Propagation'] == 'rprivate'
assert 'type=bind,source=' + mount['Source'] + ',target=/src,readonly' in command['argv']
for setting in ('OPENBLAS_NUM_THREADS=1', 'OMP_NUM_THREADS=1', 'MKL_NUM_THREADS=1',
                'NUMEXPR_NUM_THREADS=1', 'PYTHONDONTWRITEBYTECODE=1', 'PYTHONSAFEPATH=1',
                'PYTENSOR_FLAGS=base_compiledir=/tmp/pytensor,floatX=float64'):
    assert setting in command['argv']
state = capture['State']
assert state['Status'] == 'exited' and state['ExitCode'] == 0
assert not state['Running'] and not state['OOMKilled'] and not state['Error']
assert command['watchdog_seconds'] == ready['seconds'] == 300
assert datetime.fromisoformat(ready['armed_at']) < datetime.fromisoformat(state['StartedAt'])
assert result['elapsed_seconds'] < 300
assert result['attach_returncode'] == result['watchdog_exit'] == 0
assert result['container_exit'] == '0' and result['retained_stopped_container'] is True
assert watchdog['events'] == [{'terminal': state}]
assert 'Ran 1 test in ' in (FOLDER / 'terminal.stderr').read_text()
assert (FOLDER / 'terminal.stderr').read_text().rstrip().endswith('OK')

# Check the actual subprocess boundaries, rather than redacting a broad capture.
tree = ast.parse((ROOT / HARNESS).read_bytes())
formats = []
for node in ast.walk(tree):
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'TERMINAL_INSPECT_FORMAT' for t in node.targets):
        terminal_format = ast.literal_eval(node.value)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'run' and node.args and isinstance(node.args[0], ast.List):
        values = node.args[0].elts
        if len(values) >= 2 and all(isinstance(v, ast.Constant) for v in values[:2]) and [v.value for v in values[:2]] == ['docker', 'inspect']:
            assert isinstance(values[2], ast.Constant) and values[2].value == '--format'
            formats.append(values[3])
assert len(formats) == 2
assert terminal_format == command['terminal_inspect_format']
assert '.Env' not in terminal_format and not re.search(r'\.Config\s*}}', terminal_format)
for path, digest in command['source_sha256'].items():
    assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path

# Preserve all historical raw files. The historical manifest's old harness entry
# deliberately continues to identify its pre-repair bytes, not today's harness.
historical = json.loads((FOLDER.parent / 'raw-manifest.json').read_bytes())
entries = historical['sources'] + historical['evidence']
assert len(entries) == 132
for entry in entries:
    raw = (ROOT / entry['path']).read_bytes()
    if entry['path'] == HARNESS:
        raw = subprocess.check_output(['git', '-C', str(ROOT), 'show', PRE_REPAIR + ':' + HARNESS])
    assert len(raw) == entry['bytes'] and hashlib.sha256(raw).hexdigest() == entry['sha256'], entry['path']

summary = dict(
    version='support-capture-repair-verification-v1', passed=True, cid=cid,
    schema_keys=sorted(capture), full_config_or_env_captured=False,
    pre_capture_formatted_inspection=True, source_associations_checked=len(command['source_sha256']),
    literal_cid_watchdog_prearmed=True, deadline_seconds=300, deadline_or_oom=False,
    historical_entries=132, historical_current_entries_unchanged=131,
    historical_harness_entry_verified_at=PRE_REPAIR, changed_historical_entry=HARNESS,
    test_scope='One existing S0/masked/randomized projection and no-leakage UNIT control; functional source unchanged; no repeated 41-control science suite.',
)
(FOLDER / 'verification.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n', encoding='utf-8')
print(json.dumps(summary, indent=2, sort_keys=True))
