# S2-PROD4 Repair2 SOURCE handoff

FROZEN SOURCE REPAIR, pending the SAME independent Astra full-source re-review.
Exact source candidate **d1042620df29b535068f0ada6890903f1dfab469**, tree
**cf391b1b41578d98115716b5b3b2b03cab074a1d**, parent/repair base
**a8c96b3d3d1ec95deaac97f0ca882486888e8fb1**. Production base remains
**88aec132ad0cbf182e2fb1fc697f479477ef2e36**. The enclosing evidence-only commit
adds this packet without changing those source blobs. No source self-acceptance,
merge, push, PR, reservation, operation GO or actual qualification.

Exclusive checkout C:/Users/erics/Documents/Projects/REMission-worktrees/
s2-controller-sol-261024; branch feat/poc-s2-controller-20261024. Assigned
gpt-6.1-sol/high, no model override, escalation or helpers. Primary and other
worktrees preserved. No additional skill; no UI edit in this repair.

## Findings and bounded repair

Independent review **e80cae850fdd2343cf3bc982d130eca611b22ec3**, checks
**6ce6ffe044d9c8982b034bda44ec9c40d341a299**, index
**9174967e0baa57d72ced92311e64aae578d028c6** verified all57 existing source
controls and the earlier repairs, then found two unmet existing workflow
requirements. Its actual-source/inert repro script
**0c3716710f6ee68f3e0089951a3fe10c69d1d0c0** / log
**5bb3f8b0cf799cab3220958618f710c256a2f54b** reproduced successful withdrawal
without a task and stale_or_not_visible_dependency on withdrawal -> advance and
withdrawal -> renewal without approval -> advance. Exact public prior review,
checks/index, repro and log are retained in this repair evidence folder; previous
failed candidates, Repair1 review and chronology-failure logs remain unchanged.

Only three source paths change from the repair base:

- services/foundation/simulation.py: the two prepared S2 advance branches now
  require support_controller.status == active as well as the retained snapshot.
- services/foundation/support_s2_controller.py: withdrawal creates an owned
  pending review task in the existing transaction and returns its task_id.
- tests/test_s2_controller_source.py: actual-source/inert producer, ordinary
  continuation, task reader/replay/rollback regressions and a generalized labeled
  exhaustive observed-product double for ordinary day/visit advancement.

**P1:** withdrawal, renewal without fresh approval, and pause retain their prior
envelope and immutable histories but no longer enter decide/derive authorization
through that obsolete envelope. The unchanged ordinary simulation path admits
the already approved behavioral background deliveries and new observed reports,
advances the fictional clock and creates the current decision. It does not draw,
assign, offer, deliver or create support decision/outcome closure for the disabled
component. Consent validation and execution authorization remain strict; no old
approval is revived or substituted. A fresh explicit current envelope is required
for S2 reentry. Clinical/independent holds, death and active/stopped/completed N
routing remain before ordinary/S2 selection. Inactive support never bypasses the
N path; active post-N reentry still requires its exact explicit N review identity.
Ordinary, N, V and S0/S1 source behavior retains the existing inverse evidence.

**P2:** withdrawal persists the real consent revision and real state_changes
command, then inserts one pending task owned by patient.owner_id. Its payload
contains trigger support_consent_withdrawal, immediate fictional due_at, current
decision_id, command_id, the exact withdrawn consent reference, rationale and an
explicit ordinary-care/fixed-support review purpose with no support approval.
Candidate task IDs use the existing producer namespace and payloads carry the
exact candidate invocation reference. The existing after_follow_up fault seam
runs before patient version/state update and create_decision. The enclosing
serialized transaction commits task, command, consent, versions and current
decision together or rolls them back together. Existing owned stable receipts
return task_id on replay; stale commands fail before another task insertion.

## Legacy task anchor and readers: explicit review point

