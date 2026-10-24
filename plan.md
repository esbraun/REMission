# REMission development plan

**Immediate scope (2026-10-22):** deploy the [physician simulation PoC](docs/spec/poc-amendment-20261021.md#immediate-physician-simulation-milestone-2026-10-22) on Google Cloud and validate HTTPS username/password login, owned synthetic panels, explicit decisions/rationale, simulated advancement/outcomes/history and persistence across reload and restart. Training/fitting is not needed for this milestone. The [cloud task/test ledger](docs/implementation/poc-cloud-simulation-ledger-20261022.md) owns its implementation sequence and unexecuted acceptance checks. Real analytics, all seven study configurations, scientific accuracy/timeliness and full G0-G7/human/clinical work remain later milestones under their existing contracts.

Revision: 2026-10-20. Build a synthetic research demonstration for adult outpatient leukemia chemotherapy insomnia care. No clinical efficacy, clinical validation, or executed model-validation result is claimed.

This file is the authoritative navigation index. Requirements live in the linked canonical specifications; the [execution entry point](implementation-prompt.md) defines how future workers load context.

Start with [scope and invariants](docs/spec/00-scope-and-invariants.md), then the [gate reading bundles](docs/spec/08-gates-and-release.md). See [scenario catalog](docs/spec/scenario-catalog.md), [requirement map](docs/spec/requirement-map.md), [evidence rules](docs/evidence/README.md), and [revision history](docs/spec/revision-history.md).

Remaining analytics implementation: [POC4–6 technical contract](docs/implementation/poc-analytics-contract-20261021.md) proposes the next bounded source changes and first real-fit slice on accepted POC1–3. It is a plan, not implemented or independently accepted analytics.

User requirements candidate (2026-10-24): [four-family synthetic breadth and reusable ablation harness](docs/spec/poc-ablation-breadth-reuse-20261024.md), with TA-B0–B4 in the existing truth/ablation ledger. Different critique/adoption and full critical-gate study/harness design plus different critique precede broader DGP/feature-contract freeze and pilot; apply the [launch model policy](implementation-prompt.md#launch-contract), preserving actual historical reviewer identities. No coverage or study result is asserted.

Accepted appointment requirements: [APPT-01–05](docs/spec/poc-amendment-20261021.md#appt-0105--background-refresh-and-appointment-prediction) separate background posterior refresh from versioned appointment predictions; [POC-VAL](docs/spec/07-validation-protocol.md#appt-04--appointment-timeliness-and-freshness) owns accuracy/freshness/latency measurement. A1–A4 remain not started in the [existing ledger](docs/implementation/poc-analysis-task-ledger.json). The [proposal promotion record](docs/spec/poc-appointment-inference-proposal-20261022.md) preserves review provenance; [StochTree/A5](docs/implementation/poc-appointment-inference-assessment-20261022.md) remains conditional/deferred, with no installation or backend exception.

## Implementation coordination

Use one orchestrator and at most two concurrently open non-Luna subagents with the [entry point's model assignments](implementation-prompt.md#launch-contract). **GPT-6 Luna helpers do not count toward that two-worker limit** and may run alongside both workers within the runtime's total capacity. Every subagent works in its own Git worktree, including planners, explorers, helpers, and reviewers. The orchestrator may open PRs and merge accepted worktree branches into assigned integration targets after independent review deems the exact head/base ready to ship, required checks pass, findings are resolved, and dependencies are accepted. Follow the canonical [worktree and merge procedure](docs/execution/delegation.md#worktree-isolation-and-reviewed-merges); source conflicts and repairs remain delegated. Integration does not replace G0–G7 or outstanding human/clinical acceptance.

## UX implementation planning sequence

Start with [UX research and foundations](docs/plans/ux/00-research-and-foundations.md), which indexes the ordered plans for doctor accounts, panel dashboard, patient decisions, contextual guides, technical appendix and validation. The [adversarial review](docs/plans/ux/07-adversarial-review.md) records the completed plan review. These are application requirements, not implemented features or accepted human-factors results. The existing G0-G7 dependencies still apply.

## Data science library and methods implementation plans

Use the [methods library decisions](docs/plans/methods/00-library-decisions.md) and ordered Bayesian/borrowing, experiments/support and validation plans. Selected foundations are PyMC, compatible ArviZ, NumPy/SciPy, statsmodels and scikit-learn; StochTree supplies the matched BCF benchmark and COBA contextual OPE. RBesT, SBC and MRTAnalysis run offline. nutpie is a conditional accelerator. The [software evidence register](docs/evidence/software-libraries.md) records sources and limitations.

Use existing applicable evidence to settle clear library choices. Plan selective synthetic-DGP comparisons only for consequential unresolved questions; no benchmarks were executed for this documentation revision. Required project validation and G0-G7 gates remain unchanged.

## Engineering and UI skills

Use the [engineering guidelines](docs/execution/engineering-guidelines.md) for DRY, maintained open-source reuse, simple implementation and meaningful tests. The three pinned React/composition/web-design skills are installed; their portable guidance preserves the existing React/TypeScript and FastAPI architecture and deployment outside Vercel. See the [review dispositions](docs/plans/ux/07-adversarial-review.md#october-19-2026-engineering-and-skills-review).

## Validation claim boundary

Synthetic DGPs permit checks of implementation, computation, causal recovery under stated assumptions, misspecification and policy behavior. They do not establish that those assumptions hold in patients or that treatment is safe or effective. Human-factors and clinical gates remain separate.

## 1. Recommendation and intended demonstration

Canonical specification: [00-scope-and-invariants.md](docs/spec/00-scope-and-invariants.md).

## 2. Clinical pathway and boundaries

Canonical specification: [00-scope-and-invariants.md](docs/spec/00-scope-and-invariants.md).

## 3. Workflow state and decision ownership

Canonical specification: [00-scope-and-invariants.md](docs/spec/00-scope-and-invariants.md).

## 4. Estimands before algorithms

Canonical specification: [01-estimands-and-contracts.md](docs/spec/01-estimands-and-contracts.md).

## 5. Data contracts, timing, and provenance

Canonical specification: [01-estimands-and-contracts.md](docs/spec/01-estimands-and-contracts.md).

## 6. Synthetic data and simulator

Canonical specification: [02-synthetic-dgp.md](docs/spec/02-synthetic-dgp.md).

## 7. Bayesian population model and external-evidence borrowing

Canonical specification: [03-bayesian-models.md](docs/spec/03-bayesian-models.md).

## 8. Individual experiments and behavioral escalation

Canonical specification: [04-individual-experiments.md](docs/spec/04-individual-experiments.md).

## 9. MRTs, contextual bandit, and optional offline RL

Canonical specification: [05-support-learning.md](docs/spec/05-support-learning.md). Restricted PoC S2 model/precision/saved-prediction definitions are proposed in [S2-CANONICAL-01](docs/implementation/poc-analytics-contract-20261021.md#s2-canonical-01--batch-working-policy-and-saved-prediction); [implementation handoff](docs/implementation/poc-s2-app-handoff-20261023.md). Canonical review, executable source and actual qualification remain separate.

## 10. Research-backed UI design requirements

Canonical specification: [06-service-and-ui.md](docs/spec/06-service-and-ui.md).

## 11. Overall dashboard

Canonical specification: [06-service-and-ui.md](docs/spec/06-service-and-ui.md).

## 12. "Next treatment assignment" tab

Canonical specification: [06-service-and-ui.md](docs/spec/06-service-and-ui.md).

## 13. Historical review and time travel

Canonical specification: [06-service-and-ui.md](docs/spec/06-service-and-ui.md).

## 14. Application architecture and implementation contracts

Canonical specification: [06-service-and-ui.md](docs/spec/06-service-and-ui.md).

## 15. Development phases and acceptance gates

Canonical specification: [08-gates-and-release.md](docs/spec/08-gates-and-release.md).

## 16. Methodological, software, and UX evaluation

Canonical specification: [07-validation-protocol.md](docs/spec/07-validation-protocol.md).

## 17. Demonstration script

Canonical specification: [08-gates-and-release.md](docs/spec/08-gates-and-release.md).

## 18. Completion definition and later clinical translation

Canonical specification: [08-gates-and-release.md](docs/spec/08-gates-and-release.md).
