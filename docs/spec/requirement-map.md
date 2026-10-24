# Requirement preservation and gate map

**Immediate milestone (2026-10-22):** [cloud physician simulation](poc-amendment-20261021.md#immediate-physician-simulation-milestone-2026-10-22) precedes later analytics. POC-CLOUD-01–05 and POC-1–3 plus workflow/persistence/failure portions of POC-6 map to CS0–CS4 and CS-T1–T8 in the [cloud task/test ledger](../implementation/poc-cloud-simulation-ledger-20261022.md). These checks require real Google Cloud HTTPS deployment, credential/session validation, account isolation, physician interaction and durable state. They are planned, not executed. Training/fitting is not an immediate dependency; existing seven-condition science, accuracy/timeliness and analytics ledger obligations remain later work.

**Proposed implementation amendment (2026-10-22; independent critique pending):** [Restricted longitudinal truth and seven-condition study plan](../implementation/poc-truth-ablation-plan-20261022.md) and its [task/test ledger](../implementation/poc-truth-ablation-task-ledger-20261022.json) map TRUTH-01/02, TIME-01, DGP-03, POC-4/5/6, POC-VAL, BAYES-02, MRT-01, MISS-01 and APPT-01–05 to TA1–TA6/TA-T1–10. This is planning traceability, not implemented or executed acceptance; canonical PoC scope and repetition counts are unchanged.

Legacy section IDs retain all original requirements in the mapped canonical sections. Atomic paragraph/list/table units are mapped in the gate traceability files below; each mandatory unit receives an implementation task/test ID before its gate. Migration does not count as executed acceptance. Source IDs refer to the domain evidence registers.

## Atomic legacy map

[G0](traceability/g0.md), [G1](traceability/g1.md), [G2](traceability/g2.md), [G3](traceability/g3.md), [G4](traceability/g4.md), [G5](traceability/g5.md), [G6](traceability/g6.md), [G7](traceability/g7.md). Baseline: commit `b21f00003e3f31866f29f9dc20f0d367d39ab11f`. The six changed units have explicit dispositions in [revision history](revision-history.md). Remaining units are preserved after citation/link normalization.

## New requirement and evidence map

| IDs | Canonical owner | Gate / acceptance evidence | Source justification |
|---|---|---|---|
| POC-BREADTH-01–03, POC-HARNESS-01–02 | [Breadth and reusable harness amendment](poc-ablation-breadth-reuse-20261024.md) | Candidate pending different critique/adoption; TA-B0–B4 / TA-BT1–5 in the [ablation ledger](../implementation/poc-truth-ablation-task-ledger-20261022.json). Full design and different critique before broader DGP/feature-contract freeze or pilot; observed four-family consumption, independent truth, genuine repeated-version harness and seven configurations required | User requirements 2026-10-24; source-bound gaps, no implementation/study acceptance |
| POC-CLOUD-01–05 | [PoC amendment](poc-amendment-20261021.md#immediate-physician-simulation-milestone-2026-10-22) | Immediate cloud simulation: [CS0–CS4 / CS-T1–T8](../implementation/poc-cloud-simulation-ledger-20261022.md); all cloud checks pending | Latest user scope; official Google Cloud sources in ledger |
| ENG-01, UI-SKILLS, TEST-QUALITY | [Engineering guidelines](../execution/engineering-guidelines.md) | G0-G7: choices tied to requirements; G5: complete UX/browser scenario mapping, real middleware/persistence tests; G7: pinned dependencies and skill provenance | User engineering requirements; ux-agent-react, ux-agent-composition, ux-agent-web |
| SYN-BOUNDARY, CLIN-UPDATE | [Scope](00-scope-and-invariants.md) | G0/G7: separate claim statuses and evidence scope | esmo, cochrane-cbti, zhang-leukemia, dimsdale-inpatient |
| CONTRACT-01, TIME-01, EST-INT | [Contracts](01-estimands-and-contracts.md) | G0/G5: schema versions, temporal DAG, no scalarized interruption winner | iche9, gformula; vector is engineering choice |
| DGP-01, DGP-02, DGP-03 | [DGP](02-synthetic-dgp.md) and [equations](dgp-reference.md) | G0/G1: parameter manifest, independent layers, locked namespaces | sim-check, recsim; numerical equations are invented |
| TRUTH-01, TRUTH-02 | [DGP](02-synthetic-dgp.md#primary-scientific-law-and-implementation-claim) | G1: analytic versus rollout agreement, numerical SE, denied truth access; stochastic target-law assumption explicit, T2/literal implementation bridge unresolved; V0/V1 matched sampling-SE experiment [TA2-SE-DEFINITION-01](../implementation/poc-ta2-se-definition-20261024.md), populated calibration/admission pending | sim-check; precision cutoffs and empirical successful-pair SE convention are engineering choices |
| BAYES-01, BAYES-02 | [Bayesian](03-bayesian-models.md) | G2: analytic posteriors, SBC quantities/faults, diagnostics | sbc-talts, sbc-quantities, stan-diagnostics |
| BORROW-01, MEASURE-01 | [Bayesian](03-bayesian-models.md) | G2: bridge/transport/measurement comparisons | robustmap, rover, gformula; new bridge is proposed |
| EXP-01, SMART-01 | [Experiments](04-individual-experiments.md) | G3: block and strategy recovery, consent/stopping | n1bayes, smart-adaptr |
| SUPPORT-01, MRT-01 | [Support](05-support-learning.md) | G4: executable probability checks, WCLS recovery/coverage | wcls, pooling, adaptive, microsoft-srm |
| MISS-01, OPE-01 | [Support](05-support-learning.md) | G4/G6: reporting sensitivity, on-policy truth comparison | ope-dr, adaptive; MNAR parameters are assumptions |
| UI-VALIDATION | [UI](06-service-and-ui.md) | G5: saved backend output comparison and original workflow matrix | Existing UX sources; EST-INT |
| VAL-01, VAL-02, VAL-03 | [Validation](07-validation-protocol.md) | G6: locked manifests, counts, MCSEs, failures and criteria | sim-ademp, sbc-quantities, rliable |
| DECISION-01, POLICY-01 | [Validation](07-validation-protocol.md) | G6: clinic-wide false claims, held-out personalization value | gnull, adaptive, netflix-hte, rliable; gates are engineering choices |
| RELEASE-01 | [Gates](08-gates-and-release.md) | G7: clean reproduction and separate human/clinical statuses | Existing clinical and UX evidence boundaries |
| S01–S32 | [Catalog](scenario-catalog.md) | Applicable gates and tiers are specified per row | Sources in consuming component contracts |

## Methods library implementation requirements

| IDs | Canonical owner / implementation steps | Gate / acceptance | Sources |
|---|---|---|---|
| LIB-01, LIB-02, LIB-03 | [Library decisions](../plans/methods/00-library-decisions.md) | G0 qualification, evidence-led selection, versioned artifacts; G5 metadata; G7 tested pins | [Software register](../evidence/software-libraries.md); user Python/offline-R preference |
| DGP-LIB | [DGP](02-synthetic-dgp.md); methods validation steps | G1 keyed numerical streams, independent truth and replay | sw-numerics |
| BAYES-LIB, BORROW-LIB, SBC-LIB, BCF-LIB | [Bayesian steps](../plans/methods/01-bayesian-and-borrowing.md); canonical Bayesian specification | G2 actual-backend calibration, bridge/import checks and matched BCF; no duplicated studies | sw-pymc, sw-arviz, sw-rbest, sw-sbc, sw-stochtree, sw-nutpie |
| EXP-LIB, SUPPORT-LIB, MRT-LIB, BANDIT-LIB, OPE-LIB | [Experiments/support steps](../plans/methods/02-experiments-and-support.md); canonical component specifications | G3/G4 schedule/strategy/covariance checks, WCLS reference and correction coverage, executed-policy and OPE validation | sw-numerics, sw-statsmodels, sw-mrtanalysis, sw-sklearn, sw-bandits, sw-ope |
| LIB-BENCH | [Validation steps](../plans/methods/03-validation-and-benchmarks.md); canonical validation protocol | G0 selection dispositions; G6/G7 targeted future comparisons only where consequential uncertainty remains, unchanged mandatory gates | Software register; user instruction to defer benchmarks and reuse clear evidence |

## Legacy section homes

### October 19 UX additions

| IDs | Canonical owner / implementation plan | Acceptance | Sources |
|---|---|---|---|
| UX-FOUNDATION | [Research and foundations](../plans/ux/00-research-and-foundations.md); service/UI presentation refinement | G0 reviewed contracts; G5 view/requirement mapping | ux-nhs, ux-nist, ux-dashboard |
| UX-ACCOUNT | [Accounts and shell](../plans/ux/01-doctor-accounts-and-shell.md) | UX-T01/02 | Engineering access-control requirements; ux-nist identity rationale |
| UX-PANEL | [Panel dashboard](../plans/ux/02-panel-dashboard.md) | UX-T03/04/13 | ux-carbon, ux-github |
| UX-WORKFLOW | [Patient workflow](../plans/ux/03-patient-decision-workflow.md) | UX-T05-10/14 | ux-govtasks, ux-apple; existing domain evidence |
| UX-HELP | [View guides](../plans/ux/04-tooltips-and-view-guides.md) | UX-T11/12 | ux-cloudscape, ux-wcag-help, ux-dialog |
| UX-APPENDIX | [Technical appendix](../plans/ux/05-technical-appendix.md) | UX-T12 | ux-cloudscape |
| UX-ACCEPTANCE | [Validation](../plans/ux/06-validation-and-integration.md) | G5 plus separate human/clinical statuses | ux-nist, ux-nhs; existing human-review requirements |

UX source records are in the [UX register supplement](../evidence/ux-and-interfaces.md#ux-pattern-research-2026-10-19). Tests remain planned, not passed.

### Legacy mapping

| ID | Original section | Canonical document | Disposition |
|---|---|---|---|
| LEG-01 | 1. Recommendation and intended demonstration | [00-scope-and-invariants.md](00-scope-and-invariants.md) | Preserved; targeted revisions listed in revision history |
| LEG-02 | 2. Clinical pathway and boundaries | [00-scope-and-invariants.md](00-scope-and-invariants.md) | Preserved; targeted revisions listed in revision history |
| LEG-03 | 3. Workflow state and decision ownership | [00-scope-and-invariants.md](00-scope-and-invariants.md) | Preserved; targeted revisions listed in revision history |
| LEG-04 | 4. Estimands before algorithms | [01-estimands-and-contracts.md](01-estimands-and-contracts.md) | Preserved; targeted revisions listed in revision history |
| LEG-05 | 5. Data contracts, timing, and provenance | [01-estimands-and-contracts.md](01-estimands-and-contracts.md) | Preserved; targeted revisions listed in revision history |
| LEG-06 | 6. Synthetic data and simulator | [02-synthetic-dgp.md](02-synthetic-dgp.md) | Preserved; targeted revisions listed in revision history |
| LEG-07 | 7. Bayesian population model and external-evidence borrowing | [03-bayesian-models.md](03-bayesian-models.md) | Preserved; targeted revisions listed in revision history |
| LEG-08 | 8. Individual experiments and behavioral escalation | [04-individual-experiments.md](04-individual-experiments.md) | Preserved; targeted revisions listed in revision history |
| LEG-09 | 9. MRTs, contextual bandit, and optional offline RL | [05-support-learning.md](05-support-learning.md) | Preserved; targeted revisions listed in revision history |
| LEG-10 | 10. Research-backed UI design requirements | [06-service-and-ui.md](06-service-and-ui.md) | Preserved; targeted revisions listed in revision history |
| LEG-11 | 11. Overall dashboard | [06-service-and-ui.md](06-service-and-ui.md) | Preserved; targeted revisions listed in revision history |
| LEG-12 | 12. "Next treatment assignment" tab | [06-service-and-ui.md](06-service-and-ui.md) | Preserved; targeted revisions listed in revision history |
| LEG-13 | 13. Historical review and time travel | [06-service-and-ui.md](06-service-and-ui.md) | Preserved; targeted revisions listed in revision history |
| LEG-14 | 14. Application architecture and implementation contracts | [06-service-and-ui.md](06-service-and-ui.md) | Preserved; targeted revisions listed in revision history |
| LEG-15 | 15. Development phases and acceptance gates | [08-gates-and-release.md](08-gates-and-release.md) | Preserved; targeted revisions listed in revision history |
| LEG-16 | 16. Methodological, software, and UX evaluation | [07-validation-protocol.md](07-validation-protocol.md) | Preserved; targeted revisions listed in revision history |
| LEG-17 | 17. Demonstration script | [08-gates-and-release.md](08-gates-and-release.md) | Preserved; targeted revisions listed in revision history |
| LEG-18 | 18. Completion definition and later clinical translation | [08-gates-and-release.md](08-gates-and-release.md) | Preserved; targeted revisions listed in revision history |
