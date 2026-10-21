# Independent G0-DGP / G0-WORKFLOW R2 review

Date: 2026-10-21. Disposition: **ready_to_ship for the combined G0-DGP/G0-WORKFLOW package only**, at the exact head/base below. No unresolved blocking finding remains in this bounded contract review. The three original findings are resolved. This does not accept G0 overall, G0-LIB, G1-G7 execution, runnable UI, human-factors, clinical review or clinical validation.

Reviewed head: `985ce540f0cc6ae1e57a6268651971acb546929d`.
Reviewed accepted main base and observed merge-base: `b24c3c0fb78bf19928750eae29e852141bd649a7`.
Exclusive detached reviewer checkout: `C:/Users/erics/Documents/Projects/REMission-worktrees/g0-dgp-workflow-r2-review-20261021`.
Reviewer task: `/root/dgp_r2_critic_astra`; CODEX_THREAD_ID `01a15ec2-f67d-7522-9ade-45b236fd41bc`.
Requested model/effort: `gpt-6-astra` / `medium`. Explicit assignment is observed; this runtime exposes no independent effective-model/effort introspection. No substitution, escalation or helper was used.

## Isolation, inputs and preserved evidence

Verified assigned root, detached exact HEAD, exact accepted base ancestry and clean tracked/untracked state before work. The candidate has 28 changed/added files against the base. Domain source, canonical specifications and requirements-contracts.txt are unchanged against that accepted base. No other live checkout was accessed. Only this new untracked report and ignored artifacts inside this checkout's `contracts/dgp/.venv/` were written; no candidate edit, staging, commit, PR or merge was performed.

Read bounded entry/index, runtime/delegation/engineering instructions, scope/invariants, G0 gate and technical-plan requirements, relevant task-ledger entries, canonical DGP/reference/scenario and TIME requirements, accepted record/history/reporting interfaces, and candidate DGP/workflow source/tests/evidence. Some initial concatenated reads were truncated; the required source, timing, prior findings, scenario and workflow ranges were subsequently read separately. This is not a claim to have loaded the entire package.

Read the complete original review through Git blob `94b100b39558fce4c6c17f9f79a6acad0c159b04`, including its scenario-by-scenario critique and independent derivations. The committed R1 copy hashes to that exact blob. Read accepted TIME review blob `80f39d8512ef631249374a1378a80aeda2f74561`, covering exact TIME head `62e6ce85299b477b0c21a18d70b49392a68e1522` against `6c3fb070d36bfefbd070f2a2c33ccba7631734be`. The current base incorporates that accepted amendment. Original 43-test DGP evidence, R1 partial checkpoint/raw report and original workflow evidence are unchanged versus preserved checkpoint `2c76f4c34bc1536714f3e1988fc68da7372eb807`; verified with Git-source comparisons. R2 retains its initial two stale-version fixture errors in `first-run-failure.md`; final recorded source hashes independently match current normalized source files. Historical failure evidence was not replaced by this review.

## Finding dispositions and independent reproductions

### Original P1 S02 support-mediated non-null: resolved

Locations: `contracts/dgp/scenarios.py:13`, `contracts/dgp/parameters.py` rows L_T, stability_max_L and z_*; `docs/implementation/dgp-decisions.md` S02 interpretation; `tests/contracts/test_dgp_contracts.py:test_s02_threshold_crossing_changes_availability_but_not_outcome_law`.

R2 retains L_T=-.1 and the L>3 hold/availability rule, while setting z_L=z_B=z_prompt=z_delayed_prompt=prompt_state_gain=0. Direct behavioral and nonlinear L coefficients remain zero. Reference visit medication, rescue, interruption and irregular-visit processes remain disabled. Treatment can still alter diagnostic L, delivery/B, function/fatigue and availability, but none of those differences retains a path into the declared severity/recall/ISI law. Hold and consent constraints are not bypassed.

Independently recomputed the original counterexample: after 28 nights, paired L difference is `-.1*(1-.6**28)/.4 = -0.24999984647644463`. L0=3.05 and L1=2.800000153523555 straddle the hold threshold. The old -.08 prompt coefficient yields 14-night recall difference `-.08*sum(.5**k for k in range(14))/14 = -0.011427873883928573`; the canonical seven-item logistic tail sum gives expected ISI difference `-0.06120213724802426`. Thus the original defect was substantive.

