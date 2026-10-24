# S2-PROD4 Repair1 SOURCE handoff

Disposition: FROZEN SOURCE REPAIR, pending the SAME independent Astra re-review.
No source self-acceptance or runtime authority. Exact repaired source candidate
**5a17897d6a9e1fe7db1ae6e47187d3e8dd3b19c3**, tree
**705f8d4256e26975202d5bd324a51ea3c7eb337c**; reviewed repair base
**837abdbb40c69c1fa4b2be8b2e189e06b5e5bb36**; production base remains
**88aec132ad0cbf182e2fb1fc697f479477ef2e36**. The enclosing evidence-only commit
adds the repair handoff/index/proofs without changing those source blobs.

Own exclusive checkout/branch remain s2-controller-sol-261024 /
feat/poc-s2-controller-20261024. Assigned Sol/high, no model override, effort
escalation, helpers, merge/push/PR or other checkout edits. No additional skill.
The earlier source handoff and failed candidate are preserved as history; this
document supersedes their current correctness claims for the repaired behavior.

## Review findings and exact bounded changes

Independent SOURCE report **b5ec20e691b712a25dded65f360ac8a9ce44abfe**, checks
96904824491e83980643c9a0754f699615967c3c, index
9b766d69912a4561cdfafb8e62a828c616f20526 requested two P1 repairs. Reviewer
counterexamples 601cd7d337f04f30f7e0c0246d8816f8b614c463 / log
27d71a207e1509bab318b41b57625c0d4f944dda remain retained public evidence, not
erased or relabeled actual execution. They reproduced source behavior under
inert guarded fixtures; the earlier45 controls did not cover these cases.

1. **Dispatch-time authority.** controller.authority now contains the existing
   permission/consent/hold/readiness/N restrictions separately from burden.
   mask calls it at the noon decision time and retains the original predecision
   feature/burden history. dispatch keeps that noon mask and separately evaluates
   authority at actual simulated20:00, intersecting restrictions before offer or
   schedule admission. Expiry at16:00 or exactly20:00 cancels; expiry just after
   20:00 remains valid at the offer instant. Effective withdrawal, hold, N freeze
   and pause restrict dispatch without redrawing. The immutable noon decision,
   final probabilities and keyed assignment stay intact. Canceled future schedule
   is removed and audited; no offered event or observed offered/delivered burden
   closure is invented. The current pending assignment never counts against
   itself through a shifted burden cutoff.
2. **Invocation finalization and output admission.** run_candidate supplies
   context.check to the EXISTING Store.transaction before_commit seam. The check
   runs after live_journal.receive and before commit. Late expiry/equality, GO or
   receipt revocation, or generation change rolls back the write and returns no
   evidence; the once receipt remains consumed. After a successful write
   finalization, admit_output rechecks external authority/receipt/lifetime and
   obtains a FRESH ordinary read-only Store transaction to check current Store/
   generation/owner/case, final current versions and snapshot. It never reuses
   the closed candidate connection. Authority is checked again after that read
   finalizes. Postcommit failure raises explicit
   candidate_committed_output_withheld and emits no successful evidence; the
   committed write remains committed, with no false rollback/refund claim.

Store.py is BYTE IDENTICAL to reviewed837abdb. No generic transaction redesign,
new framework/phase, scheduler/cache/backend, app/HTTP bypass or permanent OFF gate
was introduced. External GO hashes remain identity, not permission: independently
supplied exact SOURCE/OP authority and trusted launcher custody are still future
operation prerequisites. Candidate artifacts remain untrusted and all LIVE
history/projection/export/fit/serving nonpromotion remains enforced.

## Directly related consent-lineage extension

The real later withdraw/renew producer regression exposed another failure: later
commands advanced event_at while incrementing one same-event consent lineage.
This failed unchanged validate_lineage during create_decision. ROOT requested
proposal **9913b82e271e97427c164e152a758250d007e56f**, bound to unchanged
transition at837abdb/controller blob48354dca1ef33751c6a583c3d4deef918c42203b and
boundaries blob1f83d0cb20e11a8954d0455cd26a7e63fb9b702a. DIFFERENT Astra
accepted this narrow PLAN ONLY in **b8e1317505c2c29c6fc7f287dbd6aac89dac6c8a**,
checks317e4ae001950f4d1de1252bb37deae73b13aeb3, index
c029fb136e0ad29b223ff9dfcd2f2defe6391a2d before the change was implemented.

