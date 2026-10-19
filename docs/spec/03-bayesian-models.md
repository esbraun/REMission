# Bayesian population and measurement models

Specification revision: 2026-10-19. Status: requirements only; no implementation or validation result is asserted.

**Read first:** [00-scope-and-invariants.md](00-scope-and-invariants.md), [01-estimands-and-contracts.md](01-estimands-and-contracts.md), [02-synthetic-dgp.md](02-synthetic-dgp.md). Read linked scenario and evidence entries only when needed.

**Inputs:** versioned upstream contracts and applicable scenario IDs. **Outputs:** the contracts, artifacts and checks specified below. **Acceptance:** relevant G0–G7 evidence in [gates](08-gates-and-release.md); statistical checks use the [validation protocol](07-validation-protocol.md).

## BAYES-01 — Component validation contract

| Input | Target and truth | Comparators and evidence |
|---|---|---|
| Analytic fixtures and model-matched prior draws | Exact posterior; SBC ranks of parameters, marginal contrasts and likelihood-sensitive quantities | Analytic versus sampled posterior; SBC diagnostics and deliberate faults |
| Fixed reference and adversarial DGPs | Standardized 42-day contrasts using independent intervention truth | Regularized/flexible longitudinal models; matched single-decision BCF only |
| Generated trial effects/IPD | Matching source/target marginal contrast | No, complete and robust borrowing; prior conflict and bridge approximation |
| Ordinal ISI and wearable/report records | Category probabilities, expected totals and observed-history predictions | Item versus justified bounded-total model; phase and device shifts |