For the repaired table, independently tested three threshold excesses (.00001, .05, .2) and three common severity baselines (-1,0,1). All nine pairs retain different availability, L and B but have identical severity transitions and ordinal expected totals; the author regression additionally compares every item/category CDF. Induction over common innovations now preserves severity equality because every varying parent has zero contribution. This is bounded structural algebra, not an executed longitudinal generator or empirical paired-trajectory run. G1 retains that full equality check.

### Original P2 unbound calibration target/purpose: resolved

Locations: `contracts/dgp/calibration.py:21` (`calibration_request`), `:107` (`require_solved`), schema 1.1.0 and calibration regression groups.

The expected request is derived from the validated authoritative cell and current DGP version. MAR/MNAR target observation probability is exactly 1-missing_fraction. External target operations use trusted separately supplied reference/pilot identities and numeric inputs; their target-specification digest includes the operation, cell, DGP identity, accepted TIME identity and all reference/pilot inputs. Retrieval compares expected fields, including target and purpose, instead of accepting the binding's self-description.

Independent reproduction constructed a valid S23.MAR_20.n60 binding with target=achieved=.8, coefficient2, 200000 sample, actual fixture hashes, MCSE .001 and ten iterations. Valid retrieval returns2. Keeping the same DGP identity and cell while replacing target=achieved=.6, or purpose=event_rate, now rejects. Unknown S99 and exact-MCAR cells reject even with internally solved-looking records. Changing only the requested DGP hash rejects. Independently derived and checked targets -.8, -.6, +1, -.6 for S10 +1SE, +2SE, reversal and S30 respectively, using reference=-1 and pilot SE=.2. Valid requests retrieve the fixture coefficient; changing either source-reference or pilot hash with identical numbers rejects for each of the four operations. Author tests also reject changed target-spec hash, missing metadata, unresolved status and changed reference contrast.

Reproduction pattern:

```python
request = calibration_request(cell_id="S23.MAR_20.n60", dgp=current_ref)
# Add schema/status/sample/seed/achieved/MCSE/coefficient/iteration/freeze fields.
valid = CalibrationBinding.model_validate(request | solved_fixture_metadata)
for update in ({"target": .6, "achieved": .6}, {"purpose": "event_rate"}):
    hostile = CalibrationBinding.model_validate(valid.model_dump() | update)
    require_solved(hostile, cell_id=hostile.cell_id, dgp=current_ref)  # ValueError
```

The consumer still must verify actual trusted external artifacts before constructing ExternalTargetEvidence. Fixture hashes and this schema do not prove a pilot or calibration ran; candidate documentation explicitly retains that G1 obligation. No achieved population rate or source shift is accepted here.

### Original P2 MAR parent arrives after reporting decision: resolved

Locations: `contracts/dgp/timing.py:33` (accepted source verification), `:81` (report_decision), `:110` (mar_offset); accepted `contracts/domain/temporal.py:25` ReportingDecision; canonical TIME-01 and reference reporting paragraphs.

The 07:00 report event now labels the prior-night outcome, not the observation decision. Separate clinical pain has event/recorded/available times08:00, source dgp-clinical-pain/version1.2.0/adapter synthetic_fhir_shaped and exact dimensionless measurement. Report decision/recording is08:01; upload delay0/1/3 days starts there. Separate wearable sync/availability is07:00 plus its own delay. The adapter requires the separate active observed pain record and composes actual ObservedHistory.project and accepted ReportingDecision validation. It does not manufacture a record from latent L or permit report-only pain. MAR coefficients remain -.4 and -.2; MNAR current unobserved quality stays evaluator-only.

Independently exercised missing pain, report-only pain, wrong source ID/adapter/version, pain arriving exactly08:01, a non-pain concept and current-report self-conditioning: all reject. With previous quality9 and observed pain1.2 the offset is `-.4*(10-9)/2-.2*1.2 = -.44`. An active correction changes previous quality4 to9; a correction arriving exactly08:01 leaves4; a subsequent active retraction removes that history and restores quality7 plus missing flag. The author tests also cover the first generated morning (latent day-15 values are not historical reports) and no-prior-history offset -.84.

Independently crossed all nine report-delay/wearable-delay combinations. At07:00 neither equal-time stream is known and08:00 pain is unavailable. At08:01 pain is known, the current report is excluded, and only zero-delay wearable is known. At09:00 the current report is known iff report delay0, independently of wearable delay. Each stream is excluded at its own exact arrival and included one microsecond later. Earlier delayed/corrected report quality is selected through active available lineage, not future/latest raw payload. The separate process identities for pain/quality/function/diary/ISI/wearable measurement, report observation, report upload and wearable upload are named and deterministic; actual PRNG draws and scheduling invariance remain unexecuted.

