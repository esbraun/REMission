# S2 interactive qualification bootstrap amendment

Status: PROPOSAL FOR DIFFERENT ASTRA CRITIQUE. No new bootstrap type, context,
harness or validator seam is implemented. SOURCE preparation only; no runtime GO.
This supplements accepted PLAN r1, proposal blob
36eed1737bd8d8895d5d87118f15b0e615073c58, critique
a90252d10f73a04ee8e234db2434f1c5e93f1432, checks
f4c5021d3f02c9cac515b5a3d72dc7448050b342, index
d93635aa33a8ba904d55d3167e7f251b06b807cf. It does not claim acceptance of the
partial implementation. Production base: 88aec132ad0cbf182e2fb1fc697f479477ef2e36;
previous partial checkpoint: 3ce3764be91d5c8515e2cd555b854829c3cdfc7b.

Canonical requirements: docs/spec/05-support-learning.md SUPPORT-01/MISS-01;
docs/implementation/poc-analytics-contract-20261021.md S2-CANONICAL-01,
S2-NUMERICS-EMPIRICAL-01 and SERVING-01; docs/spec/poc-amendment-20261021.md
POC-2/3, APPT-02/03/05 and PA7; docs/implementation/workflow-contract.md
current authority, consent/hold/N freeze, explicit reentry and atomicity.
SOURCE/OP acceptance cannot substitute for actual producer evidence.

## Exact gap and existing producer

Current public source blobs: support_s2_controller.py
257c53e5cccb65fd244e378825a03669b01f36c7; support_s2_authority.py
aff2fa5d5ad0602daa4654ca0e350520a9b1ccb6; store.py
c33650711e3fc06266f067fcd1e3e1f612a793ab; simulation.py
b7f1d51d2485487040af13c316752903319b57f1; workflow.py
0dafed2f671ed18b93c28232a859dce7e8f120f6; protocol.py
e7e5a0639f7d3c880b3b8063d08382c39070fe0a; domain/support_s2_controller.py
e18784feb7da107ecb8ef74b706757309c18ba29. Service paths are under
services/foundation; the domain path is under contracts. These are PARTIAL2
source identities, not qualified image identities.

Existing simulation.advance selects the prepared S2 branch; controller.advance
calls decide -> dispatch -> existing product/persist_product -> close_stages ->
clock/create_decision inside existing Store.transaction. Every interactive
authorization/completion currently calls qualification(db), which accepts only a
typed installed InteractiveSupportQualification containing later ACTUAL acceptance.
persist_product calls LIVE workflow.history. Therefore an isolated invocation
without that later acceptance cannot emit candidate evidence. SOURCE fixtures with
UNIT-FAKE references do not resolve this gap and grant no runtime authority.

## Bounded proposed entrypoint and authority

Add one closed immutable UntrustedInteractiveInvocation, containing the ALREADY
frozen QualificationPacket plus its digest, separate exact SOURCE acceptance and
bounded OP invocation-GO VersionRefs, and invocation identity. It has NO
actual_acceptance, installed-qualified scope or promotion method. The externally
reviewed OP packet must bind the exact candidate commit/source closure, app and
generator images/runtime/config, invocation class, isolated existing Store instance
and control generation, installed bundle identity, owned synthetic case identities,
allowed operations/clocks, output location and lifecycle/resource bounds. Those
actual identities are frozen later by ROOT's separate OP process; none are invented
or queried now. GO and acceptance are external review artifacts, never assertions
supplied by app HTTP, product JSON, worker metadata or a Settings label.

Only a small non-HTTP qualification harness, invoked under that separate exact
SOURCE/OP GO, may construct the candidate context at trusted Store construction.
It uses the existing Store/SupportConnection/transaction and generation checks in
an isolated ordinary simulation Store; no schema migration or new persistence
layer. Its constructor rechecks the packet, external invocation binding and current
Store/control/source/runtime match. Installed LIVE construction remains the existing
typed InteractiveSupportQualification path. Ordinary/N construction stays NONE
and keeps its original connection call. A candidate object is never accepted in
Settings.support_qualification and cannot be installed as a LIVE binding.

