# Interactive support closure: narrow revision for different critique

Status: PLAN PROPOSAL, no trust-boundary implementation authorized yet. Supersedes
proposal blob 4c21de4e0489b84c356b1abd8ee36eacb276ed93; resolves the two requested
decisions in independent critique ef1a7975473d4957999a5ada151827ec36d7baed / checks
99c8f59b346b4988ed2042af5f79d8b2c2c2a48f / index
2092156b82efea641bfbaeb5e29a8a60c0d3d626. Production base remains
88aec132ad0cbf182e2fb1fc697f479477ef2e36. Accepted broader Slice4 SOURCE scope:
b22f75f4b263b491378c35df874953c7857cd1ce / a05f1341771e83e09fccb34e931d36bc22fad40c.

Canonical refs: SUPPORT-01/MISS-01/PA5, OBS-REP-02, S2-CANONICAL-01/SERVING-01,
APPT-02/03/05, workflow-contract.md consent/hold/freeze/re-entry/atomicity. Exact
unchanged base source locators: boundaries.py:validate_approval/validate_assignment;
evidence_v2.py:validate_support_decision/validate_outcome_link; protocol.py:
validate_snapshot/validate_support_v21/project_protocol; simulation.py:
persist_product/advance; store.py:Store.transaction; coverage_v2.py:StageLedgerV2;
support_research.py:SupportCompletion/StageVerifier. These paths respectively live
under contracts/domain, services/foundation and contracts/runs as at the base.

## P1 authorization resolution: explicit envelope, derived execution authority

Keep the original explicit BOTH-option Approval, its original approving actor,
the exact original approval DecisionSnapshot and immutable activation
ProtocolSnapshot. Introduce only internal `derive_execution_authorization` and
`validate_execution_authorization` in the sibling controller. No HTTP authority
input, repeated human approval, old-approval substitution or relaxed validator.

The internal producer resolves and validates exact original envelope/snapshot/
approval refs against the currently owned history using validate_snapshot. It
checks original approval purpose/options and actor against the persisted original
command/actor and current owner; it resolves the current snapshot and all four
patient/state/consent/eligibility versions and current view under the write lock.
It selects inclusive current consent lineage heads (including withdrawal and
retracted tombstones), rechecks active oversight/expiry, current independent hold
and safety state, data readiness, N block/washout snapshot and post-N explicit
review identity, then the selected eligible option/final distribution. Restriction
cannot expand original options. A changed original envelope/actor, foreign owner,
stale snapshot/versions, withdrawn consent or N mismatch refuses before draw.

Persist an immutable content-derived administrative authorization basis binding
EXACT original envelope/approval/snapshot/actor refs, current snapshot and versions,
current consent-head refs, current hold/N-policy refs, final eligible set/vector,
saved context/fit-or-fallback basis and derivation version. Per-decision OBS2.1
Approval is the existing producer-compatible administrative execution record under
that basis, explicitly not a fresh human action. Validate it using unchanged
ordinary validate_approval/validate_assignment and validate_support_v21, AND the
new narrow derivation validator. The SupportDecision.execution_receipt binds the
administrative basis; assignment/approval retain the exact current snapshot.
Deterministic no-prompt execution still requires current envelope/consent and
uses its ordinary no-prompt administrative record without RNG. No eligible action
logs unavailable/no draw, never fabricates an authorization. The current partial
source does not yet implement this complete derivation; it is not accepted.

## P1 producer qualification resolution: one independently installed binding

Add one closed immutable `InteractiveSupportQualification` schema
`poc-support-interactive-qualification-v1`, consumed ONLY as trusted installation
configuration, separate from completion and product. It contains: independent
SOURCE/OP acceptance VersionRef plus accepted packet digest; exact app/controller
and generator source closure digests/commit; installed app/generator image/runtime
bindings; controller CONFIG_REF; invocation class `owned-interactive-support-v1`;
Store instance id and authority generation; and the existing InstalledBundle
service/control generation identity. No generic registry or new persistence layer.

This is a NEW bounded qualification object; existing Settings labels do not supply
it. A later independently reviewed actual qualification packet must freeze these
values and the exact independent acceptance ref before ROOT installs it through
the existing trusted service configuration/installation path. Do not invent an
accepted ref now. App Settings may carry the typed object, but the internal verifier
constructor takes it ONLY from that trusted installed configuration and checks
current Store service/control generation and source/runtime/closure/config/invocation
against the admitted packet. Product/HTTP/worker metadata and Settings source_commit
or runtime_ref alone cannot construct, replace or promote the binding. Missing,
unqualified or mismatched independent packet/binding refuses; SOURCE fixture
objects grant no runtime authority. No new permanent OFF flag is introduced.

## Completion and actual stages

Reuse StageLedgerV2 plus OBS2 StageClosure/OutcomeLink unchanged. One small sibling
`InteractiveStageCompletion` suffices because SupportCompletion and
CompletionReceiptV2 assert research/runtime/schedule/artifact facts that are not
ordinary interactive app facts. Ledger identity alone is insufficient to bind a
qualified producer or establish stage completion. The sibling descriptor binds
the installed qualification ref, Store/owner/panel/patient, original envelope and
derived authorization, decision/assignment/window/index, separate preclosure
delivery-only output bytes/hash/count, both stage ledgers and separate simulated
completion/availability versus actual receipt/publication clocks. Store it in
existing state_changes by unique content identity; insertion/verifier rules enforce
append-only use, not a claim of cryptographic SQLite immutability.

Actual offer transition: after final distribution/draw, the server records the
selected prompt as offered at its scheduled 20:00 dispatch, immediately before
calling/admitting that night's generator product, under the existing single
transaction. This is an explicit simulated offer operation, not an inference from
assignment or subsequent delivery. If dispatch fails, all events roll back; no
offer/completion escapes. No-prompt closes a stage with no prompt only after that
real stage boundary executes. A missing offer transition stays unknown and cannot
yield observed zero. Prior holds/withdrawals/N constraints are checked before the
offer as well as draw; a now-restricted pending prompt is refused/canceled with
preserved decision history, never silently delivered.

After persist_product admits its exact full expected output, independently freeze
the typed delivery-only product/offer array BEFORE descriptor, closures or outcome.
The internal verifier requires the installed qualification binding, rechecks exact
owned descriptor/hash and stage refs, output exhaustiveness and active revision
heads, decision/authorization/assignment/window/clocks, and passes only that bound
verifier to project_protocol. All acyclic output, ledger/completion, closure/outcome
and clock/version changes commit or roll back together. Never backdate future
evidence into an earlier context. No source/qualification descriptor can turn a
partial product, missing offer, altered event or unqualified invocation complete.

Different Astra should review these two narrow choices before implementing the
new trust boundary. Required SOURCE negatives include old-envelope/actor/owner/
version/consent/N substitutions; forged Settings/product authority; unknown offer;
missing/partial/extra/foreign/duplicate output; active-head/clock substitutions;
replay and rollback at each stage. Actual installed producer applicability and
interactive round-trip/rollback, true S2 fit/prediction/draw, browser/study/cloud
and human/clinical gates remain separately unexecuted. All existing S2 execution
and serving gates remain OFF; unchanged numerics17/18 retains its one FAIL.
