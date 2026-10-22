"""Read-only by default; --write records documentation evidence, never runtime tests."""
import base64
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path.cwd()
BASE = 'ec18cb4020ba239710a3fd615e365d5cd72b4d80'
PRIOR = 'a58e022945d2077d7214d6c739f95bace41824c2'
DOC = 'docs/implementation/g1-live-hold-executable-contract-proposal-r1-20261021.md'
EVIDENCE = 'docs/implementation/evidence/G1-LIVE-HOLD-PLAN/R1/'

def git(*args, data=None):
    return subprocess.check_output(['git', *args], input=data, cwd=ROOT)

assert Path(git('rev-parse', '--show-toplevel').decode().strip()).resolve() == ROOT.resolve()
assert git('merge-base', 'HEAD', BASE).decode().strip() == BASE
source_map = json.loads(git('show', PRIOR+':docs/implementation/evidence/G1-LIVE-HOLD-PLAN/source-check.json'))
sources = [r['path'] for r in source_map['inspected_sources']]
sources += ['services/foundation/cli.py', 'services/learner/worker.py',
            'services/learner/export_observed.py', 'contracts/domain/boundaries.py',
            'contracts/domain/observed_v2.py', 'contracts/runs/admission.py']
inventory = []
for p in sources:
    b = git('show', BASE+':'+p)
    old = git('rev-parse', BASE+':'+p).decode().strip()
    assert git('rev-parse', 'HEAD:'+p).decode().strip() == old
    inventory.append(dict(path=p, git_blob=old, bytes=len(b), sha256=hashlib.sha256(b).hexdigest()))

preserved = []
for item in json.loads((ROOT/EVIDENCE/'preserved-inputs.json').read_bytes()):
    b = base64.b64decode(item['raw'], validate=True)
    assert len(b) == item['bytes']
    assert hashlib.sha256(b).hexdigest() == item['sha256']
    assert git('hash-object', '--no-filters', '--stdin', data=b).decode().strip() == item['git_blob']
    assert b == git('show', item['git_blob'])
    preserved.append({k:v for k,v in item.items() if k not in ('raw','encoding')})
assert any(r['git_blob']=='03113df759da826fb7da91a2ffa179228e022121' for r in preserved)
assert any(r['git_blob']=='3e133ea52bf2732ac785424ffe7f30f257332633' for r in preserved)

original = 'docs/implementation/g1-live-hold-executable-contract-proposal-20261021.md'
assert git('show', PRIOR+':'+original) == git('show', 'HEAD:'+original)
changed = git('diff', '--name-only', PRIOR).decode().splitlines()
for path in changed:
    assert path == DOC or path.startswith(EVIDENCE), path
subprocess.run(['git','diff','--check',BASE], cwd=ROOT, check=True)
links = re.findall(r'\]\(([^)]+)\)', (ROOT/DOC).read_text(encoding='utf-8'))
for link in links:
    if '://' not in link:
        resolved = (ROOT/DOC).parent / link.split('#')[0]
        assert resolved.exists() or resolved.resolve() == (ROOT/EVIDENCE/'doc-check.json').resolve(), link

result = dict(base=BASE, preserved_original_candidate=PRIOR, scope='documentation only; no self-critique/runtime result',
              source_files=inventory, raw_preservation=preserved, relative_links_checked=len(links),
              original_proposal_git_bytes_unchanged=True, ledger_git_bytes_unchanged=True,
              changes_outside_repair_scope=[], diff_whitespace='passed', runtime_tests=False,
              note='CRLF raw source-check and LF committed source-check retained separately; no bytes relabeled.')
if '--write' in sys.argv:
    (ROOT/EVIDENCE/'doc-check.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
print(json.dumps(dict(status='passed', source_identities=len(inventory), preserved_raw_objects=len(preserved),
                     relative_links=len(links), ledger_unchanged=True, runtime_tests=False)))
