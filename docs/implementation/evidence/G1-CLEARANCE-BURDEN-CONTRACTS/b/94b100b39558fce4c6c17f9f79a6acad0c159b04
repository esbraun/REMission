# Independent G0-DGP / G0-WORKFLOW review

Observed 2026-10-21, America/Los_Angeles (review closeout around 00:07 PDT). Requested reviewer: gpt-6-astra, medium. Assignment provides those settings; this runtime exposes no independent effective-model/effort introspection. No substitution requested or performed. Reviewer CODEX_THREAD_ID: 01a15d45-e5ee-7693-ac4b-91d75c46b1bf.

Reviewed head: `6195f9b745b672f087c9fdbd670497f80b7864ba`.
Reviewed accepted target base: `6c3fb070d36bfefbd070f2a2c33ccba7631734be`.
Exclusive detached reviewer checkout: `C:/Users/erics/Documents/Projects/REMission-worktrees/g0-dgp-workflow-review-20261021`.

Disposition: **changes_requested** for the combined candidate and G0-DGP. G0-WORKFLOW is **ready_to_ship as a low-fidelity contract package only**, with no blocking workflow-specific finding. This does not authorize merging the combined candidate, accept G0 overall, or accept runnable UI, human-factors, clinical review or clinical validation.

## Findings, ordered by severity

### P1 - S02 is not a sharp ISI null under its declared fixed support policy

Locations: `contracts/dgp/scenarios.py:13`; `contracts/dgp/parameters.py:147`; `docs/implementation/dgp-decisions.md:34`, `:41`, `:50`, `:85`; `tests/contracts/test_dgp_contracts.py:72`.

S02 removes z_L and z_B but retains L_T=-.1, the L>3 hold trigger, support subject to holds/eligibility, and z_prompt=-.08. The visit truth uses first-four-eligible-weekdays fixed support, and explicitly recomputes later eligibility. Thus T -> L -> clinical hold/support availability -> prompt -> z -> recall -> ISI remains open. Disabling adaptive support does not remove this path: a fixed mapping can produce different actions under different histories. Gaussian L innovations have full support, so a threshold crossing is possible even if uncommon. A rare nonzero path still invalidates a sharp-null calibration cell.

Independent local algebra counterexample, using the resolved S02 coefficients rather than a generator under test: after 28 assigned nights, paired L difference is -.1*(1-.6**28)/(1-.6)=-.249999846476445. On an eligible prompt weekday a common innovation can put one coordinate at L0=3.05 and L1=2.800000153523555, while other coordinates are below threshold and earlier histories have not triggered a hold. All other availability inputs can agree and the burden cap can be free. The control is held, while the treated trajectory receives the fixed prompt. The severity difference is -.08. Choose subsequent common innovations that hold both trajectories and hence prevent later prompts; z difference decays with .5. If this occurs on day28, day42 recall difference is -.08*sum(.5**k for k in range(14))/14=-.011427873883928573. At common baseline recall/error zero, the seven reference ordinal margins yield expected ISI difference -0.06120213724802426. This illustrative conditional expectation is not a claimed population simulation result; monotonic ordinal margins show the difference persists for finite common recall error. Neighborhoods of these innovations have positive probability. The intermediate L remains treatment affected as required.

Required repair: explicitly close every T-to-ISI path in the S02 contract, including eligibility-mediated support. For example, null all prompt-to-outcome/state paths in that cell while preserving diagnostic L changes, or specify an appropriate reviewed null support intervention. Do not bypass the general hold/consent rules or soften the sharp null. Version/update the authoritative overrides, generated manifest, prose and evidence consistently. Minimal meaningful regression: construct paired histories straddling L=3 with otherwise identical support prerequisites, demonstrate different availability/diagnostic L, and require identical declared outcome transition/ordinal law under the corrected null. Retain full G1 paired-trajectory equality as outstanding; checking only z_L/z_B zeros is insufficient.

### P2 - Solved calibration retrieval does not bind purpose or requested target

Locations: `contracts/dgp/calibration.py:13`, `:17`, `:56`; `docs/implementation/dgp-decisions.md:75`; `tests/contracts/test_dgp_contracts.py:116`.

`require_solved` checks status, cell ID and DGP VersionRef only. A record for S23.MAR_20.n60 with target=achieved=.6 is valid and returns its coefficient, although the cell requires observation target .8. Changing purpose to event_rate also passes and returns the same coefficient. Validating numerical closeness to the record's own target does not establish the correct target for the cell. This defeats the advertised fail-closed derived-binding boundary before G1 consumes it.

Reproduction observed in the isolated environment:

