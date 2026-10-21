# Validation protocol

Specification revision: 2026-10-19. Status: requirements only; no implementation or validation result is asserted.

**Read first:** [00-scope-and-invariants.md](00-scope-and-invariants.md), [01-estimands-and-contracts.md](01-estimands-and-contracts.md), [02-synthetic-dgp.md](02-synthetic-dgp.md). Read linked scenario and evidence entries only when needed.

**Inputs:** versioned upstream contracts and applicable scenario IDs. **Outputs:** the contracts, artifacts and checks specified below. **Acceptance:** relevant G0–G7 evidence in [gates](08-gates-and-release.md); statistical checks use the [validation protocol](07-validation-protocol.md).

## LIB-BENCH — Selective future library comparisons

Follow the [library validation and benchmark plan](../plans/methods/03-validation-and-benchmarks.md). Use clear applicable official/published evidence for settled library choices. Plan targeted synthetic-DGP comparisons only for material unresolved accuracy, numerical, runtime or resource questions; record the decision, matched target, cells, protocol and disposition. Do not add blanket library tournaments. No benchmarking is executed by this documentation revision.

Library-selection evidence can avoid redundant comparative benchmarks; it cannot waive required analytic checks, SBC, causal recovery, null calibration, complete-cohort runs or reproduction. The 20-fit runtime/storage pilot below remains resource planning for expensive suites, not a required bake-off. Use library interval/bootstrap routines with the declared independent sampling units, not their default row-level assumptions. [Software evidence](../evidence/software-libraries.md).

## VAL-01 — Prespecified evaluation design

