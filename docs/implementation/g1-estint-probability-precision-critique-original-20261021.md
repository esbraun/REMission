# Independent EST-INT probability precision proposal critique

Disposition: changes_requested (PLAN ONLY).
Reviewed head: 0dace8262001856eea49821ebe6b73d9ff6e0847
Reviewed target/accepted base: 69e6ae9dc5bf85ddbf39976d2ce4ce70bce1ea1e
Worktree: C:/Users/erics/Documents/Projects/REMission-worktrees/g1-probability-critic-astra-20261021
Proposal blob: cc283ee4303b47863d54b76d576d301a8056da5a
Accepted G1 plan blob: 5d46eb071485a9d5f2ed0473880a75fcab181556
Assigned model/effort: gpt-6-astra / medium. Effective-model/effort introspection is not exposed to this worker; no substitution requested or performed.
CODEX_THREAD_ID: 01a15f87-f6d7-7342-8d9b-b7b50ce25ced
Reviewer did not author this proposal. No source edits, implementation, simulation, fits, PRs, merges or child agents.

## Severity-ordered finding

P1 — Define and enforce the conditional pilot's independent sampling unit before its empirical SD can set truth precision.

Locators: docs/implementation/g1-estint-probability-precision-proposal-20261021.md:39, :41, :43 (also :27 and :51); accepted docs/implementation/g1-technical-plan-20261021.md:95, :97, :123.

The proposal targets 30 independent conditional-environment continuations per arm and estimates their arm-mean sampling SD from 1,000 trials. The inherited implementation prescription explicitly regenerates filters between trials. It does not specify whether every independently sampled continuation has an independently randomized posterior approximation, or how to remove/control extra dependence if an arm/trial shares a finite filter. Line 43 says finite-filter variability cannot inflate S_min, but neither it nor the referenced concrete refinement rule supplies a variance diagnostic/estimator, tolerance, or acceptance predicate to enforce that prohibition. The concrete two-successive-refinement rule bounds changes in mean outcomes/contrasts. The accepted pilot passage also requests uncertainty and stability, but leaves the variance target unspecified; a stable inflated SD is possible.

This matters especially under the new probability exception: S_c now IS the empirical dispersion of trial means, so shared numerical-filter variation directly enters the quantity used to relax the relative precision gate. It is not just a later test awaiting execution.

Independently checkable derivation: let Q be the event probability induced by a randomly generated finite filter, E(Q)=p, and generate n indicators conditionally IID given Q within one arm. The law of total variance gives

Var(Ybar) = E[Q(1-Q)]/n + Var(Q)
          = p(1-p)/n + (1-1/n) Var(Q).

The intended independent conditional-population sample has variance p(1-p)/n. Independent trial seeds make the trial means independent, but do not remove the extra term inside each trial. Two particle levels can have the same mean and even the same distribution of Q while retaining that term. Averaging more truth filters controls uncertainty in the estimated probability mean; it does not make this pilot sampling variance equal to the intended comparator variance. The delta-method lower limit in line 41 is uncertainty about the contaminated SD, not subtraction of numerical-filter variance.

Bounded arithmetic counterexample (not a claim about the actual longitudinal DGP): p=.001, n=30, Q=.101 with probability .001/.101 and Q=0 otherwise. Thus Var(Q)=.0001. Independent target SE is .005770615218501403. Shared-filter population SD of trial means is .011400292393911078. Exact finite enumeration of K=0,...,30 under this binomial mixture, followed by the proposal's population-moment delta formula at J=1000, gives MCSE(S)=.0025488199408115362 and S-1.645*MCSE=.007207483591276102, still above the intended sampling SE. These are analytic/population-moment calculations, not an executed 1,000-trial acceptance artifact or a promised confidence bound. They demonstrate that the lower-limit operation is not a general remedy. The unconditional pooled-binomial check does not protect this path because line 43 limits it to unconditional IID arms.

Required narrow repair: choose and document the conditional pilot's filter/continuation seeding and allocation design. One straightforward option is independently randomized posterior filters for each independently sampled conditional environment, preserving only explicitly allowed within-patient counterfactual pairing and using fixed declared arm allocation. Alternatively specify a mathematically justified variance decomposition or other concrete control that prevents shared-filter variance from relaxing the matched SD binding, including uncertainty treatment, numerical tolerance and cap/unresolved outcome. Specify exactly which pilot quantity receives the two-refinement check. Add a reduced mixture/shared-filter fault fixture that passes mean stability yet must not produce an admissible inflated comparator SE, alongside the correct independent-unit fixture. Keep 1,000 trials, catalog n, conditional 30/arm, existing particle levels and all other mandatory gates. This is not a request to redesign conditional inference, certify particle bias, or run full simulations before plan acceptance.