Extract only the common prepared S2 producer operation behind two CLOSED internal
contexts: InstalledInteractiveContext and UntrustedInteractiveContext. LIVE app
entrypoints retain require_executable and strict installed qualification; they
cannot select the candidate constructor. The bounded harness invokes the same
decide/dispatch/product admission/close/clock core through its candidate constructor,
after its distinct OP-GO check, without pretending the deployment execution gate
or serving gate is open. This is the single candidate qualification entrypoint,
not an app flag, alternate scheduler/service or general registry. No arbitrary
callback or duck-typed context can replace authorization. Scalar fixtures can test
this plumbing; they cannot authorize an ACTUAL run or qualify scientific predictions.
The harness also exercises the same command/consent/original-envelope transition
core with the declared owned synthetic actor and explicit case inputs; it cannot
fabricate a basis/approval row to skip the envelope producer. Any necessary internal
create_decision/history call uses the same closed context. This does not qualify
HTTP authentication or browser behavior; those require the later separate roundtrip.

The narrow necessary history seam is a private closed context selection at existing
persist_product admission, and the shared S2 producer's own internal history calls.
Candidate validation uses the same ordinary validators plus envelope/current-state
derivation, exhaustive output/stage/clock checks and candidate context binding.
LIVE workflow.history remains installed-only. No public optional verifier is
accepted from the request or generator. Review should reject any implementation
that lets this seam enter ordinary app callers or weaken legacy validation.

## Namespaces, nonpromotion and acyclic evidence

Use candidate-only namespaces for invocation, authorization, administrative
execution, decision/assignment, offered transition, preclosure output, ledger,
completion, closure and outcome identities (prefix candidate-s2-), while retaining
original ordinary consent/envelope identities. Candidate completion binds the
candidate invocation reference, never a qualified-installation ref or fake ACTUAL
acceptance. Namespace and typed-context consistency are validated at every link.
The candidate OBS2.1 record structures may reuse unchanged ordinary formats;
candidate identity does not assert LIVE admission or historical research equivalence.

LIVE workflow.history, project_protocol, service export_histories, prediction
current_sources/fit and serving admission MUST explicitly reject candidate family
identities/proof references, including orphan candidate administrative records and
candidate records lacking proof. Generic ordinary validators alone cannot admit
them. The harness collects raw candidate bytes/ledger/transaction evidence as
externally inspectable UNTRUSTED artifacts through its own bounded output, never
the LIVE history/export/fit/serving API. Copying candidate artifacts into LIVE
storage must fail; no relabel, promotion, candidate receipt ingestion or fixture
authority is provided.

Order: immutable SOURCE/image/config/Store packet -> different SOURCE acceptance
and exact separate OP invocation GO -> UNTRUSTED same-producer candidate outputs
and rollback/current-generation evidence -> different ACTUAL evidence acceptance
-> trusted installed object with the original immutable packet digest and LATER
actual_acceptance ref -> a separately scoped installed-LIVE roundtrip. No object
self-hash, downstream ref in the upstream packet, fabricated acceptance or receipt
backdating. Candidate use demonstrates only candidate execution; later LIVE
roundtrip must actually re-exercise installed authorization/consumers/transaction,
not reuse candidate records as accepted LIVE history.

## Required SOURCE checks and deferred ACTUAL evidence

Before source freeze: both closed contexts reach the SAME producer transaction;
candidate runs with no ACTUAL ref; missing OP/changed packet/Store/generation refuses;
forged Settings/HTTP/product/duck contexts refuse; candidate artifacts are explicitly
rejected by every LIVE consumer; installed context still rejects absent/mismatched
ACTUAL binding; no legacy/N/research-validator change; all offer/output/completion/
outcome/clock boundaries roll back; no RNG for zero/one eligible action; no fit or
serving authority follows from candidate output. Include malicious namespace and
cross-context substitution tests, not only successful constructor tests.

This amendment is a source feasibility decision only. Actual Store/SQLite/image/
generator execution, independent inspection, trusted installation and LIVE/browser
roundtrip remain separately unexecuted. Existing S2 gates remain OFF. No additional
permanent OFF gate, framework, cache, scheduler or backend is proposed. Different
Astra should accept or request a narrower wiring before implementation resumes.