```python
from contracts.dgp.calibration import CalibrationBinding, require_solved
from contracts.domain.common import VersionRef
r = {'id':'dgp-v1','version':'1.0.0','sha256':'a'*64}
d = dict(schema_version='1.0.0', synthetic=True, purpose='report_rate',
         status='solved', dgp=r, cell_id='S23.MAR_20.n60',
         calibration_sample_sha256='b'*64, seed_key_sha256='c'*64,
         sample_size=200000, target=.6, achieved=.6, achieved_mcse=.001,
         coefficient=2., iterations=10, source_se=None, source_se_mcse=None,
         source_pilot=None, smallest_estimator_se=None,
         frozen_before='development_and_confirmation')
for changes in ({}, {'purpose':'event_rate'}):
    b = CalibrationBinding.model_validate(d | changes)
    print(require_solved(b, cell_id=d['cell_id'], dgp=VersionRef.model_validate(r)))
# Observed: 2.0, 2.0; both should be rejected for this report-rate request.
```

Required repair: bind consumption to the authoritative expected calibration purpose and target specification, in addition to cell/DGP identity; for source contrasts include the independently frozen reference/pilot/target derivation identity as appropriate. Unknown/noncalibrated cells must not acquire executable coefficients merely by supplying matching free strings. Add wrong-target and cross-purpose regressions with otherwise matching versions/hashes, plus a valid expected request. Source-SE pilots and achieved calibration remain future work; this finding does not demand running them now.

### P2 - MAR reporting is scheduled before one of its declared observed parents

Locations: `docs/implementation/dgp-decisions.md:29`, `:30`, `:62`, `:75`; `contracts/dgp/parameters.py:130`.

Step 1 records morning report missingness/availability at 07:00. Step 2 only computes/measures L_t and makes its record available at 08:00. The MAR observation logit uses current observed pain, a coordinate of L_t. The proposed refinement therefore cannot evaluate its 07:00 reporting decision from the declared available observed parents. S23 MAR, S24 MNAR/action reporting (which adds to this base), and S31 admission_reporting inherit the ambiguity. The canonical reference also needs this timing reconciliation; carrying it into newly explicit clock times does not satisfy the G0 requirement of no unresolved ordering ambiguity.

Required repair: define the precise report-process time and pain index/availability, without silently changing the canonical MAR mechanism or leaking future information. An acceptable explicit refinement could collect the report event at 07:00 but determine/upload availability only after the required observed pain record exists, with delays and cutoffs consistently based on that decision; any alternative parent/index change needs a reviewed version. Reconcile the accepted temporal contract through the appropriate owner if necessary. Add a bounded dependency/time check demonstrating that each observed reporting parent exists before its reporting decision and that a 07:00 learner cutoff cannot obtain an 08:00 pain record. No longitudinal rollout is required to resolve this contract ambiguity.

## Scope and independent inspection

Verified root, detached exact HEAD, accepted base commit object and clean tracked/untracked state before work. Candidate diff contains the assigned 17 files. No candidate file was edited, staged, committed or merged. Only this new report and artifacts inside ignored `contracts/dgp/.venv/` were written. No other live agent checkout was accessed.

Read the bounded entry/index, execution delegation/runtime/engineering requirements, G0 gate/technical plan and task-ledger entries, scope, canonical DGP/reference/scenario catalog, relevant estimand/temporal/domain types and workflow boundary sources, patient decision/service UI requirements, candidate source/manifest/test/evidence paths. Large concatenated reads were truncated; relevant omitted decision/workflow/calibration sections were subsequently read in bounded ranges. This is not a claim to have reread all project documentation.

The 185-row parameter inventory was checked against the independent canonical reference equations, initial laws and scenario requirements, not merely against its generated JSON. Baseline X/U/b SD conventions, M/J/site laws, initial L/state/taken/living values, positive-definite L covariance, steroid phase, B retention/gain, medication carryover/rebound, assignment/delivery/rescue, Q/F clipping, ordinal cutpoints/offsets, diary/wearable error, death/admission/discontinuation and explicit optional descriptive/irregular laws are represented. Added values are labeled synthetic. The timing and null-path findings prevent completeness acceptance despite the inventory count.

Exact expansion independently checked against catalog families: 73 explicit variant rows, 82 ordered cells; only S01-S05 and S20-S22 duplicate n60 with n240. S14 has five controls, not a half-life-by-rebound product; S31 has only two explicit compounds. Missing/unknown/altered parameter tables and scenario targets/order fail closed through exact token comparison; no missing-cell fallback. This validation protects the frozen authoring artifact, not its scientific correctness.

## Scenario-by-scenario critique