Use [validation](07-validation-protocol.md) and scenarios S01–S12, S23–S31 as applicable. SBC tests computation; fixed-DGP recovery tests operating characteristics. Neither validates clinical assumptions. [sbc-talts](../evidence/simulation.md#sbc-talts) [sbc-quantities](../evidence/simulation.md#sbc-quantities)

### BAYES-02 — Calibration and model complexity

SBC draws parameters from the actual prior and observations from the matching likelihood. Include derived marginal contrasts and log likelihood as test quantities; parameter ranks alone can miss ignored data. Check posterior-draw dependence and use the documented SBC implementation's dependence-aware rank procedure. Record any thinning and effective independent draw count. Fixed-parameter simulations are not SBC.

Use four chains for final fits; require R-hat <1.01, bulk/tail ESS ≥400 for reported quantities and no unresolved divergences. Record MCMC SE for reported effects and probabilities; extend chains when numerical uncertainty changes the decision. If precision remains insufficient, abstain. Never replace a failed fit with canned estimates. [stan-diagnostics](../evidence/simulation.md#stan-diagnostics)

Start with population effects, then a small prespecified modifier basis, then patient-specific treatment effects when supported. Repeated nights do not create independently randomized patients or blocks. Report pooling sensitivity, modifier uncertainty, likelihood contribution and prior-only status. Complexity is retained only with held-out predictive/decision evidence and acceptable computational behavior.

Add fault fixtures that ignore all data, omit a likelihood block, reverse treatment coding and duplicate observations. Use the appropriate diagnostic for each fault: likelihood-sensitive SBC, analytic posterior disagreement or lineage invariants. The suite must demonstrate that these faults are rejected, not merely produce visually plausible plots.

### BORROW-01 — Marginal borrowing and transport

Initially borrow for one compatible behavioral comparison. Evaluate mixture weights 0, 0.5, 0.9 and 1 as engineering sensitivity settings, with at least two prespecified heterogeneity priors on the marginal ISI scale. Keep between-study heterogeneity and source-to-target bias distinct in the bridge and record the induced joint prior.

Test induced marginal distributions, missing source modifiers, selection shifts, two parameter sets giving the same source average but different target effects, and duplicated IPD/summary/meta-analysis contributions. Source mean agreement does not identify conditional effects. Robust borrowing need not win every scenario; report its failures and cold-start dependence. [robustmap](../evidence/causal.md#robustmap)

### MEASURE-01 — Measurement and temporal validation

Test residual item dependence, phase-dependent item interpretation, overlapping recall windows, diary error, quiet-wake bias and device-version shifts. A model combining reports and wearables does not identify true sleep without measurement assumptions. Compare item and bounded-total models on observable predictions and estimands; do not require recovery of nonidentified latent parameters.

## 7. Bayesian population model and external-evidence borrowing

### 7.1 Primary estimator

Implement hierarchical Bayesian longitudinal g-computation, producing conditional treatment contrasts and posterior policy rollouts. Bayesian g-formula methods support longitudinal intervention simulation, shrinkage, and modular treatment of problematic data.[gformula](../evidence/causal.md#gformula)

Start with transparent regularized outcome and transition models:

- Baseline prognostic functions and clinical-state transitions.
- Patient-level random effects, with partial pooling.
- Treatment-specific effects and a limited prespecified modifier basis.
- Chemotherapy phase, time, accumulated behavioral exposure, and medication carryover.
- Observation/availability processes and a documented missing-data model.
- Intercurrent-event processes consistent with the strategies declared in section 4.
- An ordinal likelihood for ISI items with a shared latent severity (items are not independent, and treating them as such understates uncertainty in the total), or a separately justified bounded-outcome likelihood for the total.
- Separate proximal report/function models for N-of-1 and support decisions.

For each posterior draw, simulate future confounders, delivery/adherence, outcomes, and permitted actions under the specified intervention and continuation policy. Integrate over future states rather than fixing treatment-affected confounders at their observed values.

Do not call this "Bayesian DynamicDML." Longitudinal g-computation and DML have different models and inferential properties. The Bayesian implementation does not inherit double robustness.

Bayesian causal forests (BCF) are a useful single-decision nonlinear benchmark, separating prognostic and treatment-effect regularization and incorporating propensity information.[bcf](../evidence/causal.md#bcf) Stock BCF is not automatically a longitudinal estimator or an importer of published study priors. Keep it as a baseline or later flexible component, not a substitute for the longitudinal estimand.

### 7.2 Borrow evidence at the estimand it actually measures

Construct an evidence registry before fitting:

- Separate randomized treatment-effect evidence, observational estimates, and clinical practice guidance.
- Align intervention versions, comparator, endpoint scale, follow-up, and target population.
- Extract an effect and uncertainty from the original report. Do not manufacture a standard error from a P value or two group means.
- Identify whether trial IPD, covariate distributions, or only aggregate descriptions are available.
- Record leukemia versus other cancer populations, active chemotherapy versus survivorship, blinding, and other transport differences.
- Avoid counting both a trial's IPD and its summary, or its summary and a meta-analysis containing that trial, as independent evidence.

**Runnable-demo rule:** quantitative borrowed effects come from generated synthetic trials. Real publications establish clinical and methodological rationale and populate a clearly separate reference registry. A later real-evidence demonstration requires reviewed quantitative extraction and transport decisions.

### 7.3 Robust prior design

For compatible aggregate study effects, a starting meta-analytic model is:

$$
\widehat d_s \mid d_s \sim N(d_s, \mathrm{SE}_s^2), \qquad
d_s \mid \delta_0, \tau \sim N(\delta_0, \tau^2).
$$

The predictive distribution for a new compatible target study produces a meta-analytic predictive prior $p_{\mathrm{MAP}}(\delta_\star \mid D_{\mathrm{ext}})$. Include prespecified transport uncertainty where populations differ. Robustify it:

$$
p(\delta_\star \mid D_{\mathrm{ext}}) = w\, p_{\mathrm{MAP}}(\delta_\star \mid D_{\mathrm{ext}}) + (1-w)\, p_{\mathrm{weak}}(\delta_\star).
$$

Robust MAP mixtures are established for borrowing historical information, notably historical controls.[robustmap](../evidence/causal.md#robustmap) Applying this construction to transported conditional treatment contrasts is a proposed extension that must be simulation-validated. Commensurate priors provide another established borrowing approach; compare them if needed rather than inventing an untested "Bayesian DML prior."[commensurate](../evidence/causal.md#commensurate)

**Heterogeneity prior.** With few studies the form of the prior on $\tau$ can be decisive for the result, and weakly informative priors such as a half-normal with a scale chosen for the effect measure are the recommended approach.[rover](../evidence/causal.md#rover) The demonstration presets have two to four studies, so:

- Specify the $\tau$ prior on the scale of the marginal ISI contrast and document the reasoning for its scale; do not use an improper or default "vague" prior.
- Report the MAP prior's width and effective borrowing under at least two alternative $\tau$ priors as a standing sensitivity analysis.
- Show the $\tau$ prior alongside the study estimates in the evidence inspection view, so a reader can see that the borrowed distribution is partly assumed.

The initial mixture weight $w$ and transport scale are prespecified. Posterior component probabilities can change with target data; at zero local observations, conflict cannot be learned from nonexistent local evidence. Cap initial effective borrowing through calibrated prior scale and sensitivity analysis.

If there are effect modifiers, a published average estimates an average over the source population:

$$
d_s = E_{X \sim P_s}\left[\Delta_\theta(X; a_s, c_s, K_s)\right] + \epsilon_s,
\qquad \epsilon_s \sim N(0, \omega_s^2),
$$

where $a_s$ and $c_s$ are the source study's intervention and comparator, $K_s$ its follow-up, and $\epsilon_s$ a study-specific bias/transport term.

Map this average to the model using available source covariate distributions or IPD and posterior standardization. If those distributions are missing, explicitly weaken transport and do not invent conditional effects. Shrink unsupported modifier coefficients toward zero with broad enough uncertainty; an average-effect prior is not a tight prior on every patient's effect.

For an ordinal outcome model, impose or calibrate study borrowing on the marginal ISI contrast, not by copying a points-scale study effect onto an ordinal log-odds coefficient.

Implement a versioned study-to-model bridge that standardizes posterior/prior predictions over the source covariates and the target reference population. Start with one compatible behavioral comparison and fixed endpoint; keep other contrasts weakly informed. Test that the induced prior on the reported marginal contrast matches the intended borrowed distribution. Use either an imported MAP prior or a joint external-study likelihood in a given run, not both for the same studies. If the nonlinear bridge is approximate, quantify the approximation in simulation before using its posterior uncertainty.

Study priors for a behavioral program do not establish priors for MED_A versus MED_B, a different behavioral comparison, or reminder timing. Unsupported comparisons start with appropriate weak priors.

### 7.4 Identification and diagnostics

State consistency, sequential exchangeability, positivity, intercurrent-event and missingness assumptions, and source-to-target transport assumptions. Bayesian inference conditions on these assumptions; it does not remove them.[bayescausal](../evidence/causal.md#bayescausal)

Check:

- Eligibility-specific overlap and support for each comparison.
- Covariate balance/assignment models as observational diagnostics.
- Prior predictive behavior, posterior predictive fit, posterior sensitivity to borrowing and to the $\tau$ prior.
- MCMC convergence and effective sample size.
- Outcome and measurement model adequacy across clinical phases.
- Whether the target patient's profile lies outside evaluated population support.
- Behavior under the sharp null (below).

Historical propensity models support overlap assessment. Good balance or posterior fit does not prove absence of hidden confounding.

**The g-null paradox.** The parametric g-formula has a known structural weakness in exactly the setting that motivates it. When time-varying confounders are affected by earlier treatment, some combinations of parametric models cannot represent the sharp null at all, so that with enough data a null effect is rejected with probability approaching one. McGrath, Young, and Hernán recommend avoiding overly parsimonious component models as the practical response.[gnull](../evidence/causal.md#gnull) A Bayesian implementation with parametric transition and outcome models inherits this. Therefore:

- Keep the sharp-null scenario (section 6) as a permanent regression test and report the rate at which the model ranks a plan as superior when no plan has any effect, at the demonstration and evaluation sample sizes.
- Prefer flexible component models where the data support them, and compare against the "transparent regularized" starting models to show how much the null behavior depends on that choice.
- Treat a narrow interval around a nonzero contrast as needing this check before it is shown as a model-backed ranking.

### 7.5 Outputs and updates

For each eligible comparison return:

- Estimand, comparator, horizon, and intercurrent-event strategy.
- Posterior expected difference with a credible interval.
- Probability of a clinically agreed benefit threshold, when a named threshold is configured (section 2).
- Harms and burden as separate outcomes.
- Data-support/extrapolation status.
- Prior-only versus updated evidence, with no-borrowing sensitivity.
- Sources, transport limitations, and model version.
- A reason for abstention when support or readiness is insufficient.

Use a shared longitudinal evidence store. Prefer a joint model for related outcomes where feasible; otherwise define which component owns each observation and how uncertainty is propagated.

Refit cumulative distinct data using the original prior, or update sequentially using only new likelihood contributions. Do not reuse the posterior as a prior and then refit the same old observations. Do not feed an N-of-1 posterior back as "independent evidence" while also fitting its underlying observations.