Use ADEMP: aims, data-generating mechanisms, estimands, methods and performance measures. Each protocol names cells from the [scenario catalog](scenario-catalog.md), matching estimands, model/prior versions, seeds, repetition counts, stopping/failure rules and artifacts. Freeze it before confirmation. [sim-ademp](../evidence/simulation.md#sim-ademp)

| Tier | Required repetitions | Permitted claim |
|---|---:|---|
| Analytic/deterministic | Every relevant change | Fixture and invariant correctness |
| Smoke | 5 per relevant scenario | Plumbing only |
| Development | 200 per selected cell | Debugging, tuning and runtime planning |
| SBC | 1,000 per final Bayesian family on tractable component configurations | Computational calibration in tested configurations |
| Confirmatory recovery | 1,000 independent datasets per mandatory component/scenario cell | Fixed-DGP operating characteristics |
| Decision-null | 2,000 independent complete runs per locked null decision cell | False-superiority performance |
| Integrated policy | 1,000 independent complete cohort runs per policy scenario | Closed-loop policy performance |

Analytic-only system scenarios need no meaningless model refits. The catalog identifies which tiers apply. A tractable SBC configuration does not validate numerical performance at full scale; final-scale diagnostics and recovery runs remain required.

Run a 20-fit runtime/storage pilot before expensive suites. Record estimated total cost and checkpoint/resume commands. Lack of resources leaves the gate incomplete; never silently downsize the study. Different seed namespaces isolate development and confirmation. Substantive post-confirmation changes require a new protocol and fresh seeds; retain previous results.

### VAL-02 — Metrics, sampling units and failures

Report bias, RMSE, empirical SD, mean reported SE, interval width, 50/80/95% coverage, false direction, false meaningful superiority, abstention, predictions separately from effects, subgroup/phase results, failures, burden, constraints, missingness, overrides, policy value, runtime and memory.

For binary rate p-hat over R independent repetitions, MCSE = sqrt(p-hat*(1−p-hat)/R); report a Wilson binomial interval as well. For zero events also report an exact one-sided upper bound, not zero uncertainty. At R=1,000, MCSE near 95% coverage is about 0.0069; near 50% it is about 0.0158. These calculations do not apply to correlated patient-night rows as independent repetitions.

For bias, MCSE is SD of replicate errors / sqrt(R). Use paired replicate differences for method comparisons. For nonlinear metrics use bootstrap of independent replicate/cohort units, retaining scenario stratification. Report raw per-scenario outcomes; do not collapse incompatible clinical endpoints into one score. [rliable](../evidence/industry.md#rliable)

Pooled adaptive algorithms are replicated as whole cohorts, including policy training and updates. Separate patient-level variation from algorithm-run variation. Coverage among successful fits and operational success-and-coverage among all attempts are both required. Counts of failed, abstained, undefined and pending results remain explicit; no favorable complete-case summaries.

### VAL-03 — Acceptance and failure rules

The numerical tolerances below are engineering acceptance criteria, not clinical standards or theorems from the cited papers.

| Check | Acceptance/disposition |
|---|---|
| Hard constraints | Zero observed violations; investigate every violation and report uncertainty when zero occurred |
| Truth | Independent simplified-case agreement and precision criteria in TRUTH-02; otherwise inconclusive |
| SBC | No unresolved rank/ECDF discrepancy across prespecified quantities; retain plots and reviewer diagnosis; demonstrate rejection of the seeded faults |
| Final fit | BAYES-02 diagnostics and estimand-specific numerical precision; otherwise failure or abstention |
| Matched reference bias | (absolute mean error + 1.96 times bias MCSE) / fixed truth outcome SD ≤0.1; degenerate SD fixtures use analytic checks |
| Matched reference coverage | Lower 95% Wilson bound for nominal 95% coverage ≥0.925; also report width and all other coverage levels |
| Misspecification/nonidentification | Characterize degradation and supported region; do not demand nominal coverage everywhere |
| Null decision claims | Upper one-sided 95% exact binomial bound for clinic-wide false superiority ≤0.05 |
| Personalization improvement claim | Locked held-out policy-value difference supports improvement over the best evaluated common eligible policy; otherwise fixed-policy fallback |

A nonsignificant uniformity test alone does not establish correct computation. Add likelihood-sensitive quantities and negative controls. Prior-predictive SBC coverage differs from fixed-parameter frequentist coverage; a Bayesian model can pass one and fail the other. Reference coverage thresholds describe the desired operating region, not a mathematical guarantee. [sbc-quantities](../evidence/simulation.md#sbc-quantities)

For numerical oracle comparisons, check truth MC error separately from fit MC error and dataset-to-dataset uncertainty. Gate failures cannot be cured by deleting difficult cells. Record a revised supported region or repair/version the method.

### DECISION-01 — Repeated recommendation calibration

Define a clinically meaningful benefit threshold in the estimand contract; synthetic demo thresholds are labeled engineering assumptions. Superiority is a separate output from sorting posterior means. Require eligibility, support, computational adequacy and sensitivity stability before considering probability thresholds.

On development runs evaluate posterior-probability cutoffs 0.95, 0.975, 0.99 and 0.995. Select the least stringent cutoff with a one-sided 95% upper bound on clinic-wide false superiority ≤0.05 across all locked null development cells. If none qualifies, disable model-backed superiority claims. Confirmation uses the selected rule unchanged and fresh runs. Insufficient tail-probability precision causes abstention.

Clinic-wide false superiority is at least one false superiority claim among all configured patients, options and review times in one complete 84-day run. Report patient-journey rates too, but use clinic-wide rate for the headline gate. Include interim stopping, model updates and multiple choices. A false meaningful-superiority claim means the declared effect fails the specified meaningful-benefit threshold in truth; distinguish it from merely selecting the wrong sign.

An always-abstaining rule can meet false-claim control, so also report useful-decision rate and performance in benefit scenarios. Do not claim useful personalization from null control alone. Harms and burden remain separate; no fabricated clinical utility weights.

### POLICY-01 — Matched policy comparison

Match eligibility, burden limits, context availability and horizon. Separate myopic constrained regret from long-horizon value. A hidden-state oracle is privileged, and a best common policy is not a patient-specific oracle. Evaluate the full learning algorithm, not only one fortunate trained model. [rliable](../evidence/industry.md#rliable) [netflix-hte](../evidence/industry.md#netflix-hte)

## 16. Methodological, software, and UX evaluation

### Bayesian and causal evaluation

Use prior predictive and posterior predictive checks and simulation-based calibration where the model/generator conditions warrant it.[stan_checks](../evidence/simulation.md#stan-checks)[sbc](../evidence/simulation.md#sbc)

- **Computation:** investigate divergent transitions and convergence; a target such as $\widehat R < 1.01$ is an engineering diagnostic gate, not evidence of causal validity. Choose effective-sample requirements for the reported estimands.
- **Calibration:** under model-consistent simulations, assess posterior ranks/coverage; distinguish simulation-based calibration from robustness to model misspecification.
- **Causal recovery:** compare conditional effects and policy values with hidden simulator truth across repeated independently generated datasets.
- **Null behavior:** under the sharp-null scenario, report the false-ranking rate and how it changes with sample size and with component-model flexibility.
- **Cold-start behavior:** report bias, interval width, coverage, and useful-decision rate at zero and increasing target observations.
- **Prior conflict:** compare weak borrowing, naive complete borrowing, robust mixtures, and prespecified transport sensitivities, each under more than one heterogeneity prior.
- **Robustness:** evaluate hidden confounding, poor overlap, outcome-model error, missingness, informative intercurrent events, phase shifts, and measurement bias.
- **Policy performance:** show outcomes, burden, hard-constraint violations, abstention, and regret against the simulator oracle.

Report Monte Carlo uncertainty for evaluation estimates. Do not assume that robust borrowing always wins, that Thompson sampling improves distal ISI, or that nominal Bayesian intervals maintain coverage under misspecification.

### Comparators

- Fixed clinically plausible synthetic care pathway.
- Population Bayesian model with no external borrowing.
- Naive complete external borrowing.
- Robust Bayesian longitudinal model.
- Single-decision BCF baseline where its estimand is appropriate.
- Optional longitudinal DML baseline only after matching its supported assumptions/data structure.
- N-of-1 analysis ignoring versus modeling carryover, and ignoring versus modeling rebound.
- N-of-1 with the support policy frozen versus left adaptive.
- MRT analysis by WCLS versus a naive mixed-model regression.
- Fixed/no support, MRT support, and constrained hierarchical bandit.
- Simulator oracle, restricted to the same eligible actions.

EconML's DynamicDML has specific panel and effect-modification constraints; consult its documentation rather than treating it as a generic drop-in for arbitrary irregular clinical histories.[dynamicdml](../evidence/causal.md#dynamicdml) Benchmark results must state which comparisons address the same estimand.

### Software invariants

- No future-available records or oracle values reach a learner.
- No excluded action is ranked as assignable or randomized.
- No randomized assignment is drawn without a current consent/oversight record for that component.
- Assignment probabilities are logged before outcomes, and every bandit probability for an eligible action lies within its prespecified bounds.
- The support policy for a patient does not adapt while that patient has an active N-of-1 block or washout.
- Assigned, approved, delivered, and taken actions remain distinguishable.
- Each likelihood uses each observation once per fit/update.
- No ISI value is imputed after a recorded death; a missing reward is never scored as an outcome.
- Historical views reproduce original versions and remain read-only.
- A correction creates lineage; it does not erase the original decision state.
- Approval fails safely on a material state/version change.
- Every stage has sensible loading, missing-data, error, hold, and empty states.
- All displayed units, outcome horizons, interval types, and data cutoffs are explicit.

### Human-factors and accessibility evaluation

Follow NIST's combination of expert review and representative-user task testing.[nist7804](../evidence/ux-and-interfaces.md#nist7804) Recruit intended clinician and nursing roles, including users with access needs; iterate formative tests before a broader task-based validation exercise.

Test these tasks with seeded cases:

1. Identify the patient, chemotherapy phase, and next owned action.
2. Recognize that a cold-start estimate is borrowed and not established individual evidence.
3. Compare two options and correctly interpret effect direction, interval, horizon, and unsupported modifiers.
4. Notice a medication/stability exclusion and choose the correct review path.
5. Review an N-of-1 block with carryover, rescue, and incomplete outcomes.
6. Distinguish durable behavioral escalation from reversible crossover.
7. Recognize when Oura and patient report disagree.
8. Select a historical decision, identify what was known then, and return to the current patient state.
9. Confirm that later outcomes did not inform the original recommendation.
10. Detect a deliberately wrong or unsupported recommendation and decline it.
11. Complete an assignment using keyboard navigation and the table alternatives.
12. Handle a late clinical update during approval without losing the draft or using stale readiness.
13. Recognize that a randomized option is unavailable because consent is missing or withdrawn, and identify the correct next step.

Measure task success, use errors/near misses, correct interpretation, time on task, workload, perceived usefulness, and workflow fit. Compare against the team's current or simplest prototype workflow where feasible. Preference ratings alone are insufficient.

Accessibility includes contrast, focus order/visibility, accessible tab semantics, screen-reader labels, zoom/reflow, reduced reliance on color, and chart alternatives.[wcag](../evidence/ux-and-interfaces.md#wcag)[tabs](../evidence/ux-and-interfaces.md#tabs) Select manual tab activation if fetching a panel introduces latency; follow the W3C tab pattern rather than invent keyboard behavior.

Define clinically important use-error acceptance criteria with the clinical/human-factors team. Resolve observed critical errors before presenting the demo as suitable for a clinical pilot. No arbitrary "five users prove safety" claim.