transition now selects the validated same-patient/mrt_bandit stable lineage head,
refuses component/chronology substitution, and copies only its event_at for later
revisions. New record ID/revision/exact supersedes, current recorded/available/
effective times and current withdrawal time remain; revision1 is unchanged. The
existing persist body hashes the FINAL corrected raw header. Earlier consent,
approval, snapshot, decision and distribution bytes remain immutable. Same-clock
withdraw/renew is ordered by revisions2/3, not UUIDs. Strict prior projections
retain prior knowledge; inclusive current selection uses the latest head.
Withdrawal blocks future component authority. Renewal remains unapproved and a
fresh exact current envelope is required before reentry. No generic validator,
shared schema, scientific/data or N source changed.

The typed appended-withdrawal fixture is explicitly only a dispatch-boundary test.
Separate regressions now execute the REAL initial consent/approval -> advance/
product/closure/create_decision -> later withdraw -> later renew -> fresh approval
and another advance, through existing transaction/history bodies with inert I/O.
They verify revisions2/3, same-clock order, exact versions/actor/new snapshots,
final-header raw provenance, old bytes/as-known state, zero extra draws while
withdrawn or merely renewed, and stale/expired renewal rollback/consumed receipt.
The original expectedFailure markers were removed after the fix; none remains.

This repair adds no new owned review-task or ordinary-care workflow producer.
Those existing requirements remain part of full SOURCE acceptance and are not
waived or claimed newly satisfied by the timestamp correction.

## Checks and evidence

Final **repair1-r8:57 PASS,0 FAIL,0 expectedFailures**. All original45 controls
remain included. The additional12 controls cover dispatch boundaries/current
restrictions/self-burden and canceled pending outcomes; late journal expiry/GO/
receipt/generation/exception rollback; postcommit expiry/revocation/generation/
current-version change; final read expiry; on-time distinct-connection output;
real consent revisions/reentry, stale/expired renewal and chronology/component
rejection. These are SOURCE contracts/AST bodies with typed inert I/O and
authority/transaction/generator doubles, not actual app/SQLite/atomicity claims.

Approved -I -B source-check interpreter only, with the same active scientific/
app/Store/SQLite/private-filesystem/Win32/process/network guards. No host
scientific import/computation, app/Store/SQLite, private/sealed input, native,
Docker/browser/cloud, credential/hash/ACL or current-resource operation occurred.

Evidence directory: evidence/S2-CONTROLLER-REPAIR1-20261024, including all r1-r8
attempts, final checks, frozen source closure/schema/config/function inventory,
known-lineage-failures.json, four inverse patches and protected proof. r2 had one
invalid appended withdrawal fixture correction event; the valid independent fact
remains a dispatch-only test. r4 records52 PASS plus2 real producer FAIL using
temporary expectedFailure markers and KNOWN_PRODUCER_REPAIR_PENDING status; the
observed same-event exception suffixes are preserved in known-lineage-failures.
r5 passes those corrected real producer regressions. r6 had a fixture assertion
that compared exact raw+00 timestamp bytes to Pydantic's normalized Z JSON;
the test now verifies the actual retained raw source bytes/hash and typed final
header. r7 and expanded final r8 pass. No historical failure is hidden or called
a scientific runtime result.

All17 source-closure blobs match the repaired source commit. Four fresh grouped
reverse patches in a separate temporary Git index restore ALL contracts/services/
methods/tests/web/tooling bytes to production base, with empty source remainder.
The existing AST/default connection/ordinary-N/product/validator and legacy-output
controls still pass. All18 protected Git objects remain identical to base.
Source/prose whitespace checks pass; raw logs/patch context bytes remain verbatim.

Schema/config are unchanged exact blobs ed39e96d928885f87aff5fc158357c530ee4aebf /
fdd717fa52495b0e99e00c209824bebc3d0d42a4. Entire web tree is unchanged from
reviewed837abdb. Prior Node24.19 direct TypeScript/Vite PASS logs are reused by
that exact byte identity; no unaffected TS/build rerun, install, dependency write,
lock change or browser claim. No Node22 equivalence is asserted.

Unchanged numerical **17/18 PASS, one retained FAIL** remains FAIL. It was not
rerun/repaired; baseline reproduction remains ONLY the final still-sealed
Path.exists assertion AST, not the full suite. No sealed exists/stat/read/hash/
mutation and no native GO reuse. Protected fitted delayed/multiple/reactivation/
corrected-context applicability remains pending versioned scientific/data work or
separately reviewed requirement resolution, not complete or waived.

Next is independent repaired SOURCE review. Actual SOURCE/OP packet, trusted
external authority custody, images/resources/Store/generator candidate execution,
independent ACTUAL acceptance, installation and a NEW separate installed-LIVE/
auth/browser roundtrip remain unqualified. Genuine S1/N0/N1/S2 fits/saved
prediction/serving and seven-configuration study/release remain the larger goal.
Source execution/serving gates stay OFF; no runtime GO/merge/PR. Frozen STOP.
