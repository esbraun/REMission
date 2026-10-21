"""Bind accepted base plus standalone R1 amendment without self-reference."""
from pathlib import Path
import hashlib,json,subprocess

parts=[]
for path in ['docs/implementation/g1-live-hold-executable-contract-proposal-r1-20261021.md','docs/implementation/g1-live-hold-trigger-binding-supplement-r1-20261021.md']:
    raw=Path(path).read_bytes().replace(b'\r\n',b'\n')
    blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    parts.append(dict(path=path,git_blob=blob,lf_sha256=hashlib.sha256(raw).hexdigest()))
assert parts[0]['git_blob']=='e6d39d6a0bce37a554cd768e14ee0916edf5da5c'
value=dict(contract='LIVE-HOLD-01',version='1.0.0',parts=parts,precedence='second_part_overrides_only_named_task_and_trigger_binding_clauses')
raw=(json.dumps(value,sort_keys=True,indent=2,ensure_ascii=True)+'\n').encode()
Path('docs/implementation/evidence/G1-LIVE-HOLD/proposed-composed-spec-v1.json').write_bytes(raw)
print(json.dumps(dict(parts=parts,composed_sha256=hashlib.sha256(raw).hexdigest(),disposition='proposed_not_accepted')))
