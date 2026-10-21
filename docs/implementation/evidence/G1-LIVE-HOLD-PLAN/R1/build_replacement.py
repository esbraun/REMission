"""One-shot documentation assembly; does not modify original candidate."""
import base64
import hashlib
import json
from pathlib import Path
import subprocess

root = Path.cwd()
out = root / 'docs/implementation/evidence/G1-LIVE-HOLD-PLAN/R1'
original = 'docs/implementation/g1-live-hold-executable-contract-proposal-20261021.md'
replacement = root / 'docs/implementation/g1-live-hold-executable-contract-proposal-r1-20261021.md'

def raw(ref):
    return subprocess.check_output(['git', 'show', ref], cwd=root)

preserved = []
inputs = [('original-proposal', '2483b1f93aa35a912b5e4e66c8c2b5e94caef2e4'),
                   ('full-independent-critique', '97082c7ec19fc10f1e5475df60c1a4da218ffe02'),
                   ('critic-manifest', '783e57a4738ad8c34c89292810ba606ba79ea422'),
                   ('critic-doccheck', '6008e0b2233b89a4be515b8fff26d095336966d0'),
                   ('original-raw-manifest', 'aae11a36ef157924697b0438472c48cd218a3d19'),
                   ('original-committed-source-check-LF', '3e133ea52bf2732ac785424ffe7f30f257332633')]
for item in json.loads(raw('aae11a36ef157924697b0438472c48cd218a3d19'))['files']:
    if item['raw_git_blob'] not in [ref for _, ref in inputs]:
        inputs.append(('original-raw:'+item['path'], item['raw_git_blob']))
for label, ref in inputs:
    value = raw(ref)
    preserved.append(dict(label=label, git_blob=ref, bytes=len(value), sha256=hashlib.sha256(value).hexdigest(),
                          encoding='base64', raw=base64.b64encode(value).decode('ascii')))
out.mkdir(parents=True, exist_ok=True)
(out/'preserved-inputs.json').write_bytes((json.dumps(preserved, indent=2)+'\n').encode())
text = raw('a58e022945d2077d7214d6c739f95bace41824c2:'+original).decode('utf-8')
text = text.replace('# G1 live-hold executable contract proposal', '# G1 live-hold executable contract proposal — R1', 1)
text = text.replace('2026-10-21. **T-OBS2-LIVE-HOLD-PLAN;', '2026-10-21. **Full replacement R1, T-OBS2-LIVE-HOLD-PLAN;', 1)
text = text.replace('This is the bounded executable design required',
    'This document replaces the entire original proposal; no superseded paragraph is needed to implement it. The [original](g1-live-hold-executable-contract-proposal-20261021.md) remains byte-identical at blob `2483b1f93aa35a912b5e4e66c8c2b5e94caef2e4`. The complete independent changes_requested report `97082c7ec19fc10f1e5475df60c1a4da218ffe02`, its manifest/doccheck and original proposal are preserved byte-exact in [the base64 evidence envelope](evidence/G1-LIVE-HOLD-PLAN/R1/preserved-inputs.json). Decode without newline transformation. R1 supplies a common authority/capability cutover, current authenticated review knowledge clock, and fully bound safety product/consumer contract. All are new proposals for separate critique, not acceptance.\n\nThis is the bounded executable design required',1)

def paragraph(start, new):
    global text
    first = text.index(start)
    end = text.find('\n\n', first)
    if end < 0: end = len(text)
    text = text[:first] + new + text[end:]

paragraph('Configuration is administratively installed,', '''Configuration is administratively installed, never mutable by an ordinary HTTP request. Every process is bound to the same persisted active authority/capability generation under the gate as specified below; a merely local registry digest is insufficient. Missing/revoked grants deny new operations, including retries until current authorization is valid. Removing a rule never clears an episode. No ownership-transfer endpoint is introduced; a future migration must preserve/reassign open obligations explicitly or remain blocked.''')

