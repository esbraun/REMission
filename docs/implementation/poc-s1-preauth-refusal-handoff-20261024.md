# S1 bounded pre-auth refusal — SOURCE/OP preparation

Base `ad82d6825ab4c08d1bbdaa8d5e4de4866f6cc52d`. No execution GO.
Plan `d9a1ea93e87d65f1a38b78bb3a096e266088e355` and different critique
`148328d20c1a4689761b09b397be4d178ce99a06` authorize this finite diagnostic only.
R2 actual remains confirmed stopped/failure-only (`84a68d14e51f2c35018df2c6abb4eb9968c2dec3`);
its cause, authentication, original receipt/job and current Store state are unknown.

The new R3 operation uses `s1-original-request-control-v2`, requiring nullable
`preauth_refusal`. Legacy R2 v1 records are retained without migration or reparse.
The only non-null values are the fixed ordered groups: imports, bundle_admission,
settings_load, settings_identity, original_submission, archive_binding,
auth_admission, auth_decode. Existing statements, reads and checks retain their
order; auth open/read stays in auth_decode. Ordinary Exception attempts one existing
atomic admitted/unavailable/incomplete/null-job publication, then reraises the
original exception object even if publication fails. No exception inspection occurs.
Authentication-before publication, TestClient and subsequent auth/snapshot work
remain outside this catch. BaseException, hard stop or failed publication remains
unknown. Success has null classification and exactly the original five checkpoints.

Host decoding requires the exact new field set, plain-string enum and failure-only
placement; no exception values, messages, types, locals, traceback or private data.
Whole-module AST inverse restores the accepted base after only this transport/schema
delta and R3 namespace/path literals. Existing binding/submit functions, query logic,
cutoffs, eligibility, session/control/auth/UID/mode guards and successful body remain
unchanged. Guarded actual-function tests exercise all eight failures, exception
identity, publisher faults, success order/three auth calls, BaseException/outside
boundary, atomic emission, strict decoder and inverse: 37 PASS. Retained suite:
53 PASS. Both run with native/network/science/app/Store/SQLite tripwires; no runtime.

Fresh namespace `remission-s1-original-reconcile-261024-r3`, named control
`/data/s1-p3-original-reconcile-r3/control.json`. Fresh nine-input packet is frozen
under `artifacts/s1-preauth-refusal-ad82-r3/final-packet`; exact hashes/command/index
are ignored public evidence, not execution permission. Current independent SOURCE/OP
reviews and fresh root exact-once GO are external metadata. No reservation is made.

Existing 900 outer/840 common work/870 wait/60 setup/180 auth/2 reap and
2CPU/2GiB equal swap/PID64/UID10001/RO root/netnone/dropALL/NNP/tmp128 noexec/lognone
remain. Setup60 does not separately guarantee the entire prearm interval.
Strict acquired-CID typed config/resources/mounts and live owned PID/CID/nonce/deadline
ACK before start, typed terminal/all known reaps/independent final remain mandatory.
Controller collection follows workload stop, attach/watchdog reaps and controller
independent container final; its bounded file client then reaps before controller
terminal. Outer parent reaps controller and independently reconfirms role final.
Missing custody means STOP_UNCONFIRMED/no collection. Nonzero/late remains failure.
Named JSON<=4096 and transport<=20480 before parsing; no failed-stream recovery.

Original request/key/owner/full12/day84/config/references/SQL limits and readonly
WAL/control/session checks remain; no analysis POST/new key/export/history/claim/fit.
Snapshot absence proves no absence of earlier effects. Image4c293 is a composite
selected-source proof, not a whole-current-main image claim: normal auth ASTs match
the accepted old baseline; explicit shared S2 differences are documented separately.
New mounted driver/helpers/public manifest/authority are hash bound. Private auth
is a path-only prospective input; actual private metadata, WAL/JSON capabilities,
current presence and operational feasibility remain unknown. No private host read,
SQLite, app, scientific import, real child, Docker or network operation occurred.

Requirement/task/test evidence: finite preauth classification -> eight-group actual
function test; privacy/placement -> strict schema and sentinel controls; original
failure precedence -> identity/publisher/BaseException tests; unchanged success and
legacy behavior -> ordered success and complete-module inverse; lifecycle/caps ->
retained 53 and exact helper/SQL/source byte proofs. Independent review and fresh GO
are required. Frozen STOP, no self-approval or downstream authority.
