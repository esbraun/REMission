# Gates and release

Specification revision: 2026-10-19. Status: requirements only; no implementation or validation result is asserted.

**Read first:** [00-scope-and-invariants.md](00-scope-and-invariants.md), [07-validation-protocol.md](07-validation-protocol.md). Read linked scenario and evidence entries only when needed.

**Inputs:** versioned upstream contracts and applicable scenario IDs. **Outputs:** the contracts, artifacts and checks specified below. **Acceptance:** relevant G0–G7 evidence in [gates](08-gates-and-release.md); statistical checks use the [validation protocol](07-validation-protocol.md).

## Gate context and acceptance

All gates are **not executed** at this documentation revision. The index, shared scope and [engineering guidelines](../execution/engineering-guidelines.md) are common context; read only the listed bundle and relevant linked evidence/scenario entries. Input contract changes invalidate dependent evidence, not immutable historical records.

| Gate | Reading bundle | Required outputs and acceptance evidence |
|---|---|---|
| G0 Contracts | Scope; [estimands/contracts](01-estimands-and-contracts.md); [reference DGP](dgp-reference.md); applicable evidence | Temporal DAG/factorization, reviewed synthetic parameter table, outcome/decision contracts, citation limitations, task mapping; no missing generator coefficients hidden in code |
| G1 Generator | [DGP](02-synthetic-dgp.md); reference equations; consumed contracts; catalog rows | Analytic fixtures, independent truth agreement/precision, keyed seeds, denied truth access, distribution checks, deterministic replay and lineage |
| G2 Bayesian | [Bayesian models](03-bayesian-models.md); validation; applicable DGP/estimands | Analytic posterior checks, likelihood-sensitive SBC, marginal borrowing bridge, fixed-DGP recovery, overlap and null behavior; final-scale diagnostics |
| G3 Experiments | [Individual experiments](04-individual-experiments.md); protocol/estimand contracts; relevant catalog | N-of-1 block/carryover/rebound evidence, frozen support snapshot, stage versus strategy values, enumerable SMART comparison, consent/stopping behavior |
| G4 Support | [Support learning](05-support-learning.md); relevant contracts and validation | Executable propensities, availability, WCLS checks, missingness sensitivity, supported OPE, bounded policy tests, no medication actions |
| G5 Integration | [Service/UI](06-service-and-ui.md); accepted contracts; browser execution bundle | Real service persistence, correct saved model outputs, immutable history, approval/consent/hold races, all original stories and UI states |
| G6 Confirmation | [Validation protocol](07-validation-protocol.md); locked catalog cells; accepted methods versions | Repeated recovery, decision-null and complete-cohort runs; Monte Carlo uncertainty; failures/abstentions; paired policy values; personalization decision |
| G7 Reproduction | This document; accepted manifests; [handoff](../execution/verification-and-handoff.md) | Clean-checkout reproduction, pinned dependencies, input/model/DGP hashes, preserved limitations, separate human/clinical status |

G0 precedes G1 and detailed UI design. G2 depends on accepted G1. G3 depends on shared G0/G1 and accepted G2 interfaces. G4 depends on G1 and G3 coordination contracts. A thin service shell can be built independently after G0; G5 acceptance requires the actual G2–G4 engines. G6 depends on the locked integrated version; G7 follows G6. Unresolved statistical failures cannot be relabeled as UX acceptance.

### Methods library reading and acceptance

G0 qualifies the [library decisions](../plans/methods/00-library-decisions.md), licenses/runtime support and offline artifact contracts. G1 consumes the numerical implementation guidance. G2 reads [Bayesian/borrowing steps](../plans/methods/01-bayesian-and-borrowing.md); G3/G4 read [experiments/support steps](../plans/methods/02-experiments-and-support.md). G5 consumes LIB-03 result metadata. G6/G7 read [validation and selective benchmarks](../plans/methods/03-validation-and-benchmarks.md), applicable source records and accepted runtime/artifact manifests.

Library selection may rely on clear applicable existing evidence without a redundant benchmark. Require a targeted future DGP comparison only for a material unresolved choice; preserve the required 20-fit resource pilot and all statistical acceptance gates. No library-selection evidence or documentation check counts as accepted model/policy validation.

### RELEASE-01 — Separate evidence statuses

G5 also consumes the [UX plan sequence](../plans/ux/00-research-and-foundations.md) and [UX-T01 through UX-T14](../plans/ux/06-validation-and-integration.md). These add account isolation, panel/task navigation, contextual documentation and draft-recovery acceptance; they do not replace existing statistical, clinical or human-review gates.

Track `synthetic-engineering`, `human-factors`, `clinical-review`, and `clinical-validation` separately with not-started/running/failed/blocked/accepted and evidence links. Synthetic-engineering acceptance requires G0–G7 statistical/software evidence. Human-factors requires real intended users and manual accessibility evidence as specified; clinical validation is a separate future project. A full app completion claim still requires the original human-review gates, not only synthetic-engineering acceptance.

A reproducibility manifest includes protocol hash, scenario/DGP/model/prior versions, source code commit, package/runtime versions, seed derivation, attempted/completed counts, failures, saved estimates/intervals, truth SEs, policy lineage, commands, runtime/memory and artifact checksums. Bulk data/fits remain in documented artifact storage; commit concise manifests and reports. Resume from recorded replicate keys without regenerating completed independent runs.

