# Requirement preservation and gate map

Legacy section IDs retain all original requirements in the mapped canonical sections. Atomic paragraph/list/table units are mapped in the gate traceability files below; each mandatory unit receives an implementation task/test ID before its gate. Migration does not count as executed acceptance. Source IDs refer to the domain evidence registers.

## Atomic legacy map

[G0](traceability/g0.md), [G1](traceability/g1.md), [G2](traceability/g2.md), [G3](traceability/g3.md), [G4](traceability/g4.md), [G5](traceability/g5.md), [G6](traceability/g6.md), [G7](traceability/g7.md). Baseline: commit `b21f00003e3f31866f29f9dc20f0d367d39ab11f`. The six changed units have explicit dispositions in [revision history](revision-history.md). Remaining units are preserved after citation/link normalization.

## New requirement and evidence map

| IDs | Canonical owner | Gate / acceptance evidence | Source justification |
|---|---|---|---|
| SYN-BOUNDARY, CLIN-UPDATE | [Scope](00-scope-and-invariants.md) | G0/G7: separate claim statuses and evidence scope | esmo, cochrane-cbti, zhang-leukemia, dimsdale-inpatient |
| CONTRACT-01, TIME-01, EST-INT | [Contracts](01-estimands-and-contracts.md) | G0/G5: schema versions, temporal DAG, no scalarized interruption winner | iche9, gformula; vector is engineering choice |
| DGP-01, DGP-02, DGP-03 | [DGP](02-synthetic-dgp.md) and [equations](dgp-reference.md) | G0/G1: parameter manifest, independent layers, locked namespaces | sim-check, recsim; numerical equations are invented |
| TRUTH-01, TRUTH-02 | [DGP](02-synthetic-dgp.md) | G1: analytic versus rollout agreement, numerical SE, denied truth access | sim-check; precision cutoffs are engineering choices |
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

## Legacy section homes

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
