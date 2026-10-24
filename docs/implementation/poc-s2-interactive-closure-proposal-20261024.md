# Bounded interactive support closure proposal

Status: SOURCE proposal requiring DIFFERENT Astra critique before implementation.
Base: 88aec132ad0cbf182e2fb1fc697f479477ef2e36. Owner: S2-PROD4 Sol/high,
own branch feat/poc-s2-controller-20261024. No runtime, scientific, Store or
private-data execution supplies evidence here. Existing SOURCE plan authority:
b22f75f4b263b491378c35df874953c7857cd1ce / different critique
a05f1341771e83e09fccb34e931d36bc22fad40c. Canonical requirements: SUPPORT-01,
MISS-01, PA5; OBS-REP-02; S2-CANONICAL-01/SERVING-01; APPT-02/03/05;
workflow-contract.md consent/hold/freeze/re-entry and atomicity.

## Existing seam and exact problem

Read these public files AT THE BASE COMMIT above, not changing worktree files:
services/foundation/simulation.py:persist_product/advance;
services/foundation/protocol.py:project_protocol;
contracts/domain/evidence_v2.py:validate_outcome_link;
contracts/runs/coverage_v2.py:StageLedgerV2;
contracts/runs/support_research.py:SupportCompletion/StageVerifier;
services/foundation/app.py:Settings;
services/foundation/store.py:Store.transaction.

The existing ordinary app transaction admits the generator's bounded complete
observed product, checks expected delivery/report sets and rolls back on failure.
It can therefore truthfully freeze exactly the admitted delivery array under the
owned decision before asserting completion. Today it has no trusted ledger or
completion descriptor. project_protocol deliberately rejects observed burden
without a trusted verify_closure callback. Neither absence of an event nor an
ordinary event payload is an independently completed-stage proof.

Existing StageLedgerV2 identities suffice for stage/window/decision/exhaustive
delivery references. Existing OBS2 SupportStageClosureV2 and SupportOutcomeLink
also suffice; preserve their formats. A ledger alone does not establish *why*
the source completed its stage or bind a transaction, owned Store generation,
independent output and qualified producer. StageVerifier currently requires
SupportCompletion: historical research run/partition, SupportRuntime with exact
poc-support-research-map-v1 seed derivation, output file artifacts, frozen research
plan and externally qualified invocation. Ordinary interactive app is not that
invocation. Reusing those values would fabricate research equivalence.

## Smallest proposed resolution for critique

Prefer reusing StageLedgerV2 and existing OBS2 closures, and add ONLY a closed
interactive completion descriptor plus its internal verifier in sibling
controller modules. No migration, store, generic evidence framework or worker.
Persist descriptors in the existing append-only state_changes table in the SAME
serialized transaction as decision, distribution, assignment, admitted product,
closure/outcome and clock. Descriptor precedes closure. No HTTP proof/callback
or independent caller-set authority is accepted.

Proposed descriptor schema poc-support-interactive-completion-v1:
- Owned Store id + authority generation, owner, panel/generation, patient.
- Existing service-configured source commit and runtime VersionRef, controller
  configuration ref, exact decision and assignment refs, window/index/stage.
- Full separately serialized delivery-only array from actual admitted product
  (plus actual server-produced offer if modeled), its byte length/digest/count.
- StageLedgerV2 values/refs for offered and delivered; complete stage boundary,
  synthetic available-at and actual received/publication timestamps.
- Original administrative transaction/decision identity and completed status;
  no manually supplied zero count/default completion.

Completion is constructed only AFTER persist_product validates the full expected
product and typed assignments. Non-delivery/mismatching/duplicate/foreign events,
failed/partial product or missing source/runtime qualification refuse/rollback.
No pre-outcome evidence is moved backwards. Offered and delivered counts remain
separate: if no actual offer transition is recorded, offered completeness must
stay unknown; do not derive an offer event merely from a future delivery.

Trusted DB verifier reads the exact append-only payload by descriptor id/owner,
checks content-derived ref/hash, installed Settings source/runtime and Store
authority/generation, then checks ledger and bound decision/assignment/window,
complete independently serialized typed output, exhaustive matching current
owned events and lineage, and closure clocks/availability. It supplies the
existing project_protocol verify_closure seam only internally. No untrusted
request/proof can install a verifier or upgrade an archive. Qualification of
the actual app/generator source/runtime and invocation remains independently
required before its completion may authorize fitting/serving; SOURCE tests only
use labeled inert metadata/transaction doubles, never actual completion claims.

## Decision requested from DIFFERENT Astra

Choose whether a smaller existing completion contract can express the app's
producer authority without false research/runtime/artifact assertions. If not,
critique this minimal sibling descriptor/trust predicate and precise offer-stage
source, rollback/completeness/lineage/current-authority checks before author edits
that boundary. Identify how configured source/runtime qualification is bound;
Settings labels alone cannot self-qualify the producer. Keep missing qualification
explicit and fail closed, without creating another permanent OFF switch. Actual
app/Store/browser/native runs remain out of this assignment's authorization.