## 15. Development phases and acceptance gates

| Phase | Work | Reviewable output and gate |
|---|---|---|
| 0. Clinical and UX discovery | Map outpatient tasks with clinicians/nurses/behavioral staff; define estimands, intercurrent-event strategies, eligibility, hold triggers, benefit thresholds, ownership, and evidence registry; record the anticipated research-oversight position for each randomized component; sketch both dashboards and assignment states | Reviewed workflow/state map, estimand contracts, source-to-design matrix, data dictionary, and task-based UI prototypes |
| 1. Synthetic environment | Implement causal simulator, hidden truth, external-study generator, dated EMR/Oura/report feeds, and event replay | Reproducible base and stress scenarios including the sharp null; no truth fields in learner exports |
| 2. Bayesian cold start | Implement weak, complete-borrowing, and robust priors; longitudinal models and posterior rollouts | Prior/posterior checks, convergence, study-to-target mapping, heterogeneity-prior sensitivity, sharp-null false-ranking rate, and matched/conflicting prior comparisons |
| 3. Individual learning | Add N-of-1 protocol/randomization/analysis and durable behavioral escalation | Carryover, rebound, and instability tests; assignment/delivery separation; no on/off CBT-I crossover; no randomization without a consent record |
| 4. Online support | Add MRT assignments, WCLS analysis, hierarchical contextual bandit, propensity logs, reward windows, and constraints | Valid assignment logs; unavailable actions never assigned; probabilities within bounds; support policy frozen during N-of-1 blocks; proximal and distal results compared |
| 5. Clinician app | Connect dashboard, adaptive assignment panels, evidence inspection, approval, and history | End-to-end patient replay; no stale approval; historical snapshots remain unchanged |
| 6. Evaluation and usability | Run repeated simulations, method comparisons, clinician task sessions, and accessibility review | A demo report with operating characteristics, observed use errors, unresolved limits, and revised UI |
| 7. Reproducible handoff | Package seeded scenarios, commands, saved fits, contracts, and documentation | Fresh environment can reproduce the demonstration and its evaluation outputs |

Phase 0 precedes detailed visual design. Phases 1–4 can expose results through a minimal research interface; phase 5 turns them into a tested clinical workflow. Full inference may run offline before the live replay, with incremental updates used where validated.

Do not describe the app as clinically tested merely because it passes simulated scenarios or usability tasks.

## 17. Demonstration script

Use a small set of clearly fictional patient stories backed by the larger synthetic cohort.

| Case | What the clinician sees and does | Machinery demonstrated |
|---|---|---|
| New patient | Assess symptoms and contributors; inspect compatible external evidence and broad modifier uncertainty; approve an eligible plan | Cold start, robust prior, longitudinal prediction, clinical gating |
| Returning patient | Review reports/function and chemotherapy timing; see local evidence conflict with the prior; choose a revised eligible plan | Posterior update, reduced borrowing, transport sensitivity |
| Reversible comparison | Approve an N-of-1 protocol; replay blocks, carryover/rebound/rescue, and final uncertain or informative result | Individual randomization, hierarchical analysis, stopping/review, frozen support policy |
| Durable program | Review continuing skills and nonresponse; consider an eligible escalation path | Durable state, sequential treatment strategy |
| Between-visit support | Review the approved support envelope, MRT effects, and subsequent bounded adaptation | Logged randomization, causal excursion effects, contextual bandit, proximal/distal distinction |
| Clinical interruption | New condition changes eligibility while a draft is open; assignment is held | State/version guard and clinician review |
| Historical review | Select the first visit after later outcomes have arrived; inspect original data/model and return to now | As-known-then snapshots, bitemporal data, stage-specific historical UI |
| Failure cases | Inspect a confidently biased estimate in the hidden-confounding scenario, and a false ranking under the sharp null | Limits of causal identification and of parametric longitudinal models despite computational convergence |

The normal clinician view never shows simulator truth. A separate labeled research report compares recommendations with the oracle, explains failures, and displays learning curves.

## 18. Completion definition and later clinical translation

The synthetic app is complete when it can replay all cases, implement the full authorized hybrid loop, preserve historical decisions, satisfy the hard invariants, and report its simulation and usability results reproducibly.

Expected implementation artifacts:

- Reviewed workflow and estimand specifications, including intercurrent-event strategies.
- Synthetic generator and replay adapters.
- Evidence registry and robust-prior implementation.
- Longitudinal Bayesian model and posterior rollout service.
- N-of-1 and behavioral escalation protocol services.
- MRT/bandit policy service with action masks, coordination rules, and propensity logging.
- Dashboard and stage-dependent assignment workspace.
- Immutable history and audit system.
- Reproducible evaluation notebook/report and demonstration instructions.

Clinical translation is a separate project: leukemia-specific evidence review, ISI and threshold validation in the target population, medication/rule validation, device-measurement validation, real-data quality and transport assessment, ethics review and consent design for each randomized component, regulatory classification, prospective protocol review, and an evaluated pilot in the intended workflow. The synthetic app demonstrates implementation and operating behavior; it cannot establish clinical efficacy or safe treatment policies in patients.
