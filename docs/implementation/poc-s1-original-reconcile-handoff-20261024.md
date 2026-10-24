# S1 original-request reconciliation — source/operation preparation

Base: accepted `ff0fb3f03220772e4512a337b3cc4afb53c7cce3`. Source preparation
only; no private query or runtime permission. Plan
`6490848815b796231d97cd07855cb39c6760f22b` and DIFFERENT critique
`fc914a42e1ad5a409e3b1f1122943f05c5d84ac9` govern this fixed mode.

## One original request, no replay

The new `S1_ORIGINAL_REQUEST_RECONCILIATION_V1` mode and namespace
`remission-s1-original-reconcile-261024-r1` use the original public specification
`a92f061741cf283e4bc5cf4f46a94979acf0731e`: same owner, Store/generation,
archive/export/admission, stable key, S1/day84/twelve-member request and
`previous_attempt=None`. The packet freezes the actual scalar S1Submission
normalization, CONFIG_REF and model/prior/estimand/law/protocol references from
the unchanged contracts. The original request is not reconstructed from current
outcomes or abandoned private files. No analysis POST, replacement key, guessed
job, list/owned-view, prepare/revalidate/history/export, claim, fit, initialization
or account creation is called. Old submit and binding functions are inverse-AST
identical outside the declared mode dispatch/receipt-name/label selections.
The old binding `selected_owner` empty-queue guard is unchanged; the new mode
explicitly admits only a consistent original queued attempt.

Normal GET session, CSRF-protected POST login, GET session establish the expected
owner. These use normal authentication transactions: session creation/revocation,
login-attempt accounting and ordinary control-journal/WAL bookkeeping may write.
This operation is not globally read-only. Credentials/cookies/session hashes
remain inside the container. The new selected read subsequently uses URI
`mode=ro`, verified query_only before SELECT, ordinary WAL visibility, the existing
AdmissionGate with existing writable lock/flock, and complete Store.validate_control
(including validate_bundle, schema/bindings/generation and DB/lock identity).
Validation occurs before BEGIN, inside BEGIN and before release. Authentication
is checked inside that snapshot and again before rollback/close: token-hash
lookup, exact owner, non-revoked, finite unexpired expiry, matching account
auth_version. This is snapshot-bound, not future revocation immunity or zero OS
writes. No Store.__init__/normal connect is used for the selected query.

## Closed SQL and outcomes

The accompanying SQL contract freezes the actual SQL strings and per-field
bounds. The source map `17da1a2aad7504e7a172c12d32062ffe744ddfa3` covers receipt
PK `(owner,session,key)`, pending/attempt shapes, response projection and cohort
overlap. Cross-session owner/key lookup permits at most one receipt (LIMIT2 and
overflow refusal), exact original scope/payload identity, response text <=131072
bytes verified before parsing, and original response/job identity. It never
publishes the private response. The selected job/pending projections compare
schema3/kind/purpose/owner/archive/run/cohort/day/config/reference/cutoff and
ordered twelve members with exact S1 partitions. Claim/start/result are booleans;
request_json/result_json/history/claim-token values are never returned. Member
versions are positive metadata, not current-input/H* verification.

At most two competing active overlaps and corresponding pending metadata are
materialized (LIMIT3/overflow refusal); another job, orphan pending row or
malformed/inconsistent identity is conflict. Existing running/completed/failed/
abstained states are reported without reset. No receipt plus no active conflict
means only `receipt_absent_at_snapshot`, never proof of no POST/effects/rollback.
SQLite JSON functions have an exact in-snapshot capability predicate and fail
closed; no broad-payload fallback. LIMIT bounds returned rows, not database CPU.
The fixed common deadline remains authoritative. Actual SQL/API/WAL feasibility
is UNKNOWN until a separately reviewed operation.

Public schema `s1-original-request-control-v1` has only finite phase/status flags,
optional verified original job_id and existing closed job state. Every result
states metadata_only=true/current_input_validated=false/submit=claim=fit=false.
No owner/session/key, history, private input/H*/DB/credential digest or raw error
is output. Matched queued metadata permits planning only a separate exact-job
full export/current-input validation. No outcome authorizes another POST or fit.

