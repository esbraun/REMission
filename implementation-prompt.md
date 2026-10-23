# REMission implementation entry point

Revision: 2026-10-20. This instruction set governs future application implementation. Documentation acceptance does not mean application, statistical or human validation is complete.

## Load bounded gate context

Read the [plan index](plan.md), [shared invariants](docs/spec/00-scope-and-invariants.md), and [gate bundles](docs/spec/08-gates-and-release.md#gate-context-and-acceptance). Load the assigned gate specification, consumed contracts and cited scenario/evidence entries. Do not load the entire package into every worker.

All implementation workers also read the [engineering guidelines](docs/execution/engineering-guidelines.md); UI workers load the applicable installed skills and rule files identified there. Apply the risk-based test policy without reducing required scenario coverage.

Requirements have one canonical home. Use stable requirement, estimand, scenario and source IDs from the [requirement map](docs/spec/requirement-map.md). Resolve conflicting requirements before dependent implementation.

| Task | Additional reading |
|---|---|
| Runtime setup and launch | [Runtime and workflow](docs/execution/runtime-and-workflow.md) |
| Scheduling, ownership and independent review | [Delegation](docs/execution/delegation.md) |
| UI and browser checks | [Browser validation](docs/execution/browser-validation.md) |
| Verification and release | [Verification and handoff](docs/execution/verification-and-handoff.md) |

## Launch contract

Implement the [immediate cloud physician simulation milestone](docs/spec/poc-amendment-20261021.md#immediate-physician-simulation-milestone-2026-10-22): POC-CLOUD-01–05, POC-1–3 and workflow/persistence/failure checks from POC-6, using the [cloud task/test ledger](docs/implementation/poc-cloud-simulation-ledger-20261022.md). Training/fitting and learner/evaluator workers are not required. POC-4/5, fitted protocols, APPT-01–05 and POC-VAL remain later analytics work with unchanged scientific obligations. It supersedes conflicting exhaustive G0-G7 scope and sequencing for immediate acceptance. Reuse accepted contracts and the existing task ledger under `docs/implementation/`; exhaustive full-program qualification is deferred. Use one orchestrator thread for user communication and feedback, plan and gate progress, task distribution, dependency scheduling, consolidated reporting, and reviewed PR integration. Delegate all substantive technical work to real subagents: exploration, technical planning, critique, contracts, implementation, integration edits, testing, evidence inspection, independent review, documentation, and release reproduction. An integration subagent handles source edits and conflict resolution; the orchestrator may open PRs and merge reviewed worktree branches in dependency order under the acceptance rules below. Actual runtime instructions and tool availability take precedence. These roles cannot substitute for clinicians or human-factors participants.

Follow the [official subagent guidance](https://learn.chatgpt.com/docs/agent-configuration/subagents?surface=app) and the [delegation contract](docs/execution/delegation.md#delegation-and-integration-contract). Keep at most two non-Luna subagent threads concurrently open across the entire workflow, excluding the orchestrator. **GPT-6 Luna (`gpt-6-luna`) helpers do not count toward this two-worker limit.** Two Astra/Sol workers may continue while additional Luna helpers explore or summarize, subject to the runtime's total thread capacity. Only the orchestrator spawns or assigns agents. Workers may freely request Luna helpers through it; do not queue those requests merely because both non-Luna slots are occupied. Queue only when actual runtime capacity or task dependencies require it. Reuse suitable workers and release completed threads before replacements. Do not replace unavailable delegation with solo implementation.

| Work | Subagent model | Reasoning effort |
|---|---|---|
| Technical planning, review, and critique | `gpt-6-astra` | `medium` |
| Implementation, integration, repairs, and verification | `gpt-6.1-sol` | `high` |
| Difficult implementation | `gpt-6.1-sol` | `xhigh` |
| Exploration, summaries, and lightweight helpers | `gpt-6-luna` | `high` |

Use explicit model and effort settings for every assignment. Sol implementation may increase to `xhigh` without user confirmation; record the reason in the task handoff. Independent review belongs to a separate Astra reviewer, with findings returned to Sol for fixes and then reviewed again. Verify actual model availability and settings; report unsupported choices without silently substituting models. The [runtime instructions](docs/execution/runtime-and-workflow.md#subagent-runtime-configuration) describe the required concurrency setting and capability checks.

Enforce the project limit by effective model, counting all open non-Luna threads, including idle ones. A helper switched from Luna to Astra/Sol must acquire a non-Luna slot first. The runtime's global thread cap includes Luna, so configure enough total capacity for two non-Luna workers plus helpers; a global cap of two does not implement this policy. Luna has no separate project count limit, but every helper needs a bounded task, its own worktree, and available runtime capacity.

Every subagent, including planners, explorers, Luna helpers, and reviewers, works in its own Git worktree. Give writing workers separate task branches from an accepted base commit and reviewers separate worktrees pinned to the exact candidate commit. Record absolute worktree paths, branches, and commits in assignments and the ledger. Spawning a thread does not establish workspace isolation: verify its assigned checkout before any work. Do not use the orchestrator's checkout or another agent's worktree as a shared editing area. If isolated worktrees are unavailable, report the blocker rather than falling back to shared-tree work.

The user authorizes the orchestrator to open PRs and merge worktree branches into their assigned integration target without repeated confirmation once an independent Astra reviewer explicitly deems the exact candidate ready to ship, required task/gate checks and repository checks pass, review findings are resolved, and dependencies are accepted. Respect repository protections. Head or target-base changes require refreshed review and affected checks; delegate conflicts and repairs to Sol before re-review. Record PR, reviewed head/base, review evidence, and resulting merge commit. A branch merge is engineering integration, not completion of outstanding human or clinical gates. See [worktree and merge procedure](docs/execution/delegation.md#worktree-isolation-and-reviewed-merges).

For the later analytics milestone, use actual Bayesian fitting, posterior computation, N-of-1 randomization/analysis, MRT/WCLS and bounded support selection for the minimal PoC representatives. Generalized protocol engines remain later work. Cached outputs must come from reproducible runs. Keep real literature separate from synthetic quantitative studies. No real patient systems, messages, orders or wearable accounts are in scope.

Methods workers read the [library decisions](docs/plans/methods/00-library-decisions.md), assigned method implementation steps and applicable [software evidence](docs/evidence/software-libraries.md). Use PyMC as the single application Bayesian backend, with explicit native NUTS initially; RBesT/SBC/MRTAnalysis are offline preparation/reference tools. Follow the [selective benchmark policy](docs/plans/methods/03-validation-and-benchmarks.md): reuse clear applicable evidence, benchmark only unresolved material choices, and retain all required project validation. No benchmark results are supplied by these plans.

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
