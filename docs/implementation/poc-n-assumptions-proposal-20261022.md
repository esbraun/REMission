# P3 N0/N1 pooling and adherence proposal

2026-10-22. **Proposed, not admitted or implemented.** Assigned selector: `gpt-6-astra`, medium. Own checkout: `C:/Users/erics/Documents/Projects/REMission-worktrees/poc-n-assumptions-astra-261022`; branch `plan/poc-n-assumptions-20261022`; verified clean base `2c100bcdc45c96c9f973d702ef4ea895571d1bb7`. No applicable AGENTS.md was found. This document alone is the candidate. Independent fresh Astra critique and acceptance precede canonical amendments, model/config admission and dependent execution.

Read the frozen numerical checkpoint through this checkout's Git object `1e1c27dfaaba217cff93e5dc09afdbc30e2b13ef:docs/implementation/poc-n-methods-science-checkpoint-20261022.md` and factual helper `ff63f4d698c3157bd5fc9e326ab33256bd3a322e:docs/implementation/helpers/poc-n-methods-existing-seams-20261022.md`. Neither is model acceptance. No other worker's worktree/WIP, unaccepted visit-cohort source or private generator implementation was inspected. No model build, test, fit, container, database or browser action was performed.

## What is already specified and what needs a choice

References below are to the accepted base; section anchors and named code symbols make their scope explicit.