## Inventory, scenarios and analytic truth

Independently checked source rows against canonical equations and catalog, not only against generated JSON. The inventory remains185 parameters,73 variants,82 cells. Baseline Normal second arguments are SDs; L covariance eigenvalues are .063,.063,.144; initial states, steroid phase, B retention/gain, carryover/rebound, assignments/delivery/rescue, clipped Q/F, ordinal offsets/cutpoints/recall, diary/wearable laws and event mechanisms preserve the reference. Added descriptive distributions, optional sensitivity values, initial/irregular laws and thresholds are explicitly synthetic. Missing/altered/unknown parameter and scenario inputs fail closed. Timing adds explicit manifest/source/key semantics without silently dropping numerical rows.

| Families | R2 independent disposition |
|---|---|
| S01/S06/S07 | Reference/feedback preserved; U withheld only in S07 export, still a generative common cause. No guarantee of detectable hidden confounding. |
| S02 | Repaired sharp ISI null as above; diagnostic L remains treatment affected. |
| S03 | Continuous FIX-CONSTANT, ATE/CATE -1, fixture_points; n60/n240 catalog versus separate n200 conformance example explicitly distinguished. |
| S04/S05 | Behavioral modifier -.4*(2M-1), with L_T/z_B disabled, remains distinct from medication modifier. S05 retains prognostic .2M with zero behavioral outcome contrast; no universal constant ordinal benefit is invented. |
| S08 | Three floors and separate X>1 structural zero; unsupported population effects are not identified by clipping. |
| S09-S12 | Compatible source, separate +1/+2SE/reversal and source modifier/population shift preserved. Three lineage faults remain system fixtures. Calibration repairs above apply. |
| S13-S16 | Five block/rho and five half-life/rebound controls, two phase schedules, three adherence/stopping variants; no implicit Cartesian products. Stationary AR replaces eta. Washout remains in dynamics and outside endpoint. Horizon truncation/inconclusive and informative A/B requirements remain explicit. |
| S17-S19 | Randomized/observational linear tree fixtures are distinct from clinical-scale day28/day84 targets. True response and observed noisy/sparse eligibility labels remain distinct; X standardized under interventions. |
| S20-S22 | Prompt null removes immediate/delayed/skill paths; immediate -.08, habituation .2 and delayed harm+.15 remain separate. Excursion and complete-cohort policy values are not conflated. |
| S23-S24 | Five MCAR/MAR and three MNAR/action cells preserve targets and coefficients; accepted08:01 observed-parent mechanism resolves ordering. Action-dependent reporting retains equal true reward paths. |
| S25-S26 | Quiet-wake/device and copula/overlap/phase-item controls remain separate. Copula preserves logistic margins; shared recall already induces marginal dependence. |
| S27-S29 | Four interruptions, five system cases and frozen-versus-drifting support retained. Own-intervention conditional ISI denominators, no post-death symptoms and full support freeze are explicit. Drifting policy is a rejection fixture. |
| S30-S32 | Only +2SE/floor.01, regimen/half-life3 and admission/MAR40 compounds. Wrong propensity, infeasible bounds, missing fit and no actions remain explicit rejection/unavailability cases. |

Only S01-S05 and S20-S22 receive additional n240 cells. Analytic checks agree with independent algebra: Normal posterior mean40/81 and variance4/81; Beta(10,15); constant -1; modifier -1/+1 and marginal0; contextual values1/1/1.5. Two-period value is `.5 + .5*(expit(-1+.7*a)+expit(-.2+.7*a)) - a - 2*b`, preserving the descendant contribution. Randomized escalation values00/01/10/11 are2.4/3.6/3.6/4.4; observational standardized values add.5. Classification-noise enumeration uses true nonresponders receiving escalation. Ordinal tail sum is2 per equal item at severity0 and14 for seven regardless of dependence. Truth precision requires both absolute and relative MCSE, treats zero target SE explicitly and cap exhaustion as inconclusive. None of these computations reuses learner predictions.

## Workflow and version consistency

