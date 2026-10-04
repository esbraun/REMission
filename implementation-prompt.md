# REMission implementation prompt and execution playbook

Use this document to implement [plan.md](plan.md) with GPT-6.1-Sol as an orchestrator, subagents for every work package, and Playwright MCP for browser validation. This document is an implementation instruction set; adding it to the repository does not implement or validate the app.

## Research basis and model configuration

Research checked October 4, 2026. The repository currently contains only `plan.md`; there is no application, established directory layout, or repository `AGENTS.md` to inherit. Recheck that before implementation.

The requested model name, “open gpt sol 6.1,” is interpreted here as **GPT-6.1-Sol**, exposed in this coding environment as `gpt-6.1-sol`. That environment selector is not evidence of a public API model identifier. Verify the exact model identifier, supported reasoning settings, context handling, and subagent capabilities in the actual runtime. Do not silently substitute another model.

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

The guide suggests medium reasoning as a general starting point and high/xhigh for demanding work on its documented model. For GPT-6.1-Sol, choose only supported settings and evaluate them: routine scaffolding and UI tasks can start at medium; causal modeling, protocol design, and invariant review may warrant high. These are initial hypotheses, not benchmark results. Do not configure unavailable settings.

The guide's older starter text discourages prompted preambles, while its later sections allow them for GPT-5.3-Codex and subsequent versions. Follow the current harness's communication instructions. Give concise progress updates without ending a working turn at a preamble. In a custom API harness, preserve tool results and supported assistant phase metadata; the guide specifically requires `phase` preservation for GPT-5.3-Codex. Verify applicability before using that field with another model.

Multi-agent orchestration and the phase map below are REMission-specific workflow choices. Parallel tool calls alone do not provide subagents, isolated workspaces, or a task scheduler. The harness must expose actual delegation tools. Do not describe simulated role-playing as delegated work.

## How to launch

1. Open a checkout of `esbraun/REMission` and inspect the current branch, working tree, `plan.md`, applicable `AGENTS.md` files, and available tools.
2. Select the verified GPT-6.1-Sol runtime configuration. Confirm that the orchestrator can spawn, message, wait for, and resume subagents, and that delegated agents can access the required files and tools.
3. Connect Playwright MCP as described below and verify browser availability. Record tool or environment blockers before depending on them.
4. Give the orchestrator the launch prompt in the next section. Use the task template for each delegated package; use the browser template for UI checks.
5. Continue through phases 0–7 with persisted gates. If the run is interrupted, resume unfinished task IDs from the ledger. A bounded session can end with a precise checkpoint but must not label the complete app done.

The implementation run should create `docs/implementation/` for the task ledger, requirement mapping, contracts, decisions, validation manifests, and handoff. These paths are proposed outputs, not existing files. Keep bulky fits, screenshots, traces, and generated datasets in documented artifact storage rather than committing all of them by default.

## Ready-to-use orchestrator launch prompt