text = text.replace('installed manual rule VersionRef, `assessed_at`, nonempty rationale,', 'installed manual rule VersionRef, nonempty rationale,')
text = text.replace('installed manual rule VersionRef, nonempty rationale,', 'complete installed `review_rules` VersionRef list, nonempty rationale,')
text = text.replace('installed rule VersionRef. No option,', 'same complete `review_rules` VersionRef list. No option,')
text = text.replace('exact live review hash, rule hash)', 'exact live review hash, canonical review_rules-list digest)')
text = text.replace('current-assessment attestation. Creates immutable authenticated review evidence;', 'explicit current-assessment attestation for the whole active trigger/obligation set. No caller assessment/recording/availability timestamp. Creates immutable authenticated review evidence;')
paragraph('Evidence refs are typed', '''Evidence refs are typed `{store=archive|event|live_review, namespace_id, record_id, payload_sha256}`; namespace is archive ID for archived records and service patient ID for events/reviews. Archive refs also bind partition ID. Reviews bind the complete exact evidence closure, current lineage-head digest and active authority generation. The authenticated current review time is server-authored as specified in section 6; no request may supply `assessed_at` or backdate current knowledge. This inclusive current-review boundary is separate from TIME-01 strict learner visibility.''')

paragraph('Transport-arrival diagnostics,', '''Transport-arrival diagnostics, if captured, are not clinical receipt/source availability. Preserve source event/recorded/available A in archive. Mandatory supplementary `LIVE-SAFETY-EXPORT / 1.0.0`, fully specified in section 3A, carries service operational facts separately from the unchanged observed projection. Do not add a member to ObservedHistory/LearnerHistory v1/v2 or infer that their current readers accept it. Current safety folds committed operations inclusively at R; the supplementary learner product filters strictly before K. At K=R a pending current read yields busy, never ready; after commit safety is held while the new live fact remains absent at strict K=R. Archive reconstruction retains original A; a fact visible in an archive before R does not prove live-service receipt. Operational facts are neither symptoms nor extra likelihood observations.''')

text = text.replace('`live_hold_reviews`: immutable authenticated reviews with exact generation, versions, assessment/evidence/rule, actor, recorded/available clocks and hash.', '`live_hold_reviews`: immutable authenticated reviews with exact episode and authority generations, versions, server current_review_at, assessment/evidence/rule, store-specific committed-visibility proofs, actor, recorded/available clocks and hash.')
text = text.replace('future source declarations/assessment reject422', 'future source declarations reject422')
text = text.replace('assessment no earlier than required evidence.', 'current review knowledge satisfying the store-specific committed-publication rules below.')
text = text.replace('Any material patient/version/trigger/evidence change since review makes it stale;', 'Any material patient/version/trigger/evidence or active authority-generation change since review makes it stale;')

# Insert full normative sections from documentation fragments; original remains unchanged.
for marker, fragment in [('### Endpoints and request fields', 'authority-cutover.md'),
                         ('## 4. Admission, durable state and exact deltas', 'safety-product.md'),
                         ('## 7. Guard-preserving rollout and coordinator', 'review-clocks.md')]:
    text = text.replace(marker, (out/fragment).read_text(encoding='utf-8')+'\n\n'+marker, 1)

text = text.replace('Feature off until implementation/exact independent review/integrated checks accepted.', 'Feature off until implementation/exact independent review/integrated checks and section 2A deployment cutover are accepted. An off/stale worker cannot serve current authority against a LIVE-HOLD-capable database.')
text = text.replace('Source-byte evidence](evidence/G1-LIVE-HOLD-PLAN/source-check.json)', 'Source-byte evidence](evidence/G1-LIVE-HOLD-PLAN/R1/doc-check.json)')
text = text.replace('Documentation verifier](evidence/G1-LIVE-HOLD-PLAN/verify_docs.py)', 'Documentation verifier](evidence/G1-LIVE-HOLD-PLAN/R1/verify_docs.py)')
replacement.write_bytes(text.encode('utf-8'))
print(replacement.name)
