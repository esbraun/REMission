# Runtime And Workflow

**Immediate PoC precedence (2026-10-22):** the [PoC amendment](../spec/poc-amendment-20261021.md) controls active scope, sequencing and acceptance over conflicting full-program requirements below. The immediate Google Cloud physician simulation milestone requires POC-CLOUD-01 through POC-CLOUD-05, POC-1 through POC-3 and the workflow/persistence/failure portions of POC-6. Training/fitting, POC-4/5, fitted protocol representatives, APPT-01–05 and POC-VAL remain later analytics acceptance; retain relevant invariants and independent review. Exhaustive G0-G7 counts, deferred engines and human/clinical gates are later work, not prerequisites for synthetic PoC operation. Existing historical evidence retains its original scope.

Read [execution entry point](../../implementation-prompt.md) and your assigned gate bundle first. This document governs future application implementation, not the documentation migration.

## Research basis and model configuration

Research checked October 4, 2026. The 2026-10-19 checkout contains planning documents and local infrastructure configuration, but no application source. Inspect current state and applicable repository instructions before implementation.

The historical prompting rationale is recorded below with its public guide and reviewed source revision. Do not depend on an unavailable conversation attachment. These are execution guidelines for a future app implementation; the current runtime instructions take precedence.

The workflow uses the [official subagent guidance](https://learn.chatgpt.com/docs/agent-configuration/subagents?surface=app). Under the user's 2026-10-24 [model policy](../../implementation-prompt.md#launch-contract), reserve `gpt-6-astra/medium` only for critical gate plans and critical gate reviews; ROOT records the material gate reason before assignment. Default to `gpt-6.1-sol/high` for all other planning, critique, review, implementation, integration, repairs, verification, documentation and ordinary decisions. `gpt-6-luna/high` remains for bounded exploration, summaries and helpers. Only difficult Sol implementation may increase to `xhigh` without user confirmation, with the reason recorded in the ledger and handoff. These are runtime selectors, not claims about public API identifiers. Verify actual availability/settings and report unsupported choices without silent substitution. Historical model records remain unchanged.

The supplied [OpenAI Codex prompting guide](https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide) currently identifies `gpt-5.3-codex`, not GPT-6.1-Sol. Its [source notebook](https://github.com/openai/openai-cookbook/blob/main/examples/gpt-5/codex_prompting_guide.ipynb), reviewed at blob `30b2eab0ba05235b8070c9838352cfdd2546d8b8`, supports the general practices below. Their application to GPT-6.1-Sol is an engineering recommendation to evaluate, not a claim of model-specific published research.

| Practice from the guide | Application to REMission |
| --- | --- |
| Start from the coding harness's standard instructions and make targeted additions | Supply this project's scope, contracts, delegation rules, and gates; avoid copying the entire starter system prompt into every task |
| Autonomy and persistence through implementation and verification | Require runnable artifacts and observed evidence at each gate; a plan or agent's assertion is insufficient |
| Gather context before editing; batch independent reads | Read the relevant plan sections and interfaces together; sequence dependent work and shared-file writes |
| Prefer native tools and `apply_patch` | Use tools actually exposed by the harness; `rg` for discovery and native patching for edits; do not invent tool names |
| Explicit custom-tool instructions | Explain when to use Playwright MCP, what state to inspect, and what evidence to return |
| Preserve conventions, types, errors, and unrelated edits | Establish typed contracts first; surface failures instead of returning fabricated successful estimates |
| Native compaction for long runs | Use supported compaction and durable task records; resume from commits, contracts, and evidence instead of restarting |
| Evaluate prompt changes against observed failures | Use seeded REMission tasks to measure constraint violations, completion, rework, and time to a useful artifact |

The older guide's suggestions do not override the project's explicit model policy: Sol/high is the default, with xhigh only for difficult implementation and a recorded reason; Astra/medium is limited to critical gate plans/reviews. Routine edits and clarifications do not automatically require Astra. These are requested workflow settings, not benchmark results. Do not configure unavailable settings.

The guide's older starter text discourages prompted preambles, while its later sections allow them for GPT-5.3-Codex and subsequent versions. Follow the current harness's communication instructions. Give concise progress updates without ending a working turn at a preamble. In a custom API harness, preserve tool results and supported assistant phase metadata; the guide specifically requires `phase` preservation for GPT-5.3-Codex. Verify applicability before using that field with another model.

Multi-agent orchestration and the phase map below are REMission-specific workflow choices. Parallel tool calls alone do not provide subagents, isolated workspaces, or a task scheduler. The harness must expose actual delegation tools. Do not describe simulated role-playing as delegated work.

## Subagent runtime configuration

Use one primary orchestrator and at most two concurrently open non-Luna subagent threads. **GPT-6 Luna (`gpt-6-luna`) helpers do not count toward the project's two-worker limit.** Count idle as well as running non-Luna threads. The current assigned runtime capacity is four total live threads including ROOT; Luna helpers share that total capacity. Where a runtime setting counts spawned threads but excludes the primary, the corresponding illustrative setting is three children plus ROOT:

```toml
[agents]
enabled = true
# If this setting excludes ROOT: two non-Luna workers plus one Luna helper.
max_concurrent_threads_per_session = 3
```

Four including ROOT is current capacity, not a separate project limit on Luna. Verify actual counting semantics and effective capacity at launch; do not use a total cap of two to express the non-Luna policy. This documentation update changes no local/global configuration. Only the orchestrator spawns agents, including Luna helpers requested by workers. Do not create separate top-level tasks or nested agents to bypass runtime limits. Keep separate non-Luna and total thread counts, with open IDs, effective model/effort, ownership, worktrees/branches/bases and queued requests in the ledger. Acquire a non-Luna slot before changing Luna to Astra/Sol.

Confirm supported spawn, message, wait, resume/reuse, and close/release controls. A completed or interrupted turn may still occupy an open thread. Release completed threads before replacements, or reuse compatible existing threads if closing is unavailable. If the model/effort cannot be selected, the cap cannot be honored, or required threads cannot be released or reused, report the specific blocker and keep affected work queued; do not fall back to solo implementation.

Set the model and reasoning effort explicitly on every assignment so parent inheritance cannot silently choose the wrong settings. If custom agent files are used, inspect their effective model and effort because file settings can override spawn settings. Use the runtime's supported independent-context spawn option when required for model overrides, supplying the bounded gate context and assignment rather than relying on inherited history. Subagents inherit session permissions; do not attempt to override those in custom role files.

Schedule non-Luna work in waves: Sol/high routine planning/critique, implementation and different-worker review; use Astra/medium only for critical gate plans/reviews after ROOT records why. Route repairs to Sol, then obtain appropriate independent re-review; do not add an automatic Astra loop. Luna helpers may run alongside workers when total capacity permits. At current capacity, ROOT plus two non-Luna workers plus one Luna helper totals four; three non-Luna workers are forbidden. Follow the [delegation contract](delegation.md#delegation-and-integration-contract) for capacity/dependency queuing and waiting-worker checkpoints.

Provision a separate Git worktree for every subagent before it starts, including read-only roles and helpers. Supply the absolute checkout path and verify that commands and edits use it; native subagent spawning does not itself satisfy this requirement. Writing workers own task branches from accepted commits; reviewers use separate worktrees pinned to the exact candidate. Use supported managed-worktree tools or native Git, preserve unrelated changes, and report unavailable isolation without a shared-checkout fallback. Follow [worktree isolation and reviewed merges](delegation.md#worktree-isolation-and-reviewed-merges) for lifecycle, review, and integration.


## Codex guide rules applied to this implementation

Apply these rules within each role's responsibilities: the orchestrator communicates with the user, manages progress, distributes tasks, provisions isolated worktrees, and opens/merges reviewed PRs; subagents execute technical work below in their assigned worktrees. The supplied guide is reference material, not a replacement for higher-priority runtime instructions or the project's specification.

### Exploration, tools, and editing

- Plan the needed reads before calling tools; batch independent file searches and reads. Use the harness's native parallel facility. The guide names `multi_tool_use.parallel`; use that when available, but do not invent it in a harness with a different supported mechanism. Serialize dependent work and conflicting mutations.
- Prefer dedicated tools for their supported actions; use `rg`/`rg --files` for text/file discovery. Use shell commands only where no suitable dedicated tool exists, pass a command string, and set the working-directory argument explicitly.
- Use the native `apply_patch` implementation for manual file edits. Use generators/formatters for generated files. Treat tool-provided `L123:` prefixes as line metadata, never source text.
- Search for reusable code before introducing helpers. Read sufficient context, then make coherent edits. Keep types explicit; avoid `as any` and double assertions. Surface errors with useful context rather than broad catches, silent returns, or successful-looking fallbacks.
- Preserve unrelated changes. Do not amend commits or use destructive resets/checkouts without explicit authorization. Verify assigned worktree ownership and pause affected work if unexpected external edits appear; do not move work into another agent's checkout.
- Default to ASCII in new source files unless established content or product needs justify Unicode. Comments should explain non-obvious reasoning rather than repeat the code.

### Autonomy, plans, and closeout

Start useful work promptly. Choose reasonable reversible defaults, implement through verification, and avoid repeated discovery without a new question to resolve. The orchestrator's work is user communication and feedback, plan and gate progress, task distribution, dependency scheduling, worktree provisioning, consolidated reporting, and reviewed PR integration. It delegates technical planning, exploration, source integration/conflict resolution, evidence inspection, and all other substantive technical work. Each worker delivers its assigned artifact and returns questions through the orchestrator. Neither a narration of intended work nor a task list counts as implementation.

Use the native plan tool for substantial work, with multiple steps and at most one `in_progress` step when that is its schema. Update it after actual progress. Parallel worker state belongs in the ledger, not multiple conflicting active plan steps. Do not add broad refactors or tests to a promised scope unless they will be executed.

At each closeout, reconcile every promised task as done, blocked with its reason and required input, or cancelled with its reason. Keep unfinished project tasks in the durable ledger for resumption, but never leave a session plan implying success while work is still pending. Where a plan tool lacks a blocked/cancelled status, record the reason in its explanation and in the ledger without marking blocked work completed.

### Frontend quality adapted to the clinical workflow

Choose intentional typography, spacing, color tokens, and responsive composition; avoid interchangeable KPI walls, arbitrary purple themes, and decorative treatment scores. Honor the NHS-informed accessible component foundation and the plan's stable shell, patient identity, visible uncertainty, and progressive disclosure. The guide's visual-design suggestions do not require adding gradients, unusual fonts, or animations that compromise readability or decision context.

Frontend workers must deliver connected, runnable screens at desktop and narrow viewports. Use purposeful motion only when useful and respect reduced-motion preferences. Loading, missing-data, error, and hold states are part of completion. Have the browser worker inspect rendered screenshots as well as accessibility snapshots; text-only inspection cannot establish layout quality.

### Long-running harness behavior

Use supported native compaction before the context exceeds the model limit. In a custom Responses API harness, follow the guide's `/responses/compact` flow only for models/endpoints that support it: retain the returned compaction item including `encrypted_content` in subsequent input, alongside required conversation state. A hand-written checkpoint is useful durable state, but does not replace native compaction.

For the guide's documented GPT-5.3-Codex integration, preserve assistant `phase` values (`null`, `commentary`, `final_answer`) when reconstructing history; never attach `phase` to user messages. Verify support for GPT-6.1-Sol instead of blindly copying that API field. For supported prompted updates, keep them brief and grounded in outcomes, then continue execution rather than terminating at a preamble.

When building a custom harness, use clear tool names and semantic arguments, distinguish search-result formats, and document when/why/how to call each MCP tool. Enable supported parallel tool calls for independent operations and preserve call/result associations. The guide suggests about 10,000 tokens per tool response, retaining beginning and end when truncating. Record truncation explicitly and fetch omitted ranges needed for a decision; never claim to have read a whole specification from truncated output.

Final reports should state the delivered behavior, executed checks, and material limitations concisely, with file/artifact references rather than a dump of the output. For reviews, lead with reproducible findings ordered by severity. Use targeted metaprompting and repeated evaluations when slow starts, repeated reading, or noisy updates occur; do not expand the prompt with untested instructions.


## Selected methods runtime

Read the [methods library decisions](../plans/methods/00-library-decisions.md) for the selected stack: PyMC with explicit native NUTS initially and compatible ArviZ, NumPy/SciPy, statsmodels, scikit-learn, StochTree for the matched BCF comparator and COBA for offline contextual OPE. Offline R jobs supply RBesT prior preparation, SBC and MRTAnalysis reference checks through versioned artifacts. Do not add Stan as a second application backend by default. nutpie requires the documented targeted acceleration check. Follow [selective future benchmarking](../plans/methods/03-validation-and-benchmarks.md), retaining all required validation and the resource pilot.

## How to launch

1. Open a checkout of `esbraun/REMission` and inspect the current branch, working tree, `plan.md`, applicable `AGENTS.md` files, and available tools.
2. Verify role-specific model/effort, the two-non-Luna worker limit, and separate total runtime capacity for Luna helpers under [subagent runtime configuration](#subagent-runtime-configuration). Confirm delegation, thread lifecycle controls, separate Git worktree provisioning, and worker access to required files and tools. Use the existing primary thread as the sole orchestrator; no additional orchestrator thread is needed.
3. Delegate Playwright MCP setup and browser availability checks using [browser validation](browser-validation.md). Record tool or environment blockers before depending on them.
4. Give the orchestrator the launch prompt in the next section. Use the task template for each delegated package; use the browser template for UI checks.
5. Continue through the PoC amendment queue with persisted acceptance checks. If the run is interrupted, resume unfinished task IDs from the ledger. A bounded session can end with a precise checkpoint but must not label the complete app done.

The implementation run should create `docs/implementation/` for the task ledger, requirement mapping, contracts, decisions, validation manifests, and handoff. These paths are proposed outputs, not existing files. Keep bulky fits, screenshots, traces, and generated datasets in documented artifact storage rather than committing all of them by default.


## Ready-to-use orchestrator launch prompt

```text
Implement esbraun/REMission's plan.md as a runnable, reproducible synthetic
demonstration. Read implementation-prompt.md, the plan.md index, shared invariants, and the assigned gate bundle
before decomposition. Follow applicable repository instructions and the
runtime's higher-priority instructions. Treat plan.md as the product and
methods specification; this playbook supplies the execution workflow.
Apply its "Codex guide rules applied to this implementation" to every worker.
Read docs/execution/engineering-guidelines.md for DRY, maintained OSS reuse,
simple design, selective UI skill usage and meaningful seam/integration tests.
UI workers verify and read the applicable installed skills and rule files.
Retain the existing architecture and deployment outside Vercel.
Use native tools, batch independent reads, preserve types and unrelated edits,
surface errors, and carry each package through observed verification.

You are the orchestrator. Delegate EVERY work package to a real subagent:
discovery, contracts, scaffolding, simulator, ingestion, statistical models,
protocols, support policy, services, UI, tests, evaluation, documentation,
integration repairs, technical planning, critique, and independent review.
Your role covers user communication and feedback, plan/gate progress, task
distribution, dependency scheduling, worktree provisioning, consolidated
reporting, and opening/merging reviewed PRs. Default to a Sol/high planner for
decomposition and contracts; use Astra/medium only for critical gate plans
with your reason recorded before assignment. Schedule integration and
evidence checks through subagents and use their reports to update gate status.
Use an integration subagent for source edits and repairs; do not become the
implementer, explorer, planner, tester, or reviewer when a worker is blocked.

Use gpt-6-astra/medium ONLY for critical gate plans and critical gate reviews.
Record the concrete material-gate reason before assigning Astra; do not turn
routine edits/clarifications into automatic Astra review loops. Default to
gpt-6.1-sol/high for other planning, critique, independent review, implementation,
integration, repairs, verification, documentation and ordinary decisions;
use gpt-6-luna at high for bounded exploration, summaries and helpers.
Native work alone is not critical: unchanged-control compatibility, fixtures,
documentation and finite failed-stage checks default to Sol/high. Batch critical
review at the actual gate boundary unless a material new boundary needs it sooner.
Sol implementation may increase to xhigh for difficult work without user
confirmation; record the reason. Set model/effort explicitly and verify effective
settings, including custom-agent overrides. Never silently substitute models.

Keep at most TWO non-Luna subagent threads concurrently open, excluding this
primary orchestrator. GPT-6 Luna (gpt-6-luna) helpers DO NOT COUNT toward that
two-worker limit. Spawn requested Luna helpers alongside two Astra/Sol workers
when runtime capacity allows; do not queue them merely because both worker
slots are occupied. Only you spawn or assign agents.
The runtime total cap counts ALL spawned threads, including Luna. Verify enough
total capacity for two workers plus helpers; a global cap of two is incorrect
for this policy. Track non-Luna and total counts separately, including idle open
threads. There is no separate project count limit for Luna. Reserve a worker
slot before switching Luna to a non-Luna model. Queue for actual runtime limits,
resource conflicts, or dependencies; reuse threads and release completed ones.
If runtime capacity prevents needed helpers, checkpoint a waiting worker to free
capacity. Do not spawn nested agents or separate top-level tasks.

Give EVERY subagent its own Git worktree, including explorers, planners,
reviewers, browser workers, and Luna helpers. Assign absolute checkout paths,
task branches, and accepted base commits; verify the worker uses that path for
commands and edits. Reviewers inspect the exact candidate in their own detached
worktrees. Never use a shared checkout as a fallback. Record worktree ownership
in the ledger and preserve unfinished commits/artifacts when freeing a slot.

Delegate tool/repository exploration and consume its capability report; check
the orchestration controls and open-thread inventory before dispatching work.
If delegation is unavailable, report that blocker rather than replacing the
requested workflow with solo implementation. If threads cannot be closed,
reuse compatible ones; report a blocker if required model settings or capacity
cannot be achieved. If Playwright MCP is unavailable,
continue independent backend work but keep the UI acceptance gate blocked.

Assign creation of a requirement-to-task-to-test map for all mandatory plan
requirements and a durable task ledger under docs/implementation/. Maintain
plan progress and task status from subagent reports. Each task has a stable
ID, plan references, input contracts, output paths, worktree/branch/base and
candidate commit, integration target, exclusive write ownership,
model/effort, escalation reason, helper requests, dependencies, acceptance checks,
evidence paths, status, and separate reviewer identity. Separate required
work from optional extensions. Every required task must have a subagent owner.

Use the suggested React/TypeScript, Python/FastAPI, local immutable storage,
DuckDB/Parquet, and one Bayesian backend unless inspection establishes a sound
reason to change them. Pin dependencies and record actual run commands after
scaffolding. Choose routine reversible engineering defaults and record them.
Do not invent completed clinician review, participant testing, ethics approval,
clinical evidence, or model results. Implement provisional synthetic settings
and keep real stakeholder review explicitly outstanding where unavailable.

Follow the PoC amendment implementation queue and POC-1 through POC-6, with
the bounded POC-VAL study. The full phases 0-7 below are later scope. Parallelize only
independent tasks in separate worktrees with bounded writes. Start with contracts
and the generated-panel, physician-decision and simulation-advance loop.
Do not stop at static screens or a mock recommendation engine. Use actual Bayesian
fitting, N-of-1 analysis, MRT/WCLS and bounded support computation for the
minimal representatives and selected ablations; defer generalized protocols. Cached outputs must originate from reproducible, versioned real runs.

Require frontend workers to deliver intentional, accessible, responsive screens
within the stable clinical shell, including all error and missing-data states.
Have a browser subagent inspect rendered screenshots before visual acceptance.

Preserve all hard invariants from plan.md. The demonstration uses synthetic
patients, synthetic quantitative trials, fictional MED_A/MED_B, and replay
adapters. No real orders, messages, device accounts, or patient data. Clinical
eligibility, consent, and coordination rules constrain the learner. Wearables
are supportive measurements and do not diagnose, prescribe, or detect acute
illness. No truth or future-available records reach learner inputs.

Require Playwright MCP validation by a browser subagent for every user-visible
work package, then a complete workflow pass on the integrated commit. Have the
browser subagent inspect accessibility snapshots, use visible controls, verify
service persistence, capture screenshots, and check console/network failures.
Assign critical browser discoveries to Sol for repeatable Playwright Test
regressions. Browser checks
do not replace statistical tests, manual accessibility review, or clinician
task sessions.

Have different reviewers examine plans, methods, software invariants and UI
evidence: Sol/high for routine review; Astra/medium only for critical gate
plans/reviews under the entry point's classification and recorded ROOT reason.
Do not treat self-review as independent. Route fixes to Sol then obtain the
appropriate different-worker re-review; assign integration and gate reruns within the two-non-Luna worker
cap. Luna helpers remain exempt. Never accept a worker's unsupported "done" claim.

Persist task state, commits, contracts, model/data versions, seeds, commands,
results, and blockers before compaction or handoff. Use supported native
compaction; preserve required tool-call/result and assistant phase metadata.
Reconcile session promises as done, blocked, or cancelled with reasons, and
retain unfinished project task IDs for resumption. Give brief meaningful
progress updates under the runtime's communication policy. Continue authorized
work without repeated confirmation for routine implementation choices.

Deliver a clean-checkout runnable PoC satisfying the amendment functional cases,
reproducible evaluation outputs, source-to-requirement traceability, and an
honest report of unresolved gates. You are authorized to open PRs and merge
worktree branches into assigned integration targets without repeated user
confirmation once the appropriate independent reviewer under the model policy deems the exact head/base
ready to ship, required task/gate and repository checks pass, findings are
resolved, and dependencies are accepted. Respect branch protections. Refresh
review and affected checks whenever the head or target base changes. Assign
conflicts and source repairs to Sol, then re-review; do not resolve them yourself.
Record PR URL, reviewed head/base, evidence, and merge commit, and have a worker
verify the integrated result. Merging code does not complete outstanding human
or clinical gates. Deployment and clinician contact retain their own authorization.
```