## Checkpoint, custody, bounds and packet

The new mode alone atomically publishes <=4096-byte `control.json` checkpoints
before/after authentication and before/after the snapshot in a fresh private
0700 operation directory. Same-directory exclusive 0600 temporary publication
checks regular type/owner/link count; no raw exception output or old file recovery.
Its sole named transport retains <=20480 bytes BEFORE tar parsing/closed JSON.

Ordering is explicit: controller collection follows workload terminal, strict
live prearm evidence, attach/watchdog reaps and the controller's independent
stopped-container final. The collecting file client is then reaped before the
controller terminal. The outer parent subsequently reaps the controller and
reconfirms independent container final before ACTUAL promotion. It would be
impossible to claim controller/file-client reaping before controller collection.
Missing or inconsistent workload custody yields STOP_UNCONFIRMED/no collection.
Read/parse/missing checkpoint remains unavailable; collection never turns a
nonzero/late/timeout into success or masks its primary failure. No collection on
unconfirmed stop, old output/stdout/stderr fallback, or new observer exists.

Unchanged prospective caps: 900 outer/840 common work/870 wait/60 setup/180 per
auth request/2 reap, 2CPU/2GiB equal swap/PID64/UID10001/ROroot/netnone/dropALL/NNP/
128MiB noexec tmpfs/lognone. Setup60 is not a universal full-prearm syscall bound.
Only retained volumeRW/public five-leaf carrierRO/exact auth-fileRO mounts.
Literal CID typed-created resources/mounts/argv, live exact OWNED PopenPID/CID/
nonce/deadline ACK before start, terminal PID0/exit/OOM/restart, known reaps and
independent final remain mandatory. Shared lifecycle helpers are byte-identical.

Container-only auth is proposed regular/single-link/current-UID, mode without
group/other permissions, <=65536 bytes; bundle regular/single-link/current-UID,
not group/other writable, <=1MiB. Actual bind metadata/presence is UNKNOWN and
refused if unavailable. No host auth/DB/private-file stat/read/hash occurs.
The exact existing auth path is a future mount string only. No abandoned
intent/response/selection/export is accessed even inside this operation.

Image4c293 is the accepted composite with old selected S1/session source, not
whole current ff0 packaging. Shared app/analysis S2-only differences are explicit
under accepted inverse `485fba1445a018713b78635a74e8c3f28babab53`; the packet
compares exact selected old-image/current S1 functions and unchanged dependencies.
Public authority437547 (699480 bytes/SHA048960...) and manifestf77700d (43963/
SHAa762...) are exact Git inputs; no 103MB archive mount or artifact fallback.

## Requirement/task/test delta and limits

| Existing requirement/task | Source verification |
|---|---|
| S1 app integration / original request | actual scalar typed normalization, legitimate pending, unique receipt/absent/duplicate/identity/state/overlap negatives |
| APPT-SAVED-READ-01 prerequisite | metadata-only closed result; no serving/current-input authority |
| Auth/ownership/admission | expiry/revocation/auth-version/control/archive/member/partition/query-only/rollback-close controls |
| Failure/persistence/custody | atomic publication faults, fixed-name/size/privacy, post-stop collection, no collection on missing reaps, primary failure/absolute deadline/resource mutations |
| Regression | 53 retained guarded source controls; full old-function inverse outside explicit mode dispatch |

26 new and 53 retained guarded controls PASS, zero skips. The initial retained
global enabled-expression count failed because a new mode now has its own check;
it is narrowly scoped to the unchanged original run. An initial inverse checker
omitted the explicit reconcile-boolean dispatch; its test-only failure is retained.
All logs are indexed. No actual SQLite/app/Store/science/native/network/private
operation ran. Canonical methods/contracts/services/UI and old runtime evidence
are unchanged. Different exact SOURCE/OP review and fresh root GO remain required.
Genuine WCLS/ingest/saved-result/browser/study/clinical gates remain pending.
