# Synthetic assessment intrinsic fact mapping R0

**UNACCEPTED bounded shared-contract proposal. No dependent assessment or review implementation is authorized by this document.**

Author assignment: gpt-6.1-sol / xhigh; difficult integrated version, exact-reference, and likelihood boundaries. Effective model introspection is unavailable; no model substitution was made. Author source checkpoint: `01d4528af9f4c466e27f92ac0a1fb0ebc156bac7`, seeded by accepted verification `83481b29315b21baa4a7fa29fb8eba6e2658b84f`, integration base `0e1a11faa01d267fe1cdb06d07c0c06dcc2d5b55`.

## Accepted clauses and bounded question

The accepted scientific PLAN is exact `5409d54f570040b435a729769ba2d9353b7daffb`, [full proposal](g1-clearance-burden-contract-proposal-r1-20261021.md), Git blob `e5a67a4ad7e37b82cb591226e6b522d767f59db8`, SHA256 `87e5b95f93f97d2beb19bef9ac159c8293655589c637668b948ff69ac39d17b5`. Independent ready-plan report: `5e020233cb78c30a63f57122cebb5e69f81704fc`; full raw payloads and manifest are preserved by [the current raw manifest](evidence/G1-CLEARANCE-BURDEN-CONTRACTS/accepted-plan-raw-manifest.json).

Section 3.1, source lines 41 and 43, places both per-obligation status entries with exact observed fact references and the new binary measurement `within_synthetic_stability_limit` in `SyntheticEligibilityAssessmentV21`. Threshold status is satisfied iff the current qualified boolean is true, unsatisfied iff false, unknown if absent or stale. The same clause limits the measurement to one likelihood indicator and excludes numeric L/U and private seeds. Section 3.3, lines 78–80, requires the entire current episode/generation/obligation union, exact source prefix, next-local-date review, and subsequent exact assessment references. Section 3.4, line 88, denies archive evidence any LIVE authority. Existing public reference representation is `ExactRef(record_id, payload_sha256)` in `contracts/domain/observed_v2.py`; `payload_hash` and exact resolution are in `contracts/domain/evidence_v2.py`.

The question is how a threshold status names a measurement inside its own assessment without embedding that assessment's own payload hash. A self-ExactRef would require the assessment's hash to contain itself. A second measurement record kind would add an interface absent from the accepted PLAN. This proposal supplies one closed intrinsic selector in addition to ordinary external exact references. It does not add a record kind, a latent field, a rule, or LIVE permission.

## Proposed closed shape and interpretation

The assessment has a required nullable field `within_synthetic_stability_limit: bool | null`. Boolean input is strict: integers, strings, and other coercions are invalid. Null records an absent measurement and cannot satisfy threshold clearance. Each per-obligation entry retains its accepted obligation ID, reason, exact rule VersionRef, status, and `fact_refs: list[ExactRef]`, and adds:

```json
{"intrinsic_fact_fields": ["within_synthetic_stability_limit"]}
```

`intrinsic_fact_fields` is a required, duplicate-free list with length at most one, whose only permitted literal is `within_synthetic_stability_limit`. It is a field selector in the containing committed assessment, never a record ID, JSON pointer, arbitrary property path, external lookup, or alternative to `ExactRef`. Unknown selectors and additional fields are refused. An external `fact_refs` entry naming the assessment's own record ID is refused, regardless of supplied hash. Duplicate external references are refused.

For an active threshold obligation identified by its exact qualified SIM-REVIEW rule binding, the selector must be exactly the singleton above. The boolean determines its status: true requires `satisfied`; false requires `unsatisfied`; null requires `unknown`. An inconsistent status is malformed. An active threshold obligation cannot be `not_applicable`. The intrinsic selector does not replace the exact obligation, entry source, rule, episode/generation union, or committed source-prefix proofs required by the accepted law. Actual external facts needed by that rule remain ordinary `fact_refs`; the threshold boolean itself needs no external self-reference.