```text
Implement esbraun/REMission's plan.md as a runnable, reproducible synthetic
demonstration. Read implementation-prompt.md and the entire current plan.md
before decomposition. Follow applicable repository instructions and the
runtime's higher-priority instructions. Treat plan.md as the product and
methods specification; this playbook supplies the execution workflow.

You are the orchestrator. Delegate EVERY work package to a real subagent:
discovery, contracts, scaffolding, simulator, ingestion, statistical models,
protocols, support policy, services, UI, tests, evaluation, documentation,
integration repairs, and independent review. You own decomposition, dependency
ordering, file ownership, integration decisions, evidence reconciliation, and
the final delivery. Use an integration subagent for source edits and repairs;
do not become the untracked implementer when a worker is blocked.

Inspect the actual tool inventory, repository state, and concurrency limits.
If delegation is unavailable, report that blocker rather than replacing the
requested workflow with solo implementation. If Playwright MCP is unavailable,
continue independent backend work but keep the UI acceptance gate blocked.

Create a requirement-to-task-to-test map for all mandatory plan requirements.
Create a durable task ledger under docs/implementation/. Each task has a stable
ID, plan references, input contracts, output paths, exclusive write ownership,
dependencies, acceptance checks, evidence paths, and status. Separate required
work from optional extensions. Every required task must have a subagent owner.

Use the suggested React/TypeScript, Python/FastAPI, local immutable storage,
DuckDB/Parquet, and one Bayesian backend unless inspection establishes a sound
reason to change them. Pin dependencies and record actual run commands after
scaffolding. Choose routine reversible engineering defaults and record them.
Do not invent completed clinician review, participant testing, ethics approval,
clinical evidence, or model results. Implement provisional synthetic settings
and keep real stakeholder review explicitly outstanding where unavailable.

Follow phases 0–7 and the dependency gates in this playbook. Parallelize only
independent tasks with disjoint writes. Start with contracts and a minimal
vertical replay; expand to the full hybrid workflow rather than stopping at
static screens or a mock recommendation engine. Use actual Bayesian fitting,
randomization, WCLS analysis, and bounded policy logic for their respective
gates. Cached outputs must originate from reproducible, versioned real runs.

Preserve all hard invariants from plan.md. The demonstration uses synthetic
patients, synthetic quantitative trials, fictional MED_A/MED_B, and replay
adapters. No real orders, messages, device accounts, or patient data. Clinical
eligibility, consent, and coordination rules constrain the learner. Wearables
are supportive measurements and do not diagnose, prescribe, or detect acute
illness. No truth or future-available records reach learner inputs.

Require Playwright MCP validation by a browser subagent for every user-visible
work package, then a complete workflow pass on the integrated commit. Inspect
accessibility snapshots, use visible controls, verify service persistence,
capture screenshots, and check console/network failures. Convert critical
browser discoveries into repeatable Playwright Test regressions. Browser checks
do not replace statistical tests, manual accessibility review, or clinician
task sessions.

Have independent review subagents examine methods, software invariants, and UI
evidence. Send failures back to the owning worker, integrate fixes, and rerun
the affected gates. Never accept a worker's unsupported "done" claim.

Persist task state, commits, contracts, model/data versions, seeds, commands,
results, and blockers before compaction or handoff. Give brief meaningful
progress updates under the runtime's communication policy. Continue authorized
work without repeated confirmation for routine implementation choices.

Deliver a clean-checkout runnable demo, seeded cases from plan.md section 17,
reproducible evaluation outputs, source-to-requirement traceability, and an
honest report of unresolved gates. Open implementation PRs when authorized by
the user; do not infer authorization to merge, deploy, or contact clinicians.
```

## Delegation and integration contract

The orchestrator is the only owner of task scheduling, gate status, integration ordering, and final PR coordination. All work packages have subagent owners; each package also receives independent review. Reuse workers across related tasks instead of spawning an unbounded agent per bullet. Required work is never dropped because the agent limit is reached: queue it.

Suggested roles are contract/workflow, simulator/data, Bayesian methods, experiments/support, service/integration, frontend, browser/accessibility, independent methods review, and release/documentation. These are responsibilities, not a requirement to run nine agents simultaneously. Leave capacity for integration and review within the actual runtime limit.

Before parallel writes, allocate disjoint paths or isolated worktrees. If worktrees are supported, branch workers from a known integration commit and integrate reviewed commits in dependency order. If workers share one tree, enforce exclusive file ownership; workers must not commit the whole shared worktree or stage other workers' files. Reserve dependency manifests, lockfiles, root configuration, shared schemas, generated clients, and migration numbering for the designated integration worker. Schedule cross-cutting changes explicitly.

Workers read their assigned plan sections and relevant shared contracts, not just a coordinator's paraphrase. A change to a shared interface becomes a versioned contract proposal; integration accepts it and informs consumers before dependent work proceeds. On a worker failure, preserve its changes, record the failure, and resume or reassign the task with explicit ownership. Stop dependent tasks rather than filling the gap with invented results.

Every ledger entry should contain:

```yaml
id: P5-HISTORY-01
plan_sections: [5, 13, 14, 16]
owner_role: service
depends_on: [P0-CONTRACTS, P1-REPLAY]
base_commit: <observed commit>
write_paths: [<assigned paths>]
inputs: [<versioned contracts and fixture IDs>]
outputs: [<implementation, tests, documentation>]
acceptance: [<observable checks and commands>]
reviewer_role: invariant-review
status: queued # running | needs_review | failed | blocked | complete
evidence: [<result manifests and artifact paths>]
blocker: null
```

### Worker assignment prompt