| Authority | Already determined | Still underdetermined |
|---|---|---|
| [Analytics contract, Inputs, clocks and execution](poc-analytics-contract-20261021.md#inputs-clocks-and-execution), paragraphs beginning “For the restricted visit” and “All patients” | Reduced H*, common available-at cutoff, declared compatible owned cohort permitted, research/interactive separation, same learner/evaluator projection | Whether the first N implementation actually pools and which nuisance parameters pool |
| [Visit model](poc-analytics-contract-20261021.md#visit-model-and-assignment-contrast), six model bullets | Baseline/background hierarchy, scalar unindexed phase/AR/noise priors, rounded quality/ISI likelihood, Beta(1,1) adherence and estimated observation rate | Adherence component and patient axes; observation-rate prior/axes |
| [N extension](poc-analytics-contract-20261021.md#minimal-reversible-n-of-1-extension), final two paragraphs | Medication/rebound population Normal(0,3), patient SD HalfNormal(1); same grid/background/AR/observations; N0 changes only medication design; expected seven-night quality target | Concrete cohort unit and adherence factorization |
| [Individual experiments, N-of-1 branch](../spec/04-individual-experiments.md#n-of-1-branch) | Hierarchical pooling across trials is supported; patient effects, trend, carryover, rebound, serial correlation and frozen support | No explicit complete parameter-axis table |
| [P3 and PA6](poc-protocol-task-plan-20261022.md#small-implementation-packages-in-order), [POC-VAL](../spec/07-validation-protocol.md#poc-val--first-ablation-study) | Paired N0/N1 at36/72; same priors/H*; research panels12; independent panels as replication units | Panel size alone does not define a shared posterior or an adherence hierarchy |
| [protocol_request.py](../../contracts/domain/protocol_request.py), `N_PRIOR_REF`, `IDENTITIES`, `ProtocolInput`, `require_executable` | Strict purpose-bound v1 model/prior stubs; sorted common-cutoff cohort envelope; empty executable allowlist; boundary fixture cannot complete | Stubs do not freeze an executable model or justify silently replacing their hashes |

**A new scientific choice remains.** Recommend one fixed cohort model with patient-specific independent background and medication adherence probabilities. The unindexed phase/AR/noise parameters below interpret the existing visit equations as shared scalars; cohort selection and adherence/observation axes are explicit new restrictions. This is not a new model-selection study. The private separate .85 stream cannot settle the learner's adherence law and is not a learner constant.

## Fixed posterior unit and parameter axes

Fit one joint posterior per declared compatible N cohort, review cutoff and N0/N1 purpose. The target is one explicitly identified member, not a population-average effect. Research uses the predeclared 12-member N panel per independent run; no visit/support patients or external studies are added. Interactive use takes an explicitly selected owned compatible N panel; a declared singleton is the J=1 case of this identical hierarchy, never a different marginal prior or evidence of across-patient learning. No implicit whole-owner pool or outcome-based member selection. Freeze membership before consuming outcomes for selection, record it with request/input hashes, and reuse exactly the same cohort for paired N0/N1. Refit cumulative distinct records from the original prior.

All members must have reached the requested common cutoff and the same scheduled review day36 or72, share the public law/template and uninterrupted continuation/no-prompt restriction, and pass lineage/ownership/history checks. A malformed or incompatible member rejects the declared request; do not silently drop it. Target patients with fewer than two randomized blocks per arm remain inconclusive even if other members supply arm information. Such a member's otherwise valid history may inform the cohort hierarchy; its own comparison is withheld. This rule is fixed for both models, and arm counts use assignments, not nights or taken doses. Earlier targets are unavailable. Paused/terminated or changed-background histories do not enter this restricted uninterrupted fit.

Let i=1..J index patients, t index consecutive nights relative to each patient's public origin, and k in {C,E,A,B,R} index continuing background, escalation background, MED_A, MED_B and rebound amplitudes. The restricted N background has E=0; retaining its original prior coordinate preserves the visit background hierarchy without asserting escalation identification. All listed prior innovations and hyperparameters are mutually independent unless their dependence is displayed.

| Quantity | Shared across cohort | Individual axes and law |
|---|---|---|
| Baseline | mu_b ~ Normal(19,5); s_b ~ HalfNormal(3) | b_i=mu_b+s_b*v_bi, v_bi ~ Normal(0,1) |
| Background amplitudes | mu_C,mu_E independently Normal(0,4); s_C,s_E independently HalfNormal(1) | beta_ki=mu_k+s_k*v_ki, k=C,E; independent standard-normal deviations, no fitted correlation |
| Medication amplitudes | mu_A,mu_B independently Normal(0,3); s_A,s_B independently HalfNormal(1) | beta_Ai,beta_Bi with the same independent noncentered formula |
| Rebound amplitude | mu_R ~ Normal(0,3); s_R ~ HalfNormal(1) | gamma_i=mu_R+s_R*v_Ri; independent standard-normal deviation |
| Phase | a ~ Normal(0,1), public period21 and patient-relative t | No patient-specific a or phase shift |
| Residual process | rho ~ Uniform(-.95,.95); sigma_e ~ HalfNormal(2) | Independent innovations epsilon_it ~ Normal(0,1); patient-specific e_it paths |
| Measurement SDs | sigma_ISI ~ HalfNormal(2); sigma_Q ~ HalfNormal(1) | Independent measurement errors per patient/record, conditional on shared SDs |
| Quality observation rate | No shared rate or learned hyperprior | q_i ~ Beta(1,1), updated only from that patient's resolved quality observation indicators |
| Adherence | No shared probability or learned hyperprior | p_Ci ~ Beta(1,1), p_Mi ~ Beta(1,1), independent across patient and component; medication probability shared between A/B within patient |

This supplies outcome partial pooling, complete pooling of phase/AR/noise, and no adherence/observation-rate pooling. Those are assumptions, not recovered facts about patients. A cohort changes a target's posterior through outcome hyperparameters and nuisance parameters; it does not change the patient being targeted. A singleton retains both hierarchy levels and their uncertainty. Sparse background variation can leave baseline/background decomposition prior-sensitive; do not fix an unidentified coefficient to private truth or claim individual identification.

## Complete restricted model and likelihood ownership

Use the full daily grid t=-13,...,T, with e_i,-14=C_i,-14=E_i,-14=M_Ai,-14=M_Bi,-14=R_i,-14=0 and no pretreatment medication assignment. The untreated baseline is nights -13..0; infer no adherence failures on these unassigned nights. For historical assigned nights, binary taken indicators come only from resolved typed component deliveries:

```
C_it = .65*C_i,t-1 + .35*I(taken behavioral_continue)
E_it = .80*E_i,t-1 + .20*I(taken behavioral_escalate)   # zero in this restriction
M_jit = .5*M_ji,t-1 + .5*I(taken MED_j), j=A,B
R_it = .5*R_i,t-1 + I(assigned_i,t-1=MED_B and assigned_it!=MED_B)
D_jit = M_jit for N1; I(taken MED_j) for N0
e_it = rho*e_i,t-1 + sigma_e*epsilon_it
z_it = b_i + a*sin(2*pi*t/21) + e_it
       - beta_Ci*C_it - beta_Ei*E_it
       - beta_Ai*D_Ait - beta_Bi*D_Bit + gamma_i*R_it
```

Positive medication amplitudes reduce burden; positive rebound increases it. Negative amplitudes remain allowed. R follows assignment cessation, including washout, not missed doses. Known washout has zero medication input but retained M/R; it is not clean control. Unknown/offered/delivered-only stages are not resolved taken/not-taken statuses. Reject incomplete required exposure history before model construction; do not map missing rows to zero. Require consistent assignment linkage, action, stage and binary adherence; lineage resolves correction/duplication before ownership. Every valid nightly C delivery has one C adherence contribution; every assigned MED_A/B delivery has one M contribution. Washout, support/no-prompt deliveries and unassigned baseline nights contribute to neither medication successes nor failures. Operational evidence remains in H* but is not an extra quality/ISI observation.

For each observed quality value, the likelihood is that of Q_it=round_.001(clip_[0,10](Normal(10-z_it/3,sigma_Q))). For scheduled ISI totals use I_ir=round_1(clip_[0,28](Normal(mean of z over the record's14 recall nights,sigma_ISI))). Use interval probabilities with infinite boundary bins; never multiply seven deterministic item partitions. Keep missing nights on the latent grid. The original measurement/noise laws and recall alignment apply identically to both models. Scheduled ISI is consumed once if available and valid; no invented scheduled outcome or separate ISI observation-rate parameter.

For each patient's typed adherence ledger let n_C/n_M be eligible resolved opportunities and s_C/s_M successes. The Bernoulli likelihood times independent Beta(1,1) priors yields independent posterior probabilities Beta(1+s_C,1+n_C-s_C) and Beta(1+s_M,1+n_M-s_M). Historical exposures are known regressors given H*, so outcome data do not supply extra adherence counts. Implement either the Bernoulli likelihood with prior or these conjugate posterior draws, never both. Across future nights, component draws are conditionally independent given their patient probabilities; across A/B counterfactual branches common random numbers may couple them for precision. There is no medication-specific A/B adherence contrast in this restricted law.

For q_i count resolved designated daily-quality indicators due and available by cutoff: observed=1, explicitly missing=0, pending excluded. No count for absent unclassified records; required unresolved exposure remains a separate rejection. Use q_i|H* ~ Beta(1+observed,1+missing). This MCAR reporting model cannot repair informative missingness. Observation simulation is for reported availability/predictive displays; do not multiply quality by q_i, score unreported quality as zero, or condition the primary contrast on a simulated response subset. “Reported quality” denotes the rounded/clipped measurement scale's expected value, not a missing-as-zero endpoint. This makes explicit the existing expected-quality interpretation; changing to responder-only or observed-sum outcomes would require a new estimand.

## Patient expected assignment contrast

For target i and retained joint posterior draw u_m from p(u|H*_cohort), continue both branches from their same fitted patient state at T. For h=1..7 set assigned medication to j in branch j, keep continuation background and no-prompt support fixed, sample C adherence from p_Ci and medication adherence from p_Mi, and propagate the specified recurrences and AR innovations. Do not reset residual exposure or rebound. N0 uses its current-taken medication design throughout historical fitting and future prediction; it still propagates R and behavioral exposure. Its omitted medication carryover is precisely the intended misspecification comparator.

Define g_Q(z,s)=E[round_.001(clip_[0,10](Normal(10-z/3,s)))]. The effect draw is

```
delta_im = E_future[ (1/7)*sum(h=1..7)
                    {g_Q(z_A,i,T+h, sigma_Q) - g_Q(z_B,i,T+h, sigma_Q)}
                    | u_m, H*_cohort ].
```

This integrates future component adherence, AR/process noise and rounded measurement noise. It is not beta_A-beta_B, not a latent burden difference, and not one noisy predictive trajectory. Retain chain/draw/target axes. A positive contrast favors A on quality. Both models and evaluator receive exactly the same declared reduced cohort H* and target identity; evaluator conditional truth is computed separately with its permitted truth machinery, never supplied to the learner. No additional conditioning fields are proposed, so retain `EST-N1:poc-hstar-v1` and `poc-analysis-history-v1`. Cohort membership changes the conditioning realization/hash and must be recorded; it is not hidden behind the old patient's input hash.

Separate component probabilities prevent behavioral delivery evidence from asserting medication adherence. Relative to common p, medication predictions retain uncertainty supported only by medication opportunities; this affects nonlinear clipped quality and posterior expected contrasts even if outcome amplitude priors are unchanged. No cross-patient adherence sharing avoids adding an unprescribed adherence hierarchy. These choices neither assume perfect background adherence nor import .85. Independent streams are a modeling restriction; real adherence dependence is not established by synthetic computation.

## Minimal amendment and identity proposal

After independent acceptance, put this fixed unit/axis/adherence definition in the analytics contract's N extension (refer to its existing likelihood/numerical sections), add a short P3 dependency/reference to it, and update the existing P1 request admission seam. No additional registry or application is needed. Individual-experiment and POC-VAL requirements need no scientific rewrite. Update their indexes only if needed to point to the accepted amendment; this candidate changes none of them.

Preserve serialized old boundary fixtures and v1 model/prior references as non-executable historical identities. Propose new explicit model IDs `poc-nof1-N0-v2` and `poc-nof1-N1-v2`, and common prior ID `poc-nof1-prior-v2` with hashes over the full axes/laws above, including Beta observation/adherence factors. These are proposed names, not fabricated accepted hashes. Avoid replacing the current `IDENTITIES` entries in a way that retroactively reinterprets boundary records: retain strict old boundary validation and admit a narrow explicit executable N identity tuple separately. Existing schema2.0 wire fields can remain if their meaning is unchanged. The target member must be bound and cross-checked against the existing target patient/seed/request and result provenance; reject ambiguous target binding rather than silently use the first cohort row.

Freeze a concrete per-purpose configuration under the planned `poc-n1-v1` family with distinct N0/N1 hashes before execution. Its canonical content must include these new model/prior refs, unchanged estimand/history/protocol/law refs, fixed cohort compatibility/selection and target binding, parameter axes, adherence ownership rules, cutoff, numerical algorithm/parameterization, sampler settings, diagnostics, integration settings/seeds and artifact schemas. Data membership and histories additionally live in the immutable request/input hash. Do not inherit the visit config hash or use a boundary fixture as executable. Computation-only settings must be finalized by the implementation proposal; this scientific proposal does not pretend to specify an unimplemented integration algorithm's byte hash.

Persist posterior parameter/current-state draws with chain/draw/patient axes, integrated contrasts with chain/draw/target axes, separately labeled predictive draws, consumed record IDs plus distinct likelihood ownership, and fit/integration/resource diagnostics through the existing artifact/result machinery. Exact artifact/diagnostic schema refs and validated content hashes must be frozen with executable admission. P1's output veto and empty allowlist remain in force until that independently reviewed implementation is ready. No prior reuse as pseudo-data and no behavioral external-study likelihood in N.

## Acceptance checks and remaining limits

1. Independent critique accepts or amends the explicit new cohort and adherence choices; canonical amendments and strict v2 identity handling are reviewed before dependent work. Old boundary fixtures remain non-executable and old visit hashes/replay unchanged.
2. Verify complete parameter axes and prior density against independent small J=1 and J=2 constructions. J=1 retains both hierarchy levels; changing another member can influence target outcome hyperparameters but cannot change the target's Beta adherence counts. N0/N1 parameter/prior/likelihood ownership match exactly except medication design, with identical H* hashes.
3. Typed-stream controls distinguish C, MED_A/B and support; washout is not medication failure; missing/unknown delivery rejects; duplicate/corrected rows contribute once. Check common cutoff, owner/run/template membership, target binding, two-block-per-arm target gate, and no omitted/pending quality counted as zero outcome. Verify separate conjugate Beta updates and no double counting.
4. Extend the frozen numerical controls with independent prior/likelihood/gradient, chain/draw preservation, sign/null/no-noise, carryover/washout/rebound and exact rounded-quality integration checks. Compare expected effects with independent high-precision public-model reference calculations. No private coefficient, .85 constant or evaluator-only field may enter model/rollout inputs.
5. Retain native PyMC NUTS/float64, four chains, initial1000 tune+1000 saved and one documented2000+2000 extension; R-hat<1.01, bulk/tail ESS>=400 for reported quantities, no unresolved divergences. Do not relax these for a larger cohort.
6. Retain eight paired rollout batches, independent streams across posterior draws; K1024 doubling through65536, first possible K/2-v-K acceptance at2048; whole20-draw within-chain bootstrap1000. In quality units require U<=.01*max(L,.05^2), mean integration SE sqrt(U/M)<=.02 and <=.10*max(sqrt(L),.05), SD/interval endpoint change<=max(.005,.02*sqrt(L)). Stop whole integration stage at30 minutes under2CPU/2GiB; failed gates abstain without an accepted interval. Analytic replacement needs independently bounded error at these tolerances.
7. Actual isolated fit/refit, cohort resource qualification, conditional-truth precision and POC-VAL paired independent-panel recovery remain subsequent work. Report all failed/abstained/inconclusive targets and panel denominators; hierarchical borrowing cannot bypass a target's block-count gate.

There is no evidence here that the cohort model meets runtime limits or that this adherence restriction is calibrated. The active cohort worker's resource lease is untouched. Scientific acceptance, executable identity/artifact freeze, compatible observed-export verification and independent implementation review are blockers to execution, not evidence that the request must be expanded into WCLS/S2 or a full replan.