All other obligation entries must have `intrinsic_fact_fields: []`. Their statuses use ordinary exact external facts under their declared rule: admission/discharge, current registered schedule and explicit supersession chain, or a materialized arm-local concern script with its actual occurrence and obligation. Satisfied/unsatisfied/not-applicable claims require the rule's complete actual external evidence and explicit condition; an empty evidence set cannot serve as permissive satisfaction. Unknown may represent missing applicable evidence. Missing expected entries remain unknown at union qualification. No omitted entry or selector discharges an open obligation.

## Committed closure, clocks, and later use

This is a value inside one immutable public record. Its authority is that containing record's exact payload, qualified source header, law binding, run/partition/patient, local assessment date, actor, exact current source-prefix VersionRef, and complete episode/generation/obligation union. The assessment's external references must have exact membership in their actual qualified committed package/prefix. Each recursive dependency needs its own patient/scope, source, exact hash, committed publication sequence, and admissible clock proof. Aggregate current-head lookup cannot supply missing package membership or stamp one root receipt onto every dependency. Retractions, corrections, unknown rules, missing records, and mismatched scope fail closed under the accepted rule. Historical immutable assessments remain historical after a dependency changes; current clearance cannot reuse them as current qualification.

The existing Record chronology and accepted local 09 subphases remain: events and schedules precede assessment, which precedes review/readiness/assignment. Equal-clock ancestry is established only through the committed prefix's publication order. The assessment cannot cite itself or a later review, snapshot, assignment, or successor prefix. Subsequent `HoldReviewEvidenceV21` uses the ordinary exact reference to the now-committed assessment, with the accepted script/source-prefix and union references. A review cannot substitute the intrinsic selector for that exact assessment reference. Earliest review remains the next local date after entry; resumption remains a later fresh assessment and all other accepted gates. No learner strict-cutoff rule is relaxed by equal-clock ancestry.

The threshold measurement contributes its one indicator likelihood at its qualified measurement node. Selecting its field from a status entry, publishing a review, and publishing a snapshot contribute no second likelihood. No numeric latent coordinate, U, seed, private result, or clinician signature is introduced. Archive resolution cannot clear the LIVE1.0 latch, install the separately planned LIVE2.0 rule, restore consent, or authorize treatment. The current LIVE threshold policy stays blocked.

## Concrete controls required before code acceptance

Positive: a qualified committed assessment A at current local 09 has boolean true, a complete current prefix and active threshold obligation O, status satisfied, singleton intrinsic selector, and actual external obligation provenance. A later review references `ExactRef(A.id, hash(A))`. Hashing A does not depend on its own hash; the later review's hash depends on A in the ordinary acyclic direction.

Cycle counterexample: putting `ExactRef(A.id, hash(A))` into A's own status `fact_refs` makes the purported exact hash depend on itself. It is rejected by record ID before resolution; choosing an old or arbitrary hash does not rescue it. No special self-hash exception or unhashed field is allowed.

Required repeatable controls cover strict true/satisfied, false/unsatisfied, null/unknown; absent required field; true/unknown and false/satisfied inconsistencies; wrong rule or obligation; missing expected obligation; threshold empty selector; non-threshold intrinsic selector; unknown/duplicate selector; numeric/string boolean; self-ExactRef and forged hash; malformed/duplicate external refs; missing/stale/corrected/retracted/cross-package/foreign-patient dependency; equal-clock committed predecessor positive and future/uncommitted predecessor negative; changed generation and source-prefix rejection; valid later exact review; and one-likelihood/no-LIVE-authority preservation. They must distinguish schema shape, contextual exact closure, and current qualification rather than accepting a shape-only fixture as producer authority.

## Review disposition requested

Independent critique should accept or reject this exact narrow field mapping, including its explicit clarification of section 3.1's intrinsic versus external fact reference. All accepted5409 equations, status laws, clocks, union requirements, versions, resource gates, and source restrictions remain in force. Until independently accepted by root, the dependent assessment/review seam stays unwritten; unrelated accepted report, burden, and precision work may continue. Public contract implementation and finite fixtures are not stochastic engine, calibration, scientific, clinical, or LIVE-policy acceptance.