| Families | Independent disposition of overrides/targets |
|---|---|
| S01, S06 | Full reference/feedback equations retained; later longitudinal comparison must recompute all descendants and match continuation. No new override issue. |
| S02 | Blocking open support-mediated path described above; zero truth not accepted. |
| S03 | Correctly separate FIX-CONSTANT, continuous fixture_points, ATE/CATE -1; not an ISI effect. n60/n240 evaluation sizes distinguish catalog from canonical n200 analytic example. |
| S04 | Behavioral T modifier -.4*(2M-1), with L_T and z_B disabled, resolves the medication-versus-behavioral target ambiguity. Coefficient is not an ISI contrast; independent rollout still required. No direct medication modifier is silently used. |
| S05 | L_T=0, z_B=0 and zero direct T/modifier remove the behavioral paths while .2M remains prognostic. Unlike S02, T does not move L and therefore cannot open the same hold-support path. Exact zero is a defensible no-useful-heterogeneity choice, not nonzero homogeneous ISI benefit. |
| S07 | U withheld only from export, retained in assignment/outcome; inability to diagnose hidden confounding correctly preserved. |
| S08 | Three floors plus distinct structural-zero X>1. Whole-population truth does not identify unsupported observed-data effects; abstention retained. |
| S09-S11 | Compatible source, +1/+2 independently piloted source-SE shifts and separate reversal are appropriately marginal targets. S11 genuinely enables the behavioral modifier in source/target and omits source M while shifting X/M. Binding defect above must be repaired; actual pilot/solver/achieved truth remain unexecuted. |
| S12 | Three separate lineage rejection cases; zero numerical overrides are appropriate system fixtures, not evidence lineage tests have executed. |
| S13-S14 | Correct block/rho cells, stationary AR replacement and half-life/rebound ablations. Initial residual SD .4 and sqrt(1-rho^2) innovations preserve variance; washout excluded from endpoint but retained in dynamics. |
| S15 | Explicit phase-aligned/balanced scheduling avoids overlapping blocks; AB/BA probabilities and history-specific schedule mapping remain required. Horizon truncation/inconclusive counts are disclosed. |
| S16 | Adherence/rescue, outcome stop and insufficient-block cells are distinct. Assignment effect and observed stopping history preserved; minimum two informative A/B blocks prevents a one-block winner. |
| S17-S18 | Independent FIX-* linear escalation trees, not EST-ESC ISI truth. S18 uses X standardization under intervention rather than observational treatment distribution. Clinical-scale day28/day84 rollout correctly remains separate. |
| S19 | Label flip and sparse observed classification are separate. True response drives outcome; observed label controls escalation. Sparse .9 is not mislabeled latent response probability. |
| S20 | Immediate/delayed/prompt-skill paths all zero and habituation zero. Burden can change future offers, but none of those offers has a remaining declared reward path. Fixed/MRT null targets and complete-cohort policy validation remain distinct. |
| S21-S22 | Immediate -.08, separate habituation .2 and delayed harm +.15; proximal excursion not conflated with distal policy value. |
| S23-S24 | Correct five MCAR/MAR and three MNAR/action variants. Action-dependent selection retains equal true reward paths; reporting changes are not reward benefit. Target binding and timing findings apply. |
| S25-S26 | Correct quiet-wake/device controls and separate copula/recall/phase-item cases. Copula preserves logistic margins; shared recall dependence retained. Oppositely signed offsets need not leave total expectation unchanged away from symmetry. |
| S27 | Four separate interruptions; own-intervention conditional ISI denominators and no post-death values preserved. Discontinuation end-day21/start-day22 convention explicit. |
| S28 | Five distinct availability/lineage/stale/consent system cases; no execution falsely claimed. |
| S29 | Full support mapping frozen through blocks and washout; deliberate global drift is a rejection fixture, not a valid alternative assignment. |
| S30-S31 | Only +2SE/floor.01, regimen-change/half-life3, and admission/MAR40 compounds; no implicit extra perturbations. Calibration/timing fixes apply. |
| S32 | .5 logged versus .8 executed, .6+.6 lower bounds, missing fit and no actions are explicit faults; reject rather than normalize into apparent success. |

## Analytic truth and information boundaries

Independently derived Normal posterior v=4/81, mean=40/81 for sum10/n20; Beta posterior (10,15); constant ATE -1; modifier CATEs -1/+1 with marginal0; contextual values 1/1/1.5. Two-period E[Y(a,b)] = .5 + .5*(expit(-1+.7a)+expit(-.2+.7a)) - a - 2b, so the total first-stage effect is not merely -1. Ordinal tail sums yield 2 per equal item at severity0 and total14 regardless of item dependence. Randomized escalation values 2.4,3.6,3.6,4.4 for 00,01,10,11 follow 2+a+p+2(1-p)b; observational standardized values add .5 because marginal response is again .4+.2a while E[X]=.5. Noisy-label and sparse-label enumeration correctly weights true nonresponders receiving escalation. These are independent algebra comparisons, not model prediction reuse.