```text
You own task <ID>: <concrete behavior>.
Read plan.md sections <sections>, implementation-prompt.md, applicable
AGENTS.md, and contracts <paths/versions>. Base commit: <commit>.
Dependencies already accepted: <IDs and evidence>. Write only <paths>.
Coordinate shared-interface changes with the orchestrator before editing them.

Implement <specific outputs>. Cover <normal flow>, <failure flow>, and
<invariants>. Use actual computation where required; label fixtures and cached
results with their generation provenance. Do not change plan scope or claim
stakeholder approval. Inspect existing code and tests before adding abstractions.

Run <task-specific checks>. For visible UI changes, arrange a Playwright MCP
handoff with the browser worker using <case IDs>, <URL>, and <expected behavior>.
You are not done until required verification and independent review are accepted.

Return: task ID; changed files/commit or patch; contract versions; exact checks
and outcomes; seed/data/model versions; evidence paths; limitations; blockers;
and integration instructions. Distinguish observed results from expectations.
```

### Review prompt

```text
Review task <ID> independently against plan.md sections <sections>, contract
<version>, and accepted base <commit>. Inspect the diff and verification evidence.
Check causal/temporal leakage, state transitions, invalid actions, fabricated
outputs, and relevant failure paths. Reproduce targeted checks where needed.
Return findings ordered by severity with file references and reproduction steps.
If no findings, state the reviewed scope and remaining evidence gaps. You cannot
approve an unexecuted acceptance check on the basis of an implementer's assertion.
```

## Phase map, dependencies, and acceptance evidence

Use `plan.md` section 15 as the phase sequence. The suggested package names below organize the work; derive finer tasks from every requirement in sections 1–18. In particular, enumerate all section 6 scenarios, all section 12 assignment states, all section 16 invariants, and all section 17 demonstration cases in the requirement map.

| Phase and delegated packages | Dependencies and reviewable output | Gate evidence |
| --- | --- | --- |
| **0: workflow, estimands, contracts, UX prototype** | Read the complete plan; define clinical and learning states separately, permissions, intercurrent-event strategies, per-component consent, eligibility/holds, configurable thresholds, evidence registry, and source-to-design map | Versioned data dictionary and estimand contracts; sketch both dashboards and each assignment stage; distinguish provisional engineering assumptions from actual clinician/human-factors review |
| **1: foundation, events, adapters, simulator** | After phase 0 contracts: scaffold services/UI/tooling; implement replay clock, event/available-at times, corrections, synthetic external trials, and separated truth storage | Reproducible smoke/demo presets and all stress scenarios; export leakage tests; synthetic FHIR-shaped/Oura-like records labeled as mocks; deterministic replay and seeded case manifest |
| **2: priors, longitudinal model, rollouts, model registry** | Phase 1 exports and phase 0 estimands; use one PyMC or Stan backend and actual offline fitting | Weak/complete/robust borrowing comparisons; source-to-model marginal contrast bridge; at least two heterogeneity-prior sensitivities; prior/posterior predictive checks; convergence and estimand-specific effective sample diagnostics; repeated sharp-null false-ranking results |
| **3: N-of-1 and behavioral escalation** | Accepted state, eligibility, consent, assignment/delivery, and analysis contracts; phase 2 shared evidence handling | Approved reversible protocols, known randomization probabilities, carryover/rebound/rescue and instability checks; frozen support policy; continuing behavioral skills with sequential escalation rather than on/off crossover |
| **4: MRT, WCLS, bounded support bandit** | Accepted protocol/controller contracts; phase 1 proximal outcomes and availability; phase 3 coordination rules | WCLS causal-excursion analysis separate from the Bayesian selection model; unavailable-point logs; probability bounds and burden enforcement; missing reward handling; no medication actions; fixed/MRT/adaptive comparisons |
| **5: service integration, clinician UI, history** | Accepted phase 0–4 interfaces/results; minimal shell may exist earlier, but full acceptance waits for integrated engines | Complete patient loop; all assignment-stage panels; atomic/version-checked approvals; immutable as-known-then snapshots; evidence inspection; Playwright MCP matrix and persistent backend checks |
| **6: repeated evaluation, accessibility, usability** | Integrated services and saved runs; analysis protocols fixed before comparison | Bias/coverage/interval width/abstention/constraint violations/burden/regret with Monte Carlo uncertainty; stated comparator estimands; MCP validation, automated regressions, manual accessibility results, and actual clinician task-session results or explicit outstanding human-review gates |
| **7: fresh-environment reproduction and handoff** | Accepted software/methods/browser gates and reconciled human-review status | Pinned dependencies, documented seed/run commands, saved fit provenance, evaluation report, test results, limitations, and clean-checkout reproduction by a release subagent |