The unchanged tasks table in migrations/001_foundation.sql stores bundle_id as
non-null TEXT **without** a foreign key to bundles. Existing ordinary approval
tasks use an actual approval bundle there. This withdrawal task instead uses the
real persisted withdrawal command ID as its anchor, and exposes that same ID as
command_id in its payload. It is **not** an approval bundle, a fresh human
approval, or a new entry in the historical approval-bundle list. No bundles row
is fabricated, no historical display is repurposed and no schema/migration is
added. ROOT authorized preparing this minimal truthful interpretation for review;
that authorization is not independent source acceptance.

The existing GET /api/tasks/{task_id} joins tasks to the current owned patient and
returns the payload. The current patient workspace selects tasks by its already
owned patient and displays due_at/owner/pending follow-up. Neither reader resolves
tasks.bundle_id as an approval bundle. Historical readers query the bundles table
directly and receive no withdrawal pseudo-bundle. Source inspection found no
existing task-anchor dereference requiring an approval bundle. The guarded
actual task-reader body resolves the new payload, rejects another owner and
the existing workspace task-list SQL retrieves it. Real browser/authenticated
HTTP and SQLite constraints were not executed. Future consumers must distinguish
this explicit command anchor; independent Astra must assess these semantics and
compatibility, not infer approval from the legacy column name or ROOT's steer.

## Checks and retained failures

Final **repair2-r5:62 PASS,0 FAIL,0 expectedFailures**, 16.947s. All previous57
normal controls remain. New controls exercise the real consent/approve/advance/
withdraw and renewal commands, real simulation.advance and persist_product,
history/create_decision, Store.transaction, owned mutation receipt/route and task
reader bodies. Only I/O and unavailable runtime edges are inert labeled doubles.

1. Withdrawal -> day16 ordinary continuation, withdrawal -> renewal -> day16,
   pause -> day16 and renewal-only -> day16 preserve all prior records/snapshots,
   add only continuing behavioral delivery/report, retain disabled status, and
   make no new support draw/assignment. LIVE and renamed/rehashed candidate
   history remain rejected; the original linked provenance is not relabeled.
2. Day15 withdrawal -> ordinary day16 -> renewal -> visit day28 -> new explicit
   approval -> S2 day29 exercises commands between review dates and after the
   ordinary review transition. Exactly two support decisions/draws occur, at
   day14 and day28; renewal alone supplies no support authorization. This uses
   honest saved fallback, not a claim of applicable genuine fitted predictions.
3. Actual outer simulation branches still refuse clinical/independent holds or
   death with their expected reason and preserve active/stopped/completed N
   routing. No unauthorized advancement is hidden by a generic stale exception.
4. The actual owned support-command route calls the real withdrawal transition,
   replays its saved receipt without duplicate task, and rejects a stale new key.
   The task resolves its existing decision, exact consent revision and real
   persisted command, retains owner/candidate provenance, and the actual owned
   task reader denies a foreign owner. This injects a principal; it does not test
   session authentication or claim real HTTP execution.
5. Fault after task insertion rolls back consent/command/task/history/current
   versions/decisions/clock and app receipts. The external candidate once receipt
   remains consumed and cannot be replayed, as in the existing candidate design.

Run history is retained, not overwritten: r1's new fixture assertions incorrectly
renamed the provenance marker and used the pending task as a hold trigger; r2
corrected them and passed60. r3 added task regressions before the completed task
implementation and expected APIError where the isolated actual route propagates
SimulationError to the existing app exception layer; it failed, as retained.
r4 passed62 after task implementation/assertion correction. r5 strengthened the
hold/death/N assertions to exact reason branches and passed62. Intermediate logs
are diagnostic history, not qualifications of the final source commit. A
PowerShell unquoted HEAD^{tree} metadata query also failed and was corrected with
quoted arguments; no source or passing test was affected.

The final packet verifier initially rejected copied prior-review blobs because
the checkout's default text filter normalized their original CRLF bytes. Two
narrow .gitattributes patterns now preserve this repair's prior-* artifacts and
raw repair2-r*.txt process captures. Exact original review/repro Git blobs and raw
capture bytes are verified after staging; source files and other artifact rules
are unaffected. This evidence preservation edit is part of the enclosing packet.

