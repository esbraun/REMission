# Validation protocol

**Milestone scope (2026-10-22):** the [PoC amendment](poc-amendment-20261021.md#immediate-physician-simulation-milestone-2026-10-22) makes Google Cloud physician simulation and deployed login/persistence validation immediate. Training/fitting and POC-VAL below belong to the later analytics milestone, not cloud simulation acceptance. POC-VAL retains all seven configurations, repetition counts and accuracy/timeliness obligations; it supersedes older exhaustive thresholds for that first study. Scientific integrity, valid targets, fit diagnostics and failure disclosure remain mandatory for analytics. Existing evidence is not upgraded by this scope change.

## POC-VAL — First ablation study

Use the existing stack and report an accuracy/timeliness tradeoff, not an assumed winner. Each switch changes actual computation; a display-only toggle fails acceptance. Retain a small selected matrix rather than crossing all switches. Reference, external-conflict and sharp-null settings are bounded restrictions of the existing DGP; record their actual parameters and independently check truth in simple cases. No numerical result is asserted here.

| Family and selected configurations | Matched target and data | Question |
|---|---|---|
| Visit: V0 no external borrowing; V1 robust compatible borrowing | Same longitudinal model, eligible pair, observed cohort and cutoff; the existing 42-day visit contrast under the same continuation policy. Reference, external-conflict and sharp-null settings. | Does borrowing improve early accuracy/uncertainty and at what time-to-result cost? |
| Individual: N0 carryover term disabled; N1 carryover term enabled | Same randomized reversible schedule, support frozen, observed outcomes/cutoff and N-of-1 estimand from the individual-experiment contract. One nonzero-carryover setting. Both configurations retain the same rebound handling and report target/identification limits. | Does modeling carryover improve recovery enough to justify fitting cost? |
| Support: S0 fixed/no support; S1 MRT with WCLS; S2 bounded adaptive support | Same eligible actions, availability, burden envelope, horizon and exogenous DGP seeds. One reference support setting. WCLS reports the proximal causal-excursion target on MRT data; adaptive model estimates are not substituted for that target. | How do observed support outcomes, burden and learning latency differ? |

Borrowing, carryover modeling and support mode are independently configurable in the research runner/UI; execute only these seven named configurations in their applicable families. Other components are held fixed. The fixed support policy is a policy baseline, not an estimator of the WCLS effect. Policy changes necessarily generate different action/outcome histories: pair exogenous streams across full cohort runs, not falsely identical post-treatment datasets. Evaluate support policy value separately from WCLS effect recovery; do not compare a 42-day ISI effect to a next-window support reward. No pooled ranking across families.

For visit and individual estimator comparisons, use identical generated observations, independent recorded fit seeds and identical available-at cutoffs. Generate study treatment assignments under a declared randomized behavior policy with sufficient support; interactive physician choices are excluded from causal-recovery confirmation. Default panel size is 12 and horizon 84 days. Inspect fits at days 14, 42 and 84 (prior-only/cold start shown separately); visit contrasts project 42 days beyond each cutoff under the declared policy, so evaluator rollouts extend beyond day 84 without leaking those observations into fits. For N-of-1 use scheduled block completion cutoffs with adequate data and label earlier results unavailable, not fabricated. Fit uncertainty, oracle numerical error and dataset-to-dataset uncertainty remain distinct.

**Exploration:** run 3 independent panels per selected scenario/family, extending to at most 8 only to resolve fit/runtime or variance uncertainty. This is an engineering pilot, not evidence of calibrated coverage. Record attempted fits and elapsed time; do not first run the historical 20-fit resource pilot or hundreds of catalog cells. Investigate analytic/simple-case discrepancies, diagnostic failures and leakage before interpreting performance. Bayesian final fits retain applicable BAYES-02 diagnostic and estimand-precision checks; insufficient computation yields failed/inconclusive results, not a relaxed success badge. Check WCLS against an analytic/reference calculation and support propensity/mask/freeze rules directly.

**Confirmation:** freeze models, schedules, estimands, cutoffs, scenario parameters, metric definitions and a fresh seed namespace after exploration. Choose independent panel counts from a stated precision goal and measured cost; start with 30 per selected scenario/family and cap this first study at 100. For a coverage rate, use sqrt(p(1-p)/R) to show attainable MCSE (worst case about 0.091 at 30 and 0.05 at 100); these counts cannot certify the old 0.925 lower coverage bound or rare-event safety. Use the pilot SD of paired error differences divided by sqrt(R) for mean-difference precision planning, and retain paired panels for RMSE/interval-width comparisons. If the desired precision exceeds the cap, report inconclusive and the extra count required rather than quietly expanding or asserting equivalence. Do not tune on confirmation or discard difficult/failed panels; any revised model gets a new version and fresh seeds. Confirmation is required for the PoC report but demonstrating superiority is not.

**Metrics:** for visit/N-of-1 effects and MRT effects report bias, RMSE, interval width and nominal 95% coverage with MC uncertainty; predictions use separately named observed-outcome error/interval coverage. Include successful-fit coverage and success-and-coverage over all attempts, failures/abstentions/undefined targets and effective observation counts. Use independent panels/cohorts, not patient-nights, as replication units. Pair method differences and give uncertainty; report null sign/ranking errors descriptively, with no calibrated meaningful-superiority badges. Support reports observed proximal reward, burden, constraint violations and evaluator policy value under the same horizon; no clinical utility or personalized-improvement claim follows automatically.

**Timeliness:** report cold start, fit/update, rollout and end-to-end request-to-result wall time, accepted-fit yield and peak memory on the recorded machine/settings, including failed attempts. Show accuracy, interval width and time-to-result versus available observations at each cutoff; distinguish simulated days needed to learn from wall-clock latency. Display analysis progress/error and the result cutoff while users continue the simulation. Do not optimize draws/second at the expense of usable numerical precision.

### APPT-04 — Appointment timeliness and freshness

For the [accepted appointment requirements](poc-amendment-20261021.md#appt-0105--background-refresh-and-appointment-prediction), measure queue wait, background fitting/conditioning, artifact load/validation, scenario rollout, publication, foreground response and UI rendering separately. Freeze machine/resources, load, sample counts, cache/cold/warm state, metric definitions and engineering budgets before runs. Report failures, peak memory and accepted-result yield; preserve every attempted fit. No foreground fitting is permitted. Exact artifact round-trip and no-fit/no-future-data tests are prerequisites to timing a new saved-posterior scenario path.

Provisional engineering hypotheses are current summary/status response p95 <=2s, explicit background-refresh acknowledgement p95 <=2s and a qualified uncached bounded scenario p95 <=15s. Retain <=8h background completion only as a scheduling hypothesis to revisit with genuine cohort measurements. Retire the prior <=5min fresh appointment-fit hypothesis. None is measured performance, a guarantee or a clinician-approved SLA; record the cold/warm distributions and sample size, and do not claim production p95 from small smoke runs. Exceeding a foreground budget yields visible pending/unavailable behavior and a recorded limitation, without reducing draws or numerical precision.

Report freshness lag between current available H* and consumed H*, including same-time corrections/lineage changes, separately from artifact wall-clock age. Quantify the effect of dated results without scoring them as estimates of a newly current target or moving their original forecast horizon. Keep paired effect bias/RMSE/coverage/width, prediction metrics, independent truth error, all-attempt failure/abstention, simulated learning time and existing study counts beside compute cost. No improvement in accuracy or speed is required. A4 remains not started; this promotion supplies no benchmark result.

**Acceptance:** all required computations execute, relevant invariants and independent simple-case checks pass, failed estimates are withheld and explained, and the reproducible report includes the selected matrix, counts, diagnostics and uncertainty. Weak or inconclusive statistical performance is an allowed reported finding; broken generation, fake fits, omitted components or leakage are not. Use a concise saved run summary plus reproducible data/results in existing artifact storage. Human/clinical review and broad statistical certification remain later work.

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
