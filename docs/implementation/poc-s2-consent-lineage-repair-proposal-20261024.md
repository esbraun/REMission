# Narrow S2 consent-lineage repair proposal

Status: PROPOSAL, awaiting different Astra critique. No consent-lineage behavior
has been edited. ROOT requested this directly related extension to Repair1 after
real later withdraw/renew commands were found incompatible with the existing
same-event revision contract. The two already reviewed dispatch/finalization
repairs continue independently; an appended typed withdrawal fact tests dispatch
authority only and is NOT evidence of command-producer withdrawal/renewal.

Exact reviewed base: 837abdbb40c69c1fa4b2be8b2e189e06b5e5bb36. Unchanged
transition source is services/foundation/support_s2_controller.py, blob
48354dca1ef33751c6a583c3d4deef918c42203b, function transition, lines146-201.
Current Repair1 edits touch authority/mask/dispatch only, not transition. Unchanged
contracts/domain/boundaries.py blob 1f83d0cb20e11a8954d0455cd26a7e63fb9b702a,
validate_lineage lines33-53 requires a correction to retain event_at and extend
exactly one prior same-kind/same-lineage revision. Record.chronology in
contracts/domain/common.py lines62-69 requires revision1 iff supersedes is absent,
and event <= recorded <= available. Consent.permits in entities.py lines68-74
checks effective/expiry/withdrawal/availability at the operation instant.
workflow-contract.md line82 specifies one current lineage per component, immutable
prior facts and cessation of future assignments on withdrawal.

Current defect: transition calls record_header at the NEW fictional clock, sets
the stable support-consent-{patient} lineage and revision+1/supersedes, but leaves
event_at at the new clock. The second later consent/withdraw command therefore
fails ObservedHistoryV21.validate_lineage inside create_decision. Earlier source
checks did not run the actual later command path. This is not a scientific or
SQLite runtime observation.

Smallest proposed repair: keep the existing single component lineage, current
command/version/actor/receipt flow, revision increment and exact supersedes ref.
For a subsequent revision only, copy event_at from the ORIGINAL prior lineage
head. It identifies that same consent-state event/lineage inception. Leave the
new header's recorded_at/available_at at the CURRENT fictional command clock;
leave effective_at and withdrawn_at at their existing current-command values.
Do not alter any old bytes or timestamps, backdate availability, reset the
fictional clock, weaken validate_lineage, create an independent lineage per
command, rewrite prior snapshots or treat renewal as renewed support approval.
The first consent remains revision1 with its original event/available time.

This distinguishes later knowledge/effective state from the stable event being
revised, preserving strict as-known-then projection before the new availability
and the inclusive current head at/after it. Same-clock commands remain ordered by
the existing revision chain instead of random ID ordering. A withdrawal records
withdrawn authority, pauses the support component and stops future assignment;
renewal remains unapproved until the existing new explicit envelope/current
versions are approved. Immutable earlier decisions/distributions and original
approval/consent references remain intact in their frozen basis. Changed/revised
fitted context remains stale/unsupported under protected scientific contracts;
this proposal does not widen scientific applicability or alter generic validators.

Required regression: use the actual consent -> approve -> existing advance/
product/closure/create_decision -> later withdraw and later renew command bodies
with the existing guarded inert Store transaction, without inserting approval/
consent rows by hand. Before repair, later command must reproduce the exact
same-event lineage error and rollback while consuming the candidate invocation
receipt. After critique/repair: withdraw and renew persist revision2 (and later
renew revision3 in the combined path), retain original event_at, advance recorded/
available/effective timestamps, exact supersedes/current versions and actor,
preserve old consent/snapshot/decision bytes and strict old as-known projection,
deny draw while withdrawn or merely renewed, and require a fresh explicit approval
before reentry. Include same-clock renew/withdraw ordering and stale-version
rejection. Dispatch expiry/equality/current withdrawal and the finalization
counterexamples remain separate meaningful controls.

No schema, framework, migration, generic history redesign, scientific/N/source
contract change, runtime/OP permission or actual execution is proposed. Existing
17/18 numerical retained FAIL, source/serving OFF gates and unsupported fitted
delayed/multiple/reactivation/corrected-context limits remain unchanged.