The approved isolated source interpreter ran -I -B with ACTIVE scientific,
app/services/Store/SQLite, private/sealed filesystem, Win32, process and network
tripwires. No actual app, SQLite/Store, scientific library, generator law, native
worker, browser, current-resource query, Docker, private data, credential/ACL,
cloud, network operation or fitting ran. These are source controls, not the
integration/browser tests required for eventual runtime acceptance.

## Full source closure and inverses

source-closure.json binds all17 source paths by exact raw Git blob/byte SHA256;
checkout CRLF identities are recorded separately. Generated schema
**ed39e96d928885f87aff5fc158357c530ee4aebf** and config
**fdd717fa52495b0e99e00c209824bebc3d0d42a4** are byte-identical to Repair1.
Four focused binary reverse patches applied to an isolated temporary index
restore contracts/services/methods/tests/web/tooling source trees to production
base with zero remaining changed source paths. Eighteen protected objects
including science/data/model/N/research/generator/learner source match base.
Store.py, app.py and every other production source path except the two listed
are byte-identical to the repair base. Function inventories and guarded inverses
preserve ordinary/N default connection and transaction behavior, existing
ordinary support validators, legacy typed histories, generator product admission
and all undeclared function bodies. Task schema/readers remain unchanged.

The entire web tree is still
**dfe12f933f90f15e9cedb56d34ea7441fe273404**, with unchanged schema/config; prior
typecheck/build PASS evidence is reused only for those exact bytes. No TS rerun,
dependency install, lock change, dependency write or browser claim. Previously
observed Node24.19 is not equivalence to historical Node22 qualification.

The full unchanged source chain remains: actual current consent/envelope ->
current authority/mask -> saved scalar or named .5 fallback -> bounds/normalized
final vector -> persisted decision -> one purpose-keyed assignment -> actual
20:00 dispatch recheck -> unmodified observed generator admission -> acyclic
stage/output ledger/completion/outcome -> clock/current decision. Original
envelopes and as-known histories remain immutable. Candidate and installed closed
contexts remain distinct; all LIVE history/project_protocol/export/prediction
consumers retain derived administrative authorization proof and semantic candidate
nonpromotion. Repair1 dispatch expiry, journal before_commit lifetime/revocation/
generation checks, postcommit fresh read/output withholding and consent lineage
chronology/same-clock/reentry controls remain passing and their source unchanged.

## Remaining actual work and STOP

All executable/serving gates stay OFF; no extra permanent OFF gate was added.
SOURCE acceptance, even if independently granted later, cannot install actual
qualification. The reachable existing non-HTTP candidate harness still requires
an exact independently supplied SOURCE+OP packet/GO and consumed receipt under
trusted launcher custody; hashes identify that authority, never create it. The
acyclic sequence remains immutable source/image/config/Store packet -> separate
SOURCE/OP GO -> untrusted candidate outputs -> different ACTUAL acceptance ->
typed installed qualification -> a SEPARATE new installed LIVE roundtrip. There
is no candidate history transplant, self-attestation, HTTP bypass or fake ACTUAL
acceptance reference.

Real Store/SQLite integration, operator launcher/image installation and current
authority, genuine applicable fit/artifacts/saved prediction/serving roundtrip,
browser/auth/task presentation, N/S controller qualification, seven-configuration
study and cloud/release remain pending separately scoped exact SOURCE+OP+fresh
GO. Genuine fitted delayed/multiple activation/reactivation/corrected contexts
remain pending versioned scientific/data applicability work or independently
reviewed requirement resolution; fallback source coverage does not waive them.
Protected numerical evidence remains **17/18, one FAIL**, unchanged and not rerun.
The sealed-input line140 assertion remains FAIL; no new exists/stat/read/hash or
mutation, no relabeling green. Frozen STOP for same independent full-source
Astra re-review; no actual operation is authorized by this packet.