Phase 0 contracts precede detailed visual design. After contracts, scaffold a thin patient replay from ingestion through assessment, eligible choices, approval, follow-up, and immutable historical review. It is an integration milestone, not permission to replace the phase 2–4 algorithms with stubs. Independent simulator, UI shell, and storage tasks can then proceed concurrently within their contracts. Do not parallelize consumers of an unresolved schema.

Real clinician participation, clinical eligibility review, and human-factors acceptance criteria cannot be manufactured by subagents. Implement synthetic defaults and task protocols, continue independent engineering, and report those review gates as outstanding until the actual participants provide evidence. Browser automation does not satisfy the plan's human-subject usability work.

Optional extensions remain explicit: long-horizon RL, longitudinal DML, additional borrowing approaches, and retrospective re-evaluation must not displace mandatory hybrid functionality. Include the required single-decision BCF comparator where its estimand matches; label incompatible comparisons rather than implying equivalence.

## Project invariants to carry into every relevant task

These summarize critical constraints; workers must also read the full applicable plan sections.

- **Synthetic boundary:** use fictional MED_A/MED_B and generated quantitative study effects. Real publications supply rationale in a separate reference registry. Do not connect real EMRs, wearable accounts, messages, or orders. Keep the persistent synthetic-demo label and the limitation on acute-illness monitoring visible.
- **Eligibility before ranking or assignment:** clinician-entered restrictions, clinical holds, current consent/oversight, and coordination rules constrain the permitted action set. Missing/expired/withdrawn consent prevents the relevant randomization. Strong-inhibitor exclusion and moderate-inhibitor prescriber review are distinct illustrative outcomes, not a real prescribing engine.
- **Separate decisions and events:** clinical state, learning state, view context, recommended/approved/assigned/delivered/taken action, and patient preference have distinct contracts. The server determines permissions; tab position does not.
- **Time and lineage:** learners see only records available at the decision cutoff. Preserve event and transaction times, duplicates, late uploads, and correction lineage. Historical snapshots retain original evidence/model/policy versions and remain read-only.
- **Truth separation:** latent states, structural parameters, and oracle counterfactuals are accessible only to the separate evaluator. Verify process/storage access as well as exported field names.
- **Clinical outcomes:** label ISI version/recall window and configurable benefit thresholds. No ISI after death; no scoring missing rewards as good or bad. Show diary/report and wearable estimates separately, with gaps and device shifts.
- **Borrowing discipline:** compatible synthetic trial averages constrain their matching marginal contrast, not arbitrary ordinal coefficients, medication effects, prompt rewards, or unsupported modifiers. Never count trial IPD plus its summary, a MAP prior plus the same external likelihood, or repeated observation likelihoods twice.
- **Causal discipline:** use longitudinal g-computation and state identification assumptions. Do not claim double robustness or call it Bayesian DynamicDML. Validate sparse overlap, hidden confounding, missingness, intercurrent events, and the sharp null; computational convergence is not causal validity.
- **Individual learning:** preserve carryover and rebound as different processes; record blinding and assignment effects. Durable CBT-I skills are not washed out for crossover. Freeze each patient's support policy during an N-of-1 block and washout; other patients may still update pooled learning.
- **Support learning:** log availability and probabilities before outcomes; zero mass on excluded actions, prespecified bounds for eligible actions, and independent burden/clinical constraints. WCLS is the MRT inferential analysis; the Bayesian bandit is an action-selection working model.
- **Approval and UX:** no default selection because a card ranks first; separate ordinary treatment choice from randomization approval. Check current patient/state versions atomically and reject stale approval with a specific refresh path. Historical links remain historical after refresh; switching patients clears drafts before controls activate.

## Playwright MCP setup and ownership

