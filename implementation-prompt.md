# REMission implementation entry point

Revision: 2026-10-19. This instruction set governs future application implementation. Documentation acceptance does not mean application, statistical or human validation is complete.

## Load bounded gate context

Read the [plan index](plan.md), [shared invariants](docs/spec/00-scope-and-invariants.md), and [gate bundles](docs/spec/08-gates-and-release.md#gate-context-and-acceptance). Load the assigned gate specification, consumed contracts and cited scenario/evidence entries. Do not load the entire package into every worker.

Requirements have one canonical home. Use stable requirement, estimand, scenario and source IDs from the [requirement map](docs/spec/requirement-map.md). Resolve conflicting requirements before dependent implementation.

| Task | Additional reading |
|---|---|
| Runtime setup and launch | [Runtime and workflow](docs/execution/runtime-and-workflow.md) |
| Scheduling, ownership and independent review | [Delegation](docs/execution/delegation.md) |
| UI and browser checks | [Browser validation](docs/execution/browser-validation.md) |
| Verification and release | [Verification and handoff](docs/execution/verification-and-handoff.md) |

## Launch contract

Implement the full synthetic hybrid through G0–G7. Start with G0 contracts and a requirement-to-task-to-test ledger under `docs/implementation/`. Preserve the established future implementation workflow: real subagents own packages, an orchestrator integrates in dependency order, independent reviewers inspect evidence, and a release worker reproduces the result. Actual runtime instructions and tool availability take precedence. These roles cannot substitute for clinicians or human-factors participants.

Use actual Bayesian fitting, randomization, WCLS and bounded policy logic. Cached outputs must come from reproducible runs. Keep real literature separate from synthetic quantitative studies. No real patient systems, messages, orders or wearable accounts are in scope.

Every methods worker and reviewer receives:

- Canonical requirement and estimand IDs/versions.
- DGP/scenario versions, observation cutoff and seed namespace.
- Expected truth, its calculation method and numerical uncertainty.
- Exact comparator estimand and allowed information set.
- Required artifacts, diagnostics and acceptance checks.
- Applicable citation IDs and identification limitations.
- Fit-failure/abstention handling and the ban on evaluator-only inputs.

Keep computational calibration, fixed-DGP recovery, robustness, policy evaluation, usability and clinical validation distinct. Use the [validation protocol](docs/spec/07-validation-protocol.md).

## Completion discipline

Preserve unrelated workspace changes. Documentation revisions include all affected index, specification, execution and evidence files; the old instruction to commit only this file is obsolete. Do not invent run versions, diagnostics, clinical review or completed evaluations.

Track synthetic engineering acceptance, human-factors review, clinical review and clinical validation separately. Report failures, incomplete computations and outstanding human gates. Synthetic validation cannot establish clinical efficacy or safety.