`workflow-contract.md:5` is the only changed substantive workflow text versus original6195 and preserved checkpoint2c76. A complete LF-normalized comparison after removing exactly the Inputs paragraph proves the remainder identical. The new paragraph correctly names accepted main b24, TIME-01 2.0.0/wire1.0.0 with exact normalized-source SHA256 `fd2fe478e1fbf5237a307af8a2067fd6d485183763086ac7e10c133fda002275`, current DGP1.2.0 candidate and additive R2 consumer evidence. It does not change state, permission, threshold or approval semantics.

Rechecked the ten ASSIGN rows, parallel state dimensions, hold/consent precedence, N1 freeze through washout, explicit ordinary-care/randomization distinction, status/undefined-outcome presentation, historical read-only mode, task/owner draft isolation and atomic/idempotent approval obligations against consumed contracts. The timing amendment remains compatible with these rules: available-at cutoff determines what the view can show; current permission/hold rechecks precede assignment. No blocking workflow finding. R2 adds no UI implementation or layout change requiring a fresh installed-UI-skill design audit; the original raw review records the applicable skill/rule inspection and its limits. This review does not upgrade that prior text-sketch inspection to rendered UI/accessibility acceptance.

DGP parameter/catalog/timing identity is1.2.0; calibration-binding wire schema is1.1.0; analytic fixtures remain1.0.0. Accepted TIME source verification uses UTF-8 source bytes with CRLF normalized to LF and no JSON reserialization. Parameters/catalog/timing and calibration target specifications bind that accepted identity. Historical TIMEv1 and accepted domain code remain unchanged.

## Observed execution and clean reproduction

Inspected runner/export/source/tests before execution. Created an own isolated Python3.13.7 environment with `python -m venv contracts/dgp/.venv`, installed exact requirements-contracts.txt pins: pydantic2.14.1, pydantic_core2.50.1, annotated-types0.8.0, typing_extensions4.16.0, typing-inspection0.4.4. No methods stack or redundant second installation was used.

Executed `contracts/dgp/.venv/Scripts/python.exe -m contracts.dgp.checks` **without --record**. All seven commands passed: pip check; DGP exports; domain exports; unittest discovery; ledger; working whitespace; full-base whitespace against exact b24. Separate discovery confirms60 passing tests:18 preserved DGP,7 new DGP timing,27 original domain and8 accepted TIME. Ran the independent adversarial script in ignored `.venv/adversarial_review.py`, with results detailed above. Its initial workflow text comparison failed because reviewer read_text used the Windows default encoding; changing that reviewer-only read to explicit UTF-8 made the complete comparison pass. No candidate change was needed. This reviewer-script failure was unrelated to the separately preserved author stale-version fixture failure.

Fresh reproduction command from the reviewer checkout:

```text
git clone --single-branch --branch launch/g0-dgp-workflow-r2-20261021 https://github.com/esbraun/REMission.git contracts/dgp/.venv/fresh-clone
```

This is a genuine HTTPS network clone. Verified exact HEAD985ce540f0cc6ae1e57a6268651971acb546929d, clean status, HTTPS origin, and only `+refs/heads/launch/g0-dgp-workflow-r2-20261021:refs/remotes/origin/launch/g0-dgp-workflow-r2-20261021` fetch mapping. `.git/objects/info/alternates` is absent. `git cat-file -e 'c239dca^{commit}'` and the equivalent8315ee9 check both report invalid objects. No local reference clone, overlay, object copying or unpublished dependency was used. From that clone, `../Scripts/python.exe -m contracts.dgp.checks` passes all seven commands using the same isolated pinned environment against the clone's own source.

## Acceptance boundary

The combined exact candidate is **ready_to_ship** for G0-DGP/G0-WORKFLOW contract integration. Root alone may integrate after its dependency/protection checks and must record the reviewed head/base and resulting merge. Any head or target-base change requires refreshed review and affected checks.

G0 overall remains unaccepted; G0-LIB's unresolved DR selection/repairs are separate and are not approved by this report. G1 still must execute the full generator, qualify PRNG/draw scheduling, independently generate/verify pain and upload provenance, calibrate reporting/external targets and source-SE pilots, inspect distributions, reproduce full paired null trajectories, implement independent Layer B truth/precision, and deny learner/process/storage truth access. Actual Bayesian fitting, WCLS, bounded learning, recovery/null/policy repetitions, integrated persistence/browser behavior and G2-G7 acceptance remain required. Human-factors/manual accessibility, clinical review and clinical validation remain explicitly deferred/unaccepted; no real patient system, message, order or wearable account was used. No statistical or human gate is waived by this contract acceptance.
