# Synthetic data generating processes

Specification revision: 2026-10-19. Status: requirements only; no implementation or validation result is asserted.

**Read first:** [00-scope-and-invariants.md](00-scope-and-invariants.md), [01-estimands-and-contracts.md](01-estimands-and-contracts.md). Read linked scenario and evidence entries only when needed.

**Inputs:** versioned upstream contracts and applicable scenario IDs. **Outputs:** the contracts, artifacts and checks specified below. **Acceptance:** relevant G0–G7 evidence in [gates](08-gates-and-release.md); statistical checks use the [validation protocol](07-validation-protocol.md).

## DGP-LIB — Numerical implementation and benchmark use

Use NumPy Generator/SeedSequence and SciPy numerical distributions under the [library decisions](../plans/methods/00-library-decisions.md); preserve keyed streams, independent truth and evaluator access restrictions. The [validation plan](../plans/methods/03-validation-and-benchmarks.md) reuses these DGPs for targeted future library comparisons only where existing evidence does not resolve a material choice. No benchmark is executed by this revision, and selection evidence does not replace G1-G6 validation.

## DGP-01 — Three generator layers

**Layer A:** independent normal–normal and beta–binomial posterior fixtures; randomized constant-effect treatment; a two-group effect modifier; an enumerable two-period treatment-confounder system; ordinal category/total expectations; a two-action contextual bandit; and an enumerable two-stage escalation tree. Check signs, units, updates, standardization and probabilities against analytic answers. [sim-check](../evidence/simulation.md#sim-check)

**Layer B:** the longitudinal reference environment below, with 14 pre-assignment days and 84 prospective days. Decisions occur on days 0, 21 and 42; ISI assessments on days 0, 14, 28, 42, 56, 70 and 84 with common 14-day recall. Visit contrasts predict 42 days ahead. Initially permit one support decision per day with next-morning reward. These are engineering defaults.

**Layer C:** independent nonlinear, heavy-tailed, abrupt-shift, reporting, measurement, hidden-confounding and nonoverlap generators. Do not implement every stress generator by calling the fitted likelihood. Shared event contracts are allowed; shared generative/estimator equations cannot be the only verification path. Model matching is intentional for SBC and insufficient for robustness.

### DGP-02 — Generator specification acceptance

Before G1 implementation, a versioned table specifies every symbol, unit, distribution, baseline value, scenario override and provenance. Missing coefficients are a G0 contract gap, not permission for undocumented defaults. Code references this table; changes create new DGP versions. Scenario catalog values are fixed engineering stresses; other synthetic coefficients require a recorded G0 contract review, not clinical efficacy claims.

Specify equations and initial distributions for baseline heterogeneity, clinical transitions, chemotherapy/steroids, assignment, adherence/rescue, cumulative skills, carryover, rebound, sleep/function, ISI/diary/wearable observations, reporting delays, hospitalization/death and eligibility. State every parent and innovation dependence using [TIME-01](01-estimands-and-contracts.md#time-01--daily-ordering-and-history). Inspect distributions on a large generated sample before fitting.

Latent sleep, reports and wearable estimates stay distinct. ISI items share recall-window severity; they are not independent nightly totals. Base common causes are measured; hidden-confounding variants remove selected causes from learner exports.

### TRUTH-01 — Target-specific truth

Name the target: structural parameter; marginal contrast; observed-history conditional average; simulator-specific individual contrast; excursion effect under a named history-generating policy; fixed-policy value; or learning-algorithm performance across complete runs.

A structural coefficient is not a points-scale ISI contrast. Standardize interventions over the declared population and continuation/support policies. Conditional effects integrate latent states compatible with observed history. Conditioning on realized hidden states answers another question; label those privileged oracles separately.

Counterfactual rollouts may share exogenous draws to reduce variance. Individual-level coupling is a simulator assumption. Intervene through the causal transition system; overwriting treatment while leaving descendants unchanged is invalid.

### TRUTH-02 — Independent verification

Layer A uses analytic/enumerated answers. Layer B uses a separately implemented intervention rollout; compare both on simplified overlap cases. Tests must catch reversed treatment sign, omitted descendant updates and wrong continuation policy. Learner prediction code cannot be its sole truth evaluator.

Use keyed independent streams for generation, assignment, measurement/missingness, fitting, posterior rollout and truth. Keys contain protocol, namespace, scenario, replicate, patient, time and process. Variable draw counts must not desynchronize paired comparisons. Record PRNG/version and seed derivation.

Numerical truth includes a Monte Carlo SE. Accumulate independent batches until SE ≤0.05 ISI points or ≤0.01 on a 0–10 proximal scale, and ≤10% of the smallest estimator SE used in comparison. Pilot estimator SEs set the initial target; tighten if final fits require it. A zero target SE requires analytic truth or unresolved status. A recorded compute cap yields inconclusive truth when exhausted, not a pass.

Truth storage/processes are evaluator-only. Test denied access as well as export columns; debug endpoints cannot leak truth to ordinary UI/learners. Use only available-at history.

### DGP-03 — Development and confirmation

Use distinct seed namespaces. Freeze equations, model versions and thresholds before confirmation. Tuning after confirmation requires a new protocol and fresh seeds; preserve prior failures. The [catalog](scenario-catalog.md) defines targeted cells, not a Cartesian grid.

## 6. Synthetic data and simulator

The simulator is a causal environment with separate data export and hidden truth, not an arbitrary table of correlated fields.

### Default engineering presets

| Preset | Historical cohort | Synthetic external trials | Prospective cohort | Purpose |
|---|---:|---:|---:|---|
| Smoke | 100 trajectories | 2 small studies | 6 trajectories | Fast contract/UI checks |
| Demonstration | 2,000 trajectories | 4 studies with approximately 150–250 participants each | 60 trajectories over 12 weeks | End-to-end replay and worked patient cases |
| Evaluation | Configurable | Configurable | Configurable | Repeated simulations and sensitivity analyses |

These sizes are software defaults, not sample-size recommendations or promises of adequate clinical precision. Numerical treatment effects, kinetics, missingness, and decision thresholds in the simulator are invented engineering parameters and labeled accordingly. With two or four external studies, between-study heterogeneity is weakly informed and borrowing can be strongly sensitive to its prior (see the Bayesian-model specification); the smoke preset checks plumbing only and must not be used to illustrate borrowing behavior.

### Structural components

1. Baseline variation: leukemia/therapy strata, baseline insomnia, comorbidity, preferences, site, and measured effect modifiers.
2. Daily clinical state: chemotherapy phase, steroid exposure, pain, nausea, distress, fatigue, naps, and previous sleep.
3. Treatment assignment: historical clinicians respond to severity and measured clinical state, producing confounding by indication. Some states deliberately have poor overlap.
4. Treatment delivery: adherence, clinician overrides, rescue therapy, and missed support are generated separately from assignment.
5. Durable behavioral learning: a cumulative skills state influences later sleep. Turning off a reminder does not erase learned CBT-I skills.
6. Reversible medication dynamics: fictional onset/offset and carryover states, with patient-specific benefit and harm variation. Include a configurable withdrawal/rebound state in which sleep after stopping is transiently *worse than baseline*, because rebound insomnia after discontinuation is documented for some hypnotics and is not the same thing as residual benefit decaying to zero.[rebound](../evidence/clinical.md#rebound)
7. Sleep and function: latent sleep/wake and next-day function, autocorrelation, phase-dependent drift, and outcome-specific treatment effects.
8. Measurement: Oura-like estimates include quiet-wake misclassification, symptom-dependent bias, algorithm changes, and missing nights; diaries have a separate error process.
9. Visits and reports: generate dated outpatient observations, delayed uploads, and intermittent ISI assessments. Generate seven correlated ordinal ISI items on 0–4 scales from a shared latent severity and derive the 0–28 total.
10. External trials: randomize compatible interventions, generate study-level summaries and optional IPD, then introduce population/comparator/horizon differences in designated scenarios.
11. Clinical interruptions and intercurrent events: deterioration, medication exclusions, adverse symptoms, hospital transitions, regimen changes, and death make some actions unavailable or outcomes undefined, and depend on clinical state.

In the base scenario, all common causes needed for the specified observational estimand are measured. In a separate stress scenario, introduce a hidden common cause. The expected result is potential bias that ordinary Bayesian adjustment cannot fix.

### Required scenarios

| Scenario | What it should demonstrate |
|---|---|
| Compatible external studies | Borrowing can improve initial precision and learning efficiency |
| Conflicting external studies | Robust borrowing reduces dependence on incompatible evidence as local data accumulate |
| New Oura modifier absent historically | Wide modifier uncertainty at cold start; learning only when suitable new data exist |
| Sparse overlap | Suppress comparative ranking or flag unsupported extrapolation |
| Time-varying confounding | Static adjustment can be biased when prior treatment changes later confounders |
| Sharp null with treatment-affected confounders | No plan affects the declared outcome (other intermediate states may change); measures how often the parametric longitudinal model nonetheless ranks one plan as better (section 7.4) |
| Medication carryover and rebound | Naive nightly comparison differs from a model/protocol addressing residual effects; a washout that assumes decay-to-baseline is biased when rebound is present |
| Durable behavioral skills | On/off crossover is unsuitable for the continuing behavioral program |
| Illness-related missingness | Missing data can change conclusions; sensitivity analysis matters |
| Informative intercurrent events | Treating death or admission as ignorable censoring changes the estimate relative to the declared strategy |
| Quiet wake/device shift | Wearable improvement can disagree with patient-reported improvement |
| Steroid/chemotherapy phase change | Effects and clinical readiness may change across phases |
| Clinical hold/interaction | Eligibility is removed before optimization or randomization |
| Override/nonadherence | Assignment, actual treatment, and analysis populations remain distinct |
| Concurrent learners | An adaptive support policy left running during an N-of-1 block versus the frozen policy of section 3.1 |
| Prompt fatigue/delayed effects | Proximal reward optimization may not improve distal insomnia outcomes |
| Hidden confounding | Narrow posterior intervals need not imply valid causal effects |

All learners receive only exported observations. Oracle counterfactuals and structural coefficients are restricted to evaluation. Use patient-level, time-aware, and site-shift evaluation splits.
