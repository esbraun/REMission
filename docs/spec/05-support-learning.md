# Support learning and policy evaluation

Specification revision: 2026-10-19. Status: requirements only; no implementation or validation result is asserted.

**Read first:** [00-scope-and-invariants.md](00-scope-and-invariants.md), [01-estimands-and-contracts.md](01-estimands-and-contracts.md), [02-synthetic-dgp.md](02-synthetic-dgp.md), [04-individual-experiments.md](04-individual-experiments.md). Read linked scenario and evidence entries only when needed.

**Inputs:** versioned upstream contracts and applicable scenario IDs. **Outputs:** the contracts, artifacts and checks specified below. **Acceptance:** relevant G0–G7 evidence in [gates](08-gates-and-release.md); statistical checks use the [validation protocol](07-validation-protocol.md).

## SUPPORT-LIB — Estimation, policy and evaluation libraries

Follow the [support implementation sequence](../plans/methods/02-experiments-and-support.md): statsmodels WLS with explicit participant-clustered small-sample/df-corrected inference, offline MRTAnalysis coefficient/reference comparisons, shared PyMC hierarchical bandit inference and COBA fixed-policy contextual IPS/DR evaluation. scikit-learn supplies declared nuisance models with leakage-safe training. [Library comparison](../plans/methods/00-library-decisions.md); [software sources](../evidence/software-libraries.md).

Generic cluster correction differs from MRTAnalysis's hat-matrix correction; validate the locked Python procedure rather than assert identical SEs. COBA's defaults do not establish admissible nuisance splits or adaptive/cohort uncertainty. Project code retains final probability bounds/logging, frozen policies, observation assumptions and eligibility. Fast generic bandits are optional comparators, not silent replacements for required hierarchical pooling. No library benchmark has been executed.

## SUPPORT-01 — Initial validated action set and executable policy

