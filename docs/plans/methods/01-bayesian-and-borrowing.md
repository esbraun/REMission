# Bayesian models, borrowing and computation

Revision: 2026-10-19. Planned implementation only. Read [library decisions](00-library-decisions.md), [canonical Bayesian requirements](../../spec/03-bayesian-models.md) and the assigned G0-G2 contracts first.

## BAYES-LIB — Implementation sequence

1. Qualify and pin PyMC, its numerical dependencies and compatible ArviZ packages. Explicitly select native NUTS and 64-bit computation; do not let the presence of an optional sampler silently change a run. Record BLAS/thread settings and the actual returned draw container/API.
2. Implement normal-normal and beta-binomial fixtures using library distributions; compare to analytic posterior means, variances, quantiles and predictive probabilities before building the full model. Preserve independent expected calculations.
3. Implement noncentered patient effects where appropriate, prespecified modifier shrinkage, phase/time terms and the declared clinical-state transitions. Add carryover, accumulated behavioral exposure, adherence, intercurrent events and observation processes according to the temporal factorization. The learner receives available-at observations only.
4. Use a shared-severity ordinal item likelihood with ordered cutpoints and identifiable parameterization. Observed ordinal outcomes can coexist with continuous sampled parameters; explicitly sampled discrete latent states require marginalization or a compatible sampler. Do not assume external NUTS will handle them. Generate item categories and expected total ISI as separate predictive summaries. A bounded-total alternative must retain its existing justification and comparison requirements.
5. Build posterior intervention rollouts over future states, adherence and allowed continuation policies. Use posterior predictive primitives for distributions, but implement interventions explicitly; ordinary predictions conditional on observed treatment-affected histories are not g-computation. Batch/vectorize draws and patient trajectories without changing their statistical roles.
6. Add MAR observation models and declared MNAR sensitivity settings. Do not treat library imputation, an omitted reward or successful convergence as a missingness correction. Keep undefined post-death outcomes outside symptom likelihoods.
7. Export posterior contrasts, threshold probabilities, predictive quantities, support status, prior-only status and diagnostics under the existing contracts. Refit cumulative distinct data with the original prior or add only new likelihood terms to an appropriate sequential update; never count old observations twice.

Use ArviZ's version-compatible routines for rank-normalized R-hat, bulk/tail ESS, MCSE and predictive graphics. Preserve chain/draw axes. Diagnostics apply to reported marginal contrasts and tail probabilities, not only regression coefficients. Use four final chains, R-hat <1.01, bulk/tail ESS >=400 and no unresolved divergences; extend sampling when decision precision is inadequate, otherwise abstain. Log treedepth/energy warnings where supplied.

Compare predictions with patient-held-out, forward-time and site-shift data appropriate to the target. Do not use ordinary row-wise LOO or random folds as a substitute for those tasks. If using PSIS predictive comparisons, define the held-out unit and inspect Pareto diagnostics; refit or use the prespecified held-out design when the approximation is unreliable.

## BORROW-LIB — RBesT preparation and Python import

1. Generate compatible synthetic external studies and validate the evidence registry: contrast, sign, endpoint, horizon, source population and source identifiers. Quantitative inputs remain synthetic.
2. Fit the normal-effect meta-analytic model with RBesT gMAP, using explicit heterogeneity and population-bias assumptions. Run the two prespecified heterogeneity priors; keep bias/transport uncertainty distinct from between-study heterogeneity.
3. Approximate the MAP predictive distribution with a normal mixture using automixfit. Preserve the original draws, fitted mixture and density/CDF/quantile discrepancy report. Do not equate mixture fitting success with an adequate approximation.
4. Add the explicit weak normal component with robustify. The project uses w for the informative MAP fraction; RBesT's robustify weight is the weak-component fraction, so pass 1-w. Include exact boundary cases w=0 and w=1 without relying on an API to accept a degenerate robustification call. Preserve the prescribed w values 0, 0.5, 0.9 and 1.
5. Export JSON components with weights, means and standard deviations in marginal ISI points; require finite parameters, positive scales and normalized nonnegative weights. Record which weak-component scale was used rather than accepting an undocumented unit-information default. Preserve RBesT version, study/prior hashes, seeds and scale conventions.
6. Import the artifact through PyMC mixture distributions. Check density, quantiles and draws against RBesT and analytic single-normal limits. Record prior effective information as a method-dependent diagnostic; do not present it as the number of independent local patients or nights.
7. Implement the versioned source/target standardization bridge. A points-scale mixture cannot simply become an ordinal log-odds prior. Check the induced marginal prior and source-to-target discrepancies under the configured modifier/covariate distributions. Do not assign the same average-effect prior independently to every patient.
8. Fit target data with either the imported prior or a joint external-study likelihood, never both for the same studies. Preserve no-borrowing and complete-borrowing comparators, transport sensitivity and prior-conflict behavior. Cold-start posterior weights cannot learn target conflict from absent data.

The marginal bridge is project-owned research code. RBesT's established univariate prior construction does not validate that bridge. Scope any approximation benchmark to the induced marginal quantities, including tails relevant to superiority decisions; freeze tolerances before confirmation using the existing numerical-precision requirements.

## SBC-LIB — Use the actual fitted model

Use R SBC with a custom backend that launches the Python fit and imports actual draws, diagnostics and derived test quantities. Do not validate a convenient Stan reimplementation and call that calibration of PyMC. Pin the SBC package revision when it is not supplied through a stable package release.

For each family, draw from the actual prior, generate from the matching likelihood, fit, and retain parameters, marginal contrasts and likelihood-sensitive quantities. Preserve unthinned chain draws; use the documented dependence-aware rank procedure and record rank thinning/effective draw counts. Export unresolved fits as failures, not uniform ranks or deleted repetitions.

Start with tractable analytic fixtures, then the shared-severity, borrowing and serial-dependence components. Keep BAYES-02 seeded faults: ignored data, omitted likelihood block, reversed treatment and duplicated observations. Rank/ECDF plots, analytic checks and lineage checks must reject the appropriate faults. Follow existing 1,000-repetition SBC requirements; absence of an obvious plot discrepancy is not proof of correctness.

## BCF-LIB — Restricted nonlinear benchmark

Fit StochTree BCF only on the declared matched single-decision fixture. Freeze treatment coding, outcome scale, prognostic/modifier information, propensity inputs and patient-level held-out splits. Keep oracle fields out of features and tune without confirmation data.

Use documented multiple independent chains and retain posterior effect draws. Diagnose marginal effects and predictive summaries with applicable common diagnostics; HMC-specific divergences do not apply to a tree sampler. Evaluate bias, RMSE, coverage, support and runtime against the same target. A predictive improvement or a narrow conditional interval does not establish longitudinal recovery.

## Acceptance and acceleration

Map all steps to BAYES-01/02, BORROW-01, MEASURE-01 and G2. Required evidence includes analytic agreement, induced prior checks, SBC/fault rejection, reference recovery, g-null behavior, cold start, prior conflict, measurement shifts and final-scale diagnostics. Existing sample sizes, repetitions and failure criteria remain unchanged.

Consider nutpie after the native implementation passes analytic checks. A targeted same-model pilot compares cold compilation, warm fitting, estimand ESS/time, MCSE, peak memory, divergences and accepted-fit yield. Require posterior agreement within combined numerical uncertainty and the same gates before switching; use actual workload evidence where public benchmarks do not resolve the choice. Record a new sampler configuration/version, never switch after a failed fit without reporting it. No GPU/NumPyro bake-off is required unless a remaining resource bottleneck justifies it.
