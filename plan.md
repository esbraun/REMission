# REMission development plan

Revision: 2026-10-19. Build a synthetic research demonstration for adult outpatient leukemia chemotherapy insomnia care. No clinical efficacy, clinical validation, or executed model-validation result is claimed.

This file is the authoritative navigation index. Requirements live in the linked canonical specifications; the [execution entry point](implementation-prompt.md) defines how future workers load context.

Start with [scope and invariants](docs/spec/00-scope-and-invariants.md), then the [gate reading bundles](docs/spec/08-gates-and-release.md). See [scenario catalog](docs/spec/scenario-catalog.md), [requirement map](docs/spec/requirement-map.md), [evidence rules](docs/evidence/README.md), and [revision history](docs/spec/revision-history.md).

## UX implementation planning sequence

Start with [UX research and foundations](docs/plans/ux/00-research-and-foundations.md), which indexes the ordered plans for doctor accounts, panel dashboard, patient decisions, contextual guides, technical appendix and validation. The [adversarial review](docs/plans/ux/07-adversarial-review.md) records the completed plan review. These are application requirements, not implemented features or accepted human-factors results. The existing G0-G7 dependencies still apply.

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

Canonical specification: [05-support-learning.md](docs/spec/05-support-learning.md).

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