Truth precision requires absolute and relative MCSE, refuses zero target SE without analytic truth, and reports exhausted cap inconclusive. SHA256 canonical seed keys include phase and namespace independently and isolate named substreams. Actual NumPy PRNG qualification, draw scheduling invariance, independent Layer B rollout, truth storage/process denial and statistical calibration are explicitly later obligations. No source pilot, external calibration, achieved missingness rate, large-sample distribution inspection, SBC, recovery, policy or false-claim acceptance was executed here or waived.

## Workflow/UI review

All ten ASSIGN stages have task context, ownership, comparison semantics and allowed/denied actions. Parallel clinical/learning/readiness/support/view dimensions preserve hold authority. Component consent lineage, expiry/withdrawal/retraction tombstones, no draw on denial, N1 full snapshot freeze/washout/review, ordinary-care versus randomization, historical read-only reload, explicit return to current, task/owner draft isolation and current-version atomic/idempotent approval are specified. The single-doctor app does not silently acquire operational nurse/research auth routes. Failure/missing/pending/undefined/prior-only/unsupported results and interruption vectors are appropriately distinct. Synthetic thresholds and no-superiority default are explicit.

Applied installed `react-best-practices/SKILL.md` (async-parallel, rerender-derived-state-no-effect), `composition-patterns/SKILL.md` (architecture-avoid-boolean-props), and `web-design-guidelines/SKILL.md`. Fresh rules fetched 2026-10-21 from https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md; raw-byte SHA256 `d246b026f4f29b5823a9cc857f9edf3d2507002e055e32040cadeaf3b38e0234`. Saved ignored copy at `contracts/dgp/.venv/web-guidelines.md`. Read the fetched rules. Only applicable low-fidelity guidance evaluated: explicit variants/service-derived state, authorized independent reads, accessible labels/status/help/focus semantics, narrow-layout critical information, history and draft navigation. No typography/render/React performance/accessibility compliance pass inferred from text sketches. No detailed design/runtime upgrade/hosting change requested.

## Reproduction evidence

Inspected runner, exports, contract source and tests before executing. Created an isolated Python 3.13.7 environment with `python -m venv contracts/dgp/.venv`, then installed `requirements-contracts.txt` exactly: pydantic2.14.1, pydantic_core2.50.1, annotated-types0.8.0, typing_extensions4.16.0, typing-inspection0.4.4. No methods stack was installed.

Executed `contracts/dgp/.venv/Scripts/python.exe -m contracts.dgp.checks` **without --record**: all six runner commands passed (pip check, DGP export --check, domain export --check, unittest discovery, ledger check, whitespace). Independent discovery confirms 43 tests (16 DGP, 27 domain). Explicit base-to-head `git diff --check 6c3fb070d36bfefbd070f2a2c33ccba7631734be HEAD` also passed. Committed author evidence was not overwritten.

Fresh reproduction command, from the reviewer root:

```text
git clone --single-branch --branch launch/g0-dgp-workflow-20261020 https://github.com/esbraun/REMission.git contracts/dgp/.venv/fresh-clone
```

This is a genuine network HTTPS clone, not a local/reference clone, overlay or copied checkout. In that clone, verified HEAD equals exact reviewed6195; origin is the HTTPS URL; fetch refspec is only `+refs/heads/launch/g0-dgp-workflow-20261020:refs/remotes/origin/launch/g0-dgp-workflow-20261020`; `.git/objects/info/alternates` absent; git status clean. `git cat-file -e 'c239dca^{commit}'` and `git cat-file -e '8315ee9^{commit}'` both exit128 (objects absent). From that clone ran `../Scripts/python.exe -m contracts.dgp.checks`: all six commands passed against clone sources using the same isolated pinned environment, avoiding a redundant identical installation. No local source overlay/PYTHONPATH supplied. This demonstrates checks do not require the unpublished historical objects.

Ignored independent adversarial script `contracts/dgp/.venv/adversarial_review.py` produced the numeric null-path counterexample and both accepted wrong bindings reported above. Its essential calculation and complete binding reproduction are included in this report, so fixes do not require access to the reviewer's checkout. No full simulator was invented or run.

## Acceptance boundary

Repair the three G0-DGP findings and rerun affected checks under a new exact candidate, then obtain independent refreshed review. G0-WORKFLOW has no blocking finding for its present document-only scope, but combined integration must wait. Human/clinical review is explicitly deferred by user authorization and is not an engineering blocker here; neither synthetic contract review nor these checks substitutes for those reviews. G1 rollouts/distribution/denial tests and G2-G7 statistical/integration/reproduction gates remain mandatory and unaccepted.