Use the official [Microsoft Playwright MCP](https://github.com/microsoft/playwright-mcp) documentation, reviewed at README blob `7cecc4144025919587399336dff41b0d3ba366ad`. It recommends accessibility snapshots for interaction and explains that concurrent persistent profiles can conflict. The upstream README also discusses a CLI alternative; this project explicitly requires **MCP** for agent browser validation. Playwright Test adds repeatable regressions, rather than replacing MCP exploration.

The upstream bootstrap command for Codex is:

```sh
codex mcp add playwright npx "@playwright/mcp@latest"
```

For a reproducible run, choose and record an actual verified package version instead of leaving `latest` unpinned. If the harness uses a JSON MCP configuration, adapt this template to its documented location:

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": [
        "@playwright/mcp@<verified-version>",
        "--headless",
        "--isolated",
        "--output-dir",
        "artifacts/playwright-mcp"
      ]
    }
  }
}
```

The version placeholder must be resolved before running. Install the selected browser/runtime prerequisites according to that version's documentation and verify startup; do not assume package installation proves a browser works. Inspect actual MCP schemas because tool prefixes, capabilities, and parameters vary. Do not use unrestricted file access or weaken browser isolation as a routine workaround.

Delegate setup and the browser smoke check to a tooling/browser worker. If subagents inherit one shared MCP session, serialize browser tasks through a single browser worker. `--isolated` alone does not give two workers independent tabs when they share the same session. True parallel browser tasks need distinct MCP sessions plus isolated contexts or distinct profiles, separate artifact paths, and preferably separate seeded backend instances. Record that ownership in the ledger.

Start the actual app and service from their documented commands. Record URLs, health-check results, integration commit, fixture seed, replay cutoff, and relevant data/model/policy versions. Validate the integrated app against its real local service, not a detached static prototype. Seed/reset data through a documented synthetic-test interface and verify important UI actions in persistent service records.

### Browser worker prompt

```text
Validate UI task <ID> at <URL> using the connected Playwright MCP tools.
Read plan.md sections 10–13 and 16–17 plus the task's exact acceptance criteria.
Use integration commit <commit>, seed <seed>, and cases <IDs>. Own browser
session <session>; do not race another worker's navigation or mutate shared
fixtures without coordination.

Discover tool schemas. Navigate to the app, obtain an accessibility snapshot,
and interact with visible controls using current snapshot references. Refresh
the snapshot after navigation/state changes; do not guess stale element refs.
Typical tools are browser_navigate, browser_snapshot, browser_click,
browser_press_key, browser_resize, browser_take_screenshot,
browser_console_messages, and browser_network_requests; use the actual names.

Verify both visible behavior and persisted service state. Inspect screenshots
for clipping, density, banners, and charts; a successful click is not a visual
check. Use keyboard interactions for the keyboard task. Do not pass a workflow
by invoking a hidden mutation from browser evaluation instead of its UI control.
Use state-based waits and recorded expectations rather than arbitrary sleeps.

