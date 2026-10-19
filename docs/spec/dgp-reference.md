# Reference DGP engineering defaults

Version 1, 2026-10-19. These equations are a transparent starting synthetic environment, not a calibrated model of leukemia. The G0 reviewer must verify the equations/units and any additional implementation parameters before G1. Changes require a new manifest version. See [generator rules](02-synthetic-dgp.md) and [scenarios](scenario-catalog.md).

## Analytic fixture parameters

All numbers are engineering choices; these fixtures are distinct from the clinical-scale reference generator.

| Fixture | Exact construction and check |
|---|---|
| Normal posterior | mu~Normal(0,2); y_j~Normal(mu,1), n=20. Posterior variance v=1/(1/4+n), mean v*sum(y). Compare sampled moments/intervals allowing measured MC error |
| Beta posterior | p~Beta(2,3); k~Binomial(20,p). Posterior Beta(2+k,23−k); compare analytic moments/quantiles |
| Constant effect | X~Normal(0,1), A~Bernoulli(0.5), Y=1+X−A+e, e~Normal(0,1), n=200. ATE=−1 |
| Modifier | M~Bernoulli(0.5), Y=1+X+A*(2M−1)+e. CATEs=−1,+1; marginal ATE=0 |
| Two-period system | L0~Bernoulli(0.5); A0 probability expit(−0.5+0.5L0); L1 probability expit(−1+0.8L0+0.7A0); A1 probability expit(−0.5+0.8L1+0.2A0); Y=L0+L1−A0−2A1+Normal(0,1). Enumerate L0,L1 under fixed regimes; −1 is not the total A0 effect |
| Ordinal expectation | One item uses the reference cutpoints at severity 0 or 1. E[item]=sum over k=1..4 of P(item≥k); seven equal items have expectation seven times that value regardless of dependence |
| Contextual policy | M~Bernoulli(0.5); reward=1+A*(2M−1)+Normal(0,1). No-action and always-action values=1; choose A=M has value=1.5; logging p=0.5 |
| Escalation tree | A0~Bernoulli(0.5); response R probability 0.4+0.2A0; among R=0 randomize A1 with p=0.5; responders A1=0. Y=2+A0+R+2*(1−R)*A1+Normal(0,1). For initial a and nonresponder choice b, strategy value=2+a+(0.4+0.2a)+2*(0.6−0.2a)*b |

Normal/beta fixtures have exact posterior distributions; causal/policy fixtures have exact expectations, not noiseless individual outcomes. In the observational-first-stage escalation fixture, let X~Bernoulli(0.5), P(A0=1|X)=0.2+0.6X, response probability=0.3+0.2A0+0.2X and add X to Y. Randomize A1 among nonresponders as above. Enumerate over X under interventions for strategy truth; adjustment for X is required. Do not transfer the unadjusted randomized formula to this fixture.

## Population and time

Patients are independent before pooled policy learning. Draw X~Normal(0,1), modifier M~Bernoulli(0.5), measured common cause U~Normal(0,1), prognostic random intercept b~Normal(0,0.2), and phase offset J uniformly from integers 0–20. Baseline site is uniformly 0,1,2; default site has no effect and site-shift cells add a declared intercept. X,M,U,site and phase are exported. b is latent and never directly drives assignment.

Use integer days −14 through 84; initialize states at day −15 to zero. Steroid indicator S_t=1 when (t+J) mod 21 is 0,1,2 or 3. Phase term V_t=sin(2*pi*(t+J)/21). Export the schedule. Base interruption processes are disabled; dedicated cases enable them below.

## State equations and units

All L and z states below are dimensionless. Normal distribution second arguments denote standard deviations. Innovations are independent over time/processes except the specified L covariance. clip means clipping to the stated bounds; expit is logistic.

| State | Reference equation/default |
|---|---|
| Clinical L_t=(pain,nausea,distress) | 0.6 L_(t−1) + 0.15 z_(t−1) + 0.25 S_t + 0.1 X + 0.1 U − 0.1 T_(t−1) + e_t, applied to each coordinate; e covariance has diagonal 0.09 and off-diagonal 0.027 |
| Behavioral skill B_t | min(1, 0.995 B_(t−1) + 0.08 D_t*(1−B_(t−1))); D_t is delivered continuing behavioral program indicator |
| Drug carryover C_(k,t) | lambda_k*C_(k,t−1)+(1−lambda_k)*Taken_(k,t); lambda=2^(−1/h), h=1 day by default, h=0 means lambda=0 |
| Rebound R_t | 0.5 R_(t−1)+0.5*I(a drug taken yesterday is stopped today); zero when rebound-disabled |
| Severity z_t | 0.5 z_(t−1)+0.2 X+0.15 U+0.15 mean(L_t)+0.2 S_t+0.1 V_t+b−0.15 B_t−0.20 C_(A,t)−0.12 C_(B,t)+0.2 R_t−0.08 A_t+eta_t; eta~Normal(0,0.4) |
| Daily quality Q_(t+1) | clip(7−2 z_t+Normal(0,0.5),0,10); larger is better |
| Function F_(t+1) | clip(7−z_t−0.4 mean(L_t)−0.5*(C_A+C_B)+Normal(0,0.5),0,10) |

