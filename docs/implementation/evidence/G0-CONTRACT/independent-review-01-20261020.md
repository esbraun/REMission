# G0-CONTRACT independent review

2026-10-20. Disposition: **changes_requested**.

Reviewed head: `939dd29254bc4a6f2c4f6c92330bd1c3fc11c9d4`.
Reviewed main base: `e7965b998fa70df82e63a89ef720a6c8ad46ce6d`.
Reviewer: `/root/g0_critic_astra`, separate from Sol author, requested `gpt-6-astra` / `medium`; effective settings cannot be independently introspected. No substitution.
Exclusive checkout: `C:/Users/erics/Documents/Projects/REMission-worktrees/g0-contract-review-20261020`, detached at exact head and initially clean.

## Findings

1. **P1 - A retracted consent can authorize randomization.** `contracts/domain/entities.py:68` (`Consent.permits`) ignores inherited record_status; `contracts/domain/boundaries.py:131` selects the latest available consent without applying retraction/lineage semantics. A structurally valid consent with consent_status=active, oversight_status=approved_synthetic and record_status=retracted passes validate_approval for N-of-1. This authorizes a draw with no current usable consent record. Reproduction: load the test helper consent(), set record_status to retracted, parse Consent, and call validate_approval with the helper protocol approval/current snapshot, doctor role, time 2026-10-01T08:00:00Z and component nof1. Observed: no exception. Resolve current consent using authoritative available lineage/retraction semantics, fail closed when a retraction leaves no valid authorization, and test retracted active rows plus retraction of a previously valid consent. Do not just drop the newest row and revive superseded consent.

2. **P2 - Corrected observations cannot be represented in LearnerInput.** `contracts/domain/boundaries.py:36` requires every correction predecessor inside ObservedHistory, but `LearnerInput.only_available` at lines 66-69 requires every history record to be an active as-known record. With original R1 and correction R2, retaining R1 satisfies lineage but violates active-only learner validation. Sending only active R2 violates the required predecessor check. Both valid assembly routes fail after the correction becomes available, blocking corrected data from model requests. Reproduction uses original report(), correction report('R2', available='2026-10-03T07:00:00Z') with lineage_id=R1, revision=2, supersedes=R1, quality=3.0, and request cutoff 2026-10-05T08:00:00Z. Full lineage rejects with 'learner payload must contain only active records'; active correction alone rejects at history lineage validation. Separate validated lineage history from its active learner projection, or otherwise permit a validated projection while retaining correction provenance and excluding superseded likelihood records. Add the composition test: full history -> as-known projection -> valid LearnerInput, including earlier cutoff preservation and no double likelihood.

3. **P2 - Non-ISI estimands accept incompatible units and reversed benefit direction.** `contracts/domain/estimands.py:86-114` checks outcome/action families but only enforces units/direction for ISI and interruption vectors. EST-N1, EST-MRT and the provided quality-based EST-POLICY fixtures all accept unit=ISI_points and direction=lower_is_better. Those contracts label quality/reward effects on a different scale and reverse their interpretation despite the reference Q endpoint explicitly being higher-is-better. Reproduction: for each test helper estimand('EST-N1'), estimand('EST-MRT'), estimand('EST-POLICY'), replace those two fields and parse EstimandContract; all three were accepted. Enforce the registered endpoint's unit/direction for N1/MRT and explicitly bind policy value to its declared reward target/unit/direction; add negative tests for each registered target, not only EST-VISIT.

## Executed verification

- Read source, runner, exporter and tests before execution; inspected canonical entity/estimand requirements, temporal reference equations and the candidate's structural parent/order manifest, consumer-schema boundary explanation and evidence limitations.
- Verified root/head/base and full diff scope. No author environment or other worker checkout was used.
- The assigned checkout has no root ignore for the author's .venv-contracts/.contract-repro names. All reviewer environments/clone artifacts were instead placed beneath the already ignored `contracts/domain/__pycache__/review-artifacts/`; `git check-ignore` confirmed coverage. No ignore file was changed.
- Created an independent Python 3.13.7 venv there and installed exactly requirements-contracts.txt. Installed Pydantic 2.14.1, pydantic-core 2.50.1, annotated-types 0.8.0, typing-extensions 4.16.0 and typing-inspection 0.4.4.
- Ran `tests/contracts/run_checks.py` without --record: pip consistency, deterministic schema/dictionary export, unittest suite and ledger checker all passed. Direct `-m unittest discover -s tests/contracts -v` independently reported 24 tests, all passing.
- `git diff --check e7965b998fa70df82e63a89ef720a6c8ad46ce6d HEAD` passed, exit 0.
- The documented 24 tests include meaningful negative/cross-field cases, but omit the three compositions above; passing them does not resolve these findings.
- Ran the independent adversarial probes above in the reviewer venv. Results: both corrected-history learner representations rejected; retracted consent authorized; three incompatible endpoint unit/direction payloads accepted.

## Genuine remote reproduction

Executed `git clone --no-local --single-branch --branch launch/g0-contracts-20261020 https://github.com/esbraun/REMission.git contracts/domain/__pycache__/review-artifacts/fresh` from the assigned checkout. Clone HEAD is exactly 939dd29254bc4a6f2c4f6c92330bd1c3fc11c9d4, origin is the HTTPS GitHub URL, and .git/objects/info/alternates does not exist. No file overlay, local/shared object clone or unpublished-object transfer was used.

In that clone, `git cat-file -e` returned exit 1 for both original author commits c239dca3503c32b5e20fbd630d69f1720f9b12ce and 8315ee9d2062f04a53cd777a4891080d7c604b7d. Created a second fresh venv inside its ignored contracts/domain/__pycache__/review-venv, installed the pins, and ran the same read-only runner: all four checks passed. Thus the published-baseline repair reproduces without the unpublished commits. The checker retains canonical 635-row preservation, stable IDs, inverse references, original final acceptance, pilot/release ordering, immutable reports and merge ancestry assertions. Independently queried f986495's original planning blob: ed6985be48731e1b88fda569fed27f5a1047a371, exactly the documented original blob.

## Scope and remaining gates

The candidate preserves seven explicit estimand IDs, separate assignment/delivery/taken and workflow/view states, strict schema versions, evaluator-only export separation, missing-result states, undefined interruption denominators and suppressed overall ranking. The documentation correctly distinguishes structural JSON Schema from authoritative Python cross-field rules. Numerical/default qualification, full DGP scenario expansion, real worker artifact enforcement, persistence/auth/atomic race safety, process/storage truth denial, empirical fitting and UI remain future packages. This review ran no application, simulator, fit, statistical study, browser workflow or human session. No G0 or downstream gate is accepted; human/clinical review remains separately deferred.

Root should route findings to Sol, preserve these failed cases in meaningful regressions, and submit a new exact head/base for independent review. The prior PR10 planning acceptance does not accept these contracts. Only this untracked review report and ignored verification artifacts were written; no candidate edits, staging, commits, PRs, merges, helper spawns or lifecycle actions occurred.
