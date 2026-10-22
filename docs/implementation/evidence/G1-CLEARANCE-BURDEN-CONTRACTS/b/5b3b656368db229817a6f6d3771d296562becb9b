# Individual experiments and behavioral escalation

Specification revision: 2026-10-19. Status: requirements only; no implementation or validation result is asserted.

**Read first:** [00-scope-and-invariants.md](00-scope-and-invariants.md), [01-estimands-and-contracts.md](01-estimands-and-contracts.md), [02-synthetic-dgp.md](02-synthetic-dgp.md), [03-bayesian-models.md](03-bayesian-models.md). Read linked scenario and evidence entries only when needed.

**Inputs:** versioned upstream contracts and applicable scenario IDs. **Outputs:** the contracts, artifacts and checks specified below. **Acceptance:** relevant G0–G7 evidence in [gates](08-gates-and-release.md); statistical checks use the [validation protocol](07-validation-protocol.md).

## EXP-LIB — Reused inference and protocol machinery

Follow the [experiment implementation steps](../plans/methods/02-experiments-and-support.md): NumPy assignment draws, shared PyMC N-of-1 inference and statsmodels/NumPy design-based SMART analysis. Project code owns schedule eligibility, carryover/rebound terms, support freezing, path probabilities and compatible-strategy covariance. Use library numerical solvers rather than a bespoke inference engine; preserve actual elapsed-time residual dependence and independent block/patient sampling units. [Software rationale](../evidence/software-libraries.md).

## EXP-01 — Validation contract

N-of-1 inputs are randomized block assignments and observed outcomes; target the assignment effect under the frozen support policy. Truth is an intervention contrast, not necessarily a pharmacokinetic coefficient. Evaluate bias, coverage, interval width, inconclusive rates, early stopping and false superiority using S13–S16 and S29. [n1bayes](../evidence/experiments.md#n1bayes)

Use 2, 4 and 8 blocks; residual correlation 0, 0.4 and 0.8; and fictional carryover half-lives 0, 1 and 3 days. Test rebound absent/present with matched and misspecified models. These values are engineering stresses, not real drug protocols. Apply targeted cells in the catalog rather than every combination.

Distinguish assignment-effect recovery from kinetics identification. Include randomization schedules aligned and misaligned with chemotherapy phase, rescue, nonadherence, informative termination and too few blocks. Known randomization does not remove carryover or reporting problems.

## SMART-01 — Stage and strategy estimands

Define an enumerable two-stage randomized fixture and a separate observational-first-stage/randomized-escalation fixture. Enumerate response rules, assessment times, eligible responders/nonresponders, complete strategies and probability products before fitting.

Estimate second-stage continuation-versus-escalation among eligible nonresponders separately from whole-strategy values starting at enrollment. In the observational-first-stage fixture, whole-strategy identification needs the declared confounding assumptions. Randomization at escalation alone does not establish those assumptions.

Compare longitudinal g-computation with a design-based weighted estimator for matching targets. Retain responders in all compatible embedded strategies and account for covariance when records contribute to multiple strategy estimates. Validate against enumeration, then S17–S19; report sparse-cell uncertainty rather than force a winner. [smart-adaptr](../evidence/experiments.md#smart-adaptr)

## 8. Individual experiments and behavioral escalation

### N-of-1 branch

Use only when the clinician has approved both options, the comparison is reversible, the patient agrees, the consent/oversight record is current (section 2.1), and the relevant clinical state is sufficiently stable. AHRQ's N-of-1 guide addresses design, washout/carryover, trends, and repeated observations; Bayesian hierarchical analysis enables pooling across individual trials and can incorporate trend, carryover, and autocorrelation.[n1guide](../evidence/experiments.md#n1guide)[n1bayes](../evidence/experiments.md#n1bayes)

The protocol designer must capture:

- Clinical question, common background treatment, comparator, endpoint, and patient preference.
- Randomized block sequence and assignment probabilities.
- Blinding status of patient and clinician, and the resulting estimand label (section 4).
- Onset/offset assumptions and treatment-specific washout/carryover handling.
- Withdrawal and rebound handling: whether stopping either option can transiently worsen sleep below baseline, and if so how those nights are treated. Rebound insomnia is documented after discontinuing some hypnotics,[rebound](../evidence/clinical.md#rebound) and nights affected by it are neither clean "off" nights nor valid comparator nights.
- Clinical stability criteria and chemotherapy/steroid scheduling.
- Fall-risk review acknowledged for any sedating option (section 2).
- Rescue use, adherence collection, burden, and stopping rules.
- Prespecified analysis and clinician review points.
- The frozen support policy in force during the trial (section 3.1).

Do not prescribe a universal block length or washout interval. In the synthetic demo, use configurable fictional pharmacokinetics; future real protocols require drug-specific review. An agent whose discontinuation effects cannot be bounded within a feasible washout is not a suitable N-of-1 candidate, and the designer should say so rather than shorten the washout.

Analyze block assignment with patient effects, time/phase trends, residual carryover, rebound where configured, and serial correlation. Show the uncertainty that remains if only a few informative blocks are available. If instability or carryover defeats the comparison, terminate or redesign it; do not force a confident "winner."

### Durable behavioral care

Do not randomize the patient repeatedly between "CBT-I on" and "CBT-I off" as if learned skills wash out. Continue the core program.

Demonstrate a SMART-like pathway: after a prespecified assessment, eligible nonresponders may be randomized between clinician-approved continuation and escalation strategies.[smarttrial](../evidence/experiments.md#smarttrial) Predefine response rules and sequential assignment probabilities. An individual clinician-guided revision outside randomization is recorded as observational care.

This branch estimates adaptive treatment strategies across eligible patients; it is not an N-of-1 crossover of durable therapy. With 60 prospective trajectories in the demonstration preset, the number of randomized nonresponders will be small; the demonstration shows the mechanics and the width of the resulting uncertainty, not a usable comparison.