Exercise normal, empty, loading, missing-data, error, clinical-hold, historical,
and stale-version paths. Record unexpected console/network failures, screenshots,
accessible-tree evidence, expected/observed results, and reproduction steps.
Send defects to the owning implementation worker and verify repairs. Return
pass/fail/blocked for each case, artifact paths, versions, and untested scope.
```

### Required integrated browser matrix

| Cases | Required checks |
| --- | --- |
| Clinic and selected-patient dashboards | Patient identity, synthetic label, current/historical context, phase, task owner/due date, count denominators and timestamps, filters, missing reports, separate clinical/learning states |
| Assessment and cold start | Required inputs block premature ranking; inspect compatible evidence, broad modifier uncertainty, prior-only labels, heterogeneity/no-borrowing sensitivity, and endpoint/horizon/direction/interval labels |
| Treatment and all section 12 stages | Enumerate every stage row, including active treatment without a decision, eligibility/design, active block, interim/final review, escalation, support review, hold, and maintenance; stable navigation and five panel slots; appropriate controls and failure states |
| Treatment choice and consent | No recommendation preselected; approval summary and follow-up persist; treatment choice distinct from randomization; missing, expired, and withdrawn consent block relevant assignments and expose the next review step |
| Reversible and durable care | Carryover/rebound/washout/rescue/incomplete outcomes visible; frozen support-policy version; no manual winning-block choice presented as unchanged randomization; durable escalation not on/off CBT-I |
| Support envelope | Permitted actions, probabilities/bounds, availability, burden, reward missingness, and proximal/distal distinction visible; no medication or oncology optimization control |
| Holds, abstention, and failures | Interaction exclusion versus prescriber-review flags; acute concern hold with owner; sparse overlap suppresses superiority claims; no successful-looking substitute when fitting/ingestion fails |
| Wearable/report discordance | Distinct sources and units, missing nights as gaps, version changes, accessible table alternatives, and explanation of quiet-wake bias; no readiness score used as diagnosis or acute-illness detector |
| History and correction lineage | Navigate previous/next decision; old stage renders; banner and cutoff persist through deep-link refresh; as-known-then excludes late uploads/later outcomes; retrospective outcomes separate; no old approval controls; new fits/corrections leave original snapshot unchanged |
| Context/concurrency | Switch patients with an open draft: clear it before re-enabling controls; inject a material clinical update during approval through the seeded test interface: server rejects stale version and UI requires specific refresh/review without silent approval |
| Accessibility and responsive layout | Keyboard completion, focus order/visibility, accessible tab semantics, labels, contrast, zoom/reflow, narrow/desktop viewports, non-color statuses, and chart tables; manual screen-reader/accessibility checks recorded separately |

Map these checks to all thirteen human-factors tasks in `plan.md` section 16 and the eight section 17 stories. Also test the deliberately unsupported recommendation case in the synthetic test environment: the interface must permit the user to decline it and inspect its limitations. It must not be a production source of fabricated evidence.

Browser evidence should identify task/case, commit, browser and MCP versions, viewport, seed, data/model versions, replay time, steps, expected/observed behavior, outcome, screenshots/snapshots, console/network findings, and persisted-record references. Capture evidence after the last relevant repair. If backend, model, seed, or UI changes invalidate a result, rerun the affected checks on the final integrated commit.

MCP provides exploratory workflow evidence. Add reproducible Playwright Test checks for patient switching, stale approval, historical deep links, consent blocking, and keyboard assignment. Keep invariant tests at the service boundary too: disabling a button does not enforce a clinical constraint. A clean accessibility tree or an automated scanner does not establish WCAG conformance or clinician comprehension.

## Verification, prompt evaluation, and handoff

Each task proposes checks that test its actual risk and acceptance contract. Do not require expensive MCMC for every CSS change, and do not treat UI screenshots as evidence of statistical calibration. Separate smoke plumbing, genuine saved-model demonstration, and repeated evaluation runs; the smoke preset is not evidence about borrowing performance.

Before marking a phase accepted, the orchestrator checks that all required tasks have owners, reviews, executed checks, versioned outputs, and no unacknowledged failures. Retain failures and abstention in the report. Model runs must record seeds, distinct observation IDs, priors/transport assumptions, data cutoff, fitting configuration, diagnostics, runtime, and output lineage. Evaluation summaries report Monte Carlo uncertainty and distinguish calibration under model-consistent simulations from robustness under misspecification.

Evaluate this prompt with a small representative suite before broad instruction changes: cold-start prior-only display; consent withdrawal; frozen support during a block/washout; a late upload excluded from an old snapshot; stale approval after a new hold; and sharp-null evaluation reporting. Measure completion against requirements, hard-constraint violations, unsupported claims, rework, latency, and reproducibility. Compare one targeted instruction change at a time across multiple runs; report observed tradeoffs instead of declaring a universally best prompt.

Before compaction, worker reassignment, or session end, persist the integration commit, plan revision, ledger status, contract versions, artifact manifests, failed checks, pending workers, unresolved decisions, and exact next tasks. On resume, verify repository state and dependencies, read those records, and continue unfinished IDs. Do not overwrite accepted historical evidence or forget an outstanding human-review gate.

The release/documentation subagent must reproduce the demo from a clean checkout using the documented commands and pinned versions. The final implementation PR should explain the runnable behavior, include the requirement/gate report and verification evidence, and identify genuinely blocked reviews or computations. Do not call phase 6 complete without the plan's required real usability evidence, or call the synthetic app clinically validated.

For this initial documentation PR, commit only `implementation-prompt.md`. The future execution artifacts and application code described here belong to subsequent implementation work. `plan.md` remains the governing specification.