For the restricted seven-configuration PoC, [S2-CANONICAL-01](../implementation/poc-analytics-contract-20261021.md#s2-canonical-01--batch-working-policy-and-saved-prediction) is the proposed canonical batch-model, chain-precision and saved-prediction refinement. Its independent acceptance does not enable S2 source/runtime or replace broader G4 qualification.

Start with binary prompt/no-prompt, one decision per daily outcome window. Preserve extensibility without describing multi-action or overlapping-window inference as validated. Follow S20–S26 and S29–S32.

Execute in order: clinical/consent/availability/burden constraints → eligible set → selection probabilities → bounds → normalization/feasibility check → persist final distribution → draw/persist assignment → delivery/outcome events. Never log pre-mask or pre-clipping propensities as executed probabilities.

For two eligible actions use [0.1, 0.9] engineering bounds. One permitted action is deterministic and exempt from exploration bounds; no eligible action produces a logged unavailable decision. Excluded actions have zero mass. Reject infeasible configurations (including k times the probability floor >1), rather than silently change bounds. Record Thompson probability approximation settings and error; check normalization and final sampling frequencies against the actual final policy.

Freeze the complete patient-specific support mechanism during blocks/washout: parameters, action versions, probabilities, context mapping and burden behavior. Global updates for other patients cannot alter this snapshot. Clinical holds may override it as documented deviations.

## MRT-01 — Estimator and uncertainty contract

For binary A, declare reference probability q(S), executed probability p(H), centering A−q(S), and weight q(A|S)/p(A|H). Fit the prespecified effect-moderator basis with an independence working correlation and participant-clustered sandwich variance, using a documented small-sample correction. Reference q=0.5 in the initial two-action fixture. Deterministic/unavailable points are logged but are not two-action randomized contrasts.

Freeze the moderator basis, missingness assumptions and correction version in the analysis protocol. Validate empirical coverage at cohort sizes 60 and 240. Shared next-morning outcomes must not be duplicated as independent rewards for several decisions. Adaptive pooled learning creates dependence across participants; ordinary participant-clustered MRT standard errors are not automatically valid there. Validate a separately justified adaptive estimator or retain adaptive estimates as exploratory. [wcls](../evidence/experiments.md#wcls) [adaptive](../evidence/experiments.md#adaptive)

## MISS-01 — Reporting is part of the data process

Keep pending, missing and undefined distinct; never assign missing a reward value. Complete-case/no-update behavior is a comparator, not a missingness correction. Specify an MAR observation model with positivity checks and a weighted or modeled analysis, plus MNAR sensitivity parameters. Include equal latent rewards with action-dependent reporting that makes the observed means differ. Monitoring missingness alone does not fix selection bias.

Report policy value and reporting rates jointly. If plausible prespecified missingness sensitivities reverse action preference, return to fixed support or pause adaptation. Simulated unobserved outcomes belong only to the evaluator, including when comparing imputation methods.

## OPE-01 — Policy and learning evaluation

Start with fixed target-policy contextual IPS and doubly robust estimates, evaluated against on-policy simulator truth. Restrict comparisons to supported eligible actions; report weight dispersion/effective sample size and support failures. Define clipping as a changed estimator with bias, not a free numerical repair. Do not conflate these with long-horizon OPE. [ope-dr](../evidence/experiments.md#ope-dr)

Compare no support, fixed approved support, fixed randomization/MRT and bounded adaptation on independent complete cohort runs. Separate reward, burden and distal ISI. Evaluate habituation/delayed harm, pooled dependence and reporting bias. A hidden-state oracle is privileged; label the observed-history benchmark separately. [pooling](../evidence/experiments.md#pooling) [netflix-artwork](../evidence/industry.md#netflix-artwork) [recsim](../evidence/industry.md#recsim)

## 9. MRTs, contextual bandit, and optional offline RL

### Safe action envelope

Daily actions might be no prompt, an approved diary reminder, or delivery timing of an approved behavioral exercise. Specify action content, maximum burden, timing, and patient preferences before the experiment.

Availability is determined before assignment: clinical holds, sleepiness restrictions, patient pause, missing required data, missing or withdrawn consent, an active N-of-1 block under the freeze rule, and scheduling constraints can make the action unavailable or fix its probability. No exploration probability is assigned to excluded actions. Medication selection, dose changes, sleep-restriction parameters, and oncology medication changes remain outside this bandit.

### Learning progression

1. **MRT stage:** randomize permitted support actions at eligible decision points with known probabilities; estimate proximal effects and context interactions.[mrt](../evidence/experiments.md#mrt)
2. **Bounded bandit stage:** use a hierarchical contextual Thompson-sampling policy with partial pooling, action centering, and prespecified probability/burden bounds.[actionbandit](../evidence/experiments.md#actionbandit)[pooling](../evidence/experiments.md#pooling)
3. **Offline extension:** assess candidate longer-horizon policies in the simulator and, when appropriate, with off-policy estimators on logged data.[ope](../evidence/experiments.md#ope)

IntelligentPooling is a research basis for user-level pooling and online adaptation; use its ideas with the app's action set and validate that implementation. It does not supply validated leukemia insomnia treatment policies.

### MRT estimand and analysis

The MRT's primary quantity is a **causal excursion effect**: the effect of the current action versus none on the proximal outcome among available decision points, marginal over the history produced by the randomization policy in force. Two consequences follow from the MRT literature and must be implemented rather than left to a generic regression:

- Standard longitudinal regression methods (GEE or random-effects models with time-varying covariates) are not guaranteed to estimate this effect consistently when treatment is time-varying. Use the weighted and centered least squares (WCLS) estimator, or an equivalent, for the primary and moderation analyses.[wcls](../evidence/experiments.md#wcls)[mrt](../evidence/experiments.md#mrt)
- The effect is defined conditional on availability and relative to the randomization probabilities that generated the data, so both must be logged at every decision point, including decision points where the patient was unavailable.

The Bayesian hierarchical model that drives the bandit is a working model for action selection. It is not the inferential analysis of the MRT.

### Reward and logging

Use a prespecified proximal patient-reported outcome and support burden; retain distal ISI/function as separate evaluation outcomes. Do not optimize an opaque Oura score, deep-sleep percentage, or notification engagement as a substitute for insomnia benefit.

Because the reward is patient-reported, it will often be missing, and missingness is likely to be worse on bad nights. Use MISS-01: no fabricated reward, a declared observation model and MNAR sensitivities. A no-update/complete-case approach is an explicitly biased-risk comparator, not the primary correction.

Record eligibility, availability, context available before assignment, all eligible actions, assignment probability, policy version, delivered action, override, and outcome window. The assigned action's propensity is not the probability that a patient subsequently complied.

Compare fixed randomized, fixed support, and adaptive policies. Check habituation and delayed effects. If previous prompts materially influence later states/outcomes, document the limitation of the myopic bandit and evaluate a richer offline model.

Use estimators/inference appropriate to adaptive assignment rather than ordinary independent-sample confidence intervals. With adaptively collected data, sample means and plain inverse-propensity estimates need not be asymptotically normal, and the available corrections rely on known assignment probabilities that satisfy stated conditions.[adaptive](../evidence/experiments.md#adaptive) This is the reason for the prespecified probability floor and ceiling on every eligible action: without them the bandit can drive an arm's probability toward zero and make later inference on that arm unreliable. Logging propensities alone does not guarantee a valid off-policy estimate; examine support, missingness, and the assumptions of the selected estimator.

Clinical hard constraints cannot be offset by a higher reward. Runtime checks enforce them independently of the learner.