T is the assigned behavioral-program indicator; D is delivered program. Medications and support are distinct assignments. Before day 0 all treatment/support indicators are zero. Daily fatigue can be exported as 10−F from the previous morning, not the future morning.

At scheduled observational visits, assign behavioral T with probability clip(expit(0.4 X+0.5 mean(L_t)+0.3 U),epsilon,1−epsilon), epsilon=0.2. Randomized fixtures use 0.5. Hold the assigned program between visits. Delivery has probability expit(1.5−0.2 mean(L_t)); overrides are absent in reference and added in explicit scenarios. Causal assignment contrasts simulate this delivery mechanism rather than conditioning on adherence.

Medication experiments use only MED_A and MED_B; the reference visit behavioral comparison has neither medication. An N-of-1 fixture uses equal-probability randomized AB/BA block pairs with seven active days per block and configurable washout; default two washout days is purely synthetic. Probability of taking the assigned medication is 0.9. Rescue, when enabled, is a separately logged fictional exposure with probability expit(−3+0.5 z_(t−1)); its same-night severity contribution is −0.1. Use observed previous quality, not hidden severity, for actual learner decisions.

Available support is Bernoulli(0.5) in MRT fixtures; adaptive policy replaces only this assignment mechanism. Default burden limit is at most one prompt/day and four per rolling seven days. Holds/consent constrain availability. Fixed-support comparator offers a prompt on the first four eligible weekdays each week subject to the same burden limit.

## Measurement and observation

At morning assessment day d, recall severity is mean(z_(d−14),...,z_(d−1))+Normal(0,0.2). Seven ordinal items use logistic category probabilities P(item≤c)=expit(kappa_c−recall−offset_j), cutpoints (−1.5,−0.5,0.5,1.5), offsets (−0.3,−0.2,−0.1,0,0.1,0.2,0.3). Conditional item errors are independent in reference; shared recall already induces marginal dependence. ISI is their integer sum. Intermittent assessment and overlapping windows are preserved.

For illustrative sleep measurement, define true wake minutes W=clip(60+20 z_t,0,480) and total sleep 480−W. Diary sleep adds Normal(0,20) minutes; wearable sleep adds 0.3 W+Normal(0,15) minutes, clipped to [0,480]. These are engineering measurement errors, not Oura validation estimates. A device-shift fixture adds 30 minutes from day 42.

Reference reports are complete. MCAR uses Bernoulli observation with requested rate. MAR logit observation=a−0.4*(10−previous observed quality)/2−0.2*current observed pain; use baseline quality 7 when history is absent and include missing-history indicators. MNAR adds 0.5*(current unobserved quality−7); action-dependent reporting adds an action-by-current-quality term. Calibrate a independently as specified in the scenario catalog. Current unobserved outcomes never enter learner-side reporting models as known data.

Reference uploads arrive at measurement time. Delay fixtures add 0,1,3 days with probabilities 0.7,0.2,0.1. Duplicate and corrected records retain original event time and distinct transaction lineage. Wearable availability follows the same default, with a separate stream.

## Events and perturbations

In interruption fixtures, death hazard is expit(−7+0.3 mean(L_t)+0.2 U); hospitalization hazard among living outpatients is expit(−5+0.4 mean(L_t)+0.2 U). Death is absorbing. Admission lasts seven days unless death occurs; suspend assignments during admission. Record the event before subsequent decisions. Future symptom observations are generated only when defined; conditional day-42 outputs follow EST-INT. These rates are synthetic, not clinical estimates.

Regimen-change fixture switches the steroid window to phase days 0–6 from day 42. Discontinuation fixture stops behavioral delivery after day 21 with probability expit(−2+0.3 mean(L_21)); retain assignment. Hidden-confounding fixture withholds U while U continues to influence assignment and severity.

Observed modifier fixture replaces medication A coefficient −0.20 with −0.20−0.25*(2M−1); no-heterogeneity fixture removes modifier effects but retains prognostic differences. Nonlinear variant adds 0.15*(L_pain^2−1) to severity; heavy-tail variant replaces severity innovations with scaled t(3) noise having SD 0.4. Habituation replaces support coefficient by −0.08/(1+0.2 cumulative prompts); delayed-harm fixture adds +0.15 times yesterday's prompt. Compound cases combine only catalog-specified perturbations.

## Synthetic external trials and truth

Generate four 1:1 randomized behavioral trials with n=150,180,220,250, same 42-day endpoint and reference source covariate distributions. Derive study mean differences and SEs from generated patient outcomes. Source-population shift uses X~Normal(1,1) and P(M=1)=0.8. Compatibility/conflict modifications are versioned and calibrated by independent source intervention rollouts to achieve requested marginal shifts; never copy a marginal points effect into an ordinal coefficient.

Store IPD or its summary as the likelihood input for a study, not both. Real references remain rationale only. Independent truth implementations enumerate Layer A and roll out this structural system for Layer B; they do not reuse learner predictions.