## Findings not raised / coherent proposal choices

The new .001 probability absolute MCSE threshold is a reasonable explicit provisional synthetic-engineering choice; canonical TRUTH-02 has no existing general probability threshold. The probability-only empirical-pilot exception is defensible in principle and is correctly distinguished from the existing per-trial-minimum rule for ISI/quality/source shifts. I do not approve its conditional execution mechanism until P1 is resolved.

Six separately bound arm/component records, complete denominators, admission-before-death semantics, alive/outpatient <= survival, no forced sum-to-one, covariance retention, and no implied contrast/overall winner are coherent. Missing/failed ascertainment cannot be removed as complete cases. Zero sampled eligible paths correctly make the numerical symptom estimate undefined while acceptance remains unresolved unless structural zero is independently established. Partial vector retention is compatible with blocking full-vector acceptance.

Independent equal-sized outer batches and paired covariance are appropriate. The proposal distinguishes Monte Carlo variation from quadrature/particle approximation, preserves mandatory reduced checks and cap failure, and explicitly disclaims certified bias and simultaneous/sequential confidence coverage. The zero-batch bound uses genuinely independent batch indicators and is conservative for marginal event probability; at B=1000 it is .0029912495450953314, above the absolute .001 ceiling, so a nonanalytic all-zero conditional path cannot pass this bound under the cap. That deliberate incompleteness is not itself a design defect. No retry-until-pass pilot expansion is authorized.

For IID probability .5, binomial MCSE at 32*10,000 draws is .0008838834764831844; at 10 million it is .00015811388300841897. This is a limited arithmetic feasibility check of the absolute threshold, not evidence that conditional or rare-event gates are feasible. Smaller matched pilot bindings can still block. Throughput/resource qualification in the accepted G1 plan remains required; no sample reduction is recommended.

The empirical-SD delta expression is an explicitly labeled first-order large-sample approximation. Transforming a valid probability interval by the minimum of p(1-p) at its endpoints supplies the stated IID SE lower bound for fixed n_arm. Implementation must record fixed allocation or use a separately specified formula for varying allocations; an undocumented pooled denominator cannot stand in for the matched design.

## Contract implementation conditions (future work, not additional plan blockers)

The companion schema may settle field mechanics after the repaired plan is accepted. It must use strict finite/nonnegative units and consistency predicates; bind exactly both named actions and all three components; cross-check numerator/total/estimate/roster hashes and target identities; authenticate producer/raw artifacts; reject duplicate/missing records and legacy precision as accepted computed truth; and preserve raw partial failures. Map proposed computed/analytic/unresolved admission states explicitly to existing payload status vocabularies rather than overloading contracts/dgp/truth.py:101-115, which only supports ISI/quality and resolved/inconclusive/continue states. Established structural probabilities and undefined symptom targets need an explicit representation that does not fabricate Monte Carlo counts. These are enforceable implementation obligations, not reasons to reopen G0.

Required later probes include all proposal line 51 cases plus the P1 filter-variance fault above, covariance/paired-unit mislabeling, all-zero and nonpositive pilot lower limits, missing hashes/provenance, smaller matched-SE tightening, approximation failure/cap, and full-vector rejection on one unresolved component. None was claimed executed here.

## Observed review work and limits

Verified worktree root, exact HEAD, clean initial status and merge-base with the accepted target; diff is only the 53-line proposal. Verified both specified document Git blobs. Read the complete proposal and bounded accepted conditional/pilot/G1 execution sections, implementation entry point, runtime/delegation/engineering instructions and G1 gate context. Inspected canonical EST-INT/ConditionalSymptom/InterventionOutcomes/InterruptionResult, TRUTH-02, VAL-02 and contracts/dgp/truth.py. No canonical general probability threshold was found or inferred from unrelated tail/bandit thresholds.

Reproduced the variance identity and numerical examples with native PowerShell arithmetic and finite binomial-mixture summation, not generator/evaluator code. One exploratory PowerShell command had an empty-pipe parse error; it executed no calculation and was corrected. No production simulation, full calibration, Bayesian fitting, contract test suite or statistical acceptance was performed. No clinical/human review claim. The full G0-G7 objective and mandatory cell/sample obligations remain intact. Unrelated interfaces can continue while computed probability admission remains unresolved.

Root should route the bounded P1 plan repair to a separate planner, then request independent exact-head/base re-review. This disposition is not ready_to_proceed and grants no implementation/merge acceptance.
