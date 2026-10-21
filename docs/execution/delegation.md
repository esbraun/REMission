# Delegation

Read [execution entry point](../../implementation-prompt.md) and your assigned gate bundle first. This document governs future application implementation, not the documentation migration.

## Gate-specific worker and reviewer input

Each task supplies canonical requirement IDs, estimand/version, DGP/scenario versions, cutoff, expected truth/calculation/SE, allowed information set, exact comparator target, source IDs, failure/abstention rules and required artifacts. Use [gate reading bundles](../spec/08-gates-and-release.md#gate-context-and-acceptance), not the entire package. Add these fields to the ledger and worker/reviewer templates below.

Independent methods review checks the generator and truth evaluator against analytic cases, verifies inference and prediction are not conflated, inspects failed fits and undefined targets, and rejects confirmation-data tuning. A source citation without a supported claim/locator is not justification. The reviewer must reproduce relevant checks rather than accept a worker's summary.

## Delegation and integration contract

Use one orchestrator thread, limited to user communication and feedback, plan and gate progress, task distribution, dependency scheduling, and consolidated reporting. It assigns file ownership and schedules integration and final PR work; subagents perform the technical work. All work packages have subagent owners, including exploration, technical planning, critique, implementation, integration edits, testing, evidence inspection, documentation, and release verification. The orchestrator uses returned review evidence to update gate status rather than performing the review itself. Each package receives independent review.

The [entry point's model policy](../../implementation-prompt.md#launch-contract) is mandatory: `gpt-6-astra` at `medium` for planning, review, and critique; `gpt-6.1-sol` at `high` for implementation, integration, repairs, and verification; `gpt-6-luna` at `high` for exploration, summaries, and lightweight helpers. Sol implementation may increase to `xhigh` for difficult work without user confirmation; record the reason in the ledger and handoff. Do not silently substitute unsupported models or efforts.

Keep at most two subagent threads concurrently open, excluding the primary orchestrator, and honor any lower runtime limit. Count idle open threads as well as running ones. Only the orchestrator may spawn agents or distribute tasks; workers request Luna assistance through it and do not spawn descendants. A helper occupies one of the same two slots. When both slots are occupied, queue the helper request, let independent work finish, and release a completed thread before assigning the helper. Never make both workers wait indefinitely for queued helpers: checkpoint and release a waiting worker if needed, preserving its changes and resumption instructions. Reuse suitable workers across related tasks; queue required work instead of dropping it.

Use the runtime's supported lifecycle controls to release completed threads and confirm capacity before replacements. Interrupting or finishing a turn does not prove that a thread is closed. If the runtime cannot close threads, enforce the cap by reusing existing threads only when they can run the required model and effort; otherwise report the capability blocker and retain the queued work. Follow the [runtime configuration checks](runtime-and-workflow.md#subagent-runtime-configuration).

Suggested roles are contract/workflow, simulator/data, Bayesian methods, experiments/support, service/integration, frontend, browser/accessibility, independent methods review, and release/documentation. These are responsibilities assigned in waves within the two-subagent cap. A separate Astra reviewer must inspect implementation and reproduce relevant checks; switching the implementing worker's role or model does not make its self-review independent. Route findings to a Sol worker for correction and then back to the independent reviewer. Apply the same independent critique discipline to technical plans before dependent implementation.

Before parallel writes, allocate disjoint paths or isolated worktrees. If worktrees are supported, branch workers from a known integration commit and integrate reviewed commits in dependency order. If workers share one tree, enforce exclusive file ownership; workers must not commit the whole shared worktree or stage other workers' files. Reserve dependency manifests, lockfiles, root configuration, shared schemas, generated clients, and migration numbering for the designated integration worker. Schedule cross-cutting changes explicitly.

Workers read their assigned plan sections and relevant shared contracts, not just a coordinator's paraphrase. A change to a shared interface becomes a versioned contract proposal; integration accepts it and informs consumers before dependent work proceeds. On a worker failure, preserve its changes, record the failure, and resume or reassign the task with explicit ownership. Stop dependent tasks rather than filling the gap with invented results.

Every ledger entry should contain:

```yaml
id: P5-HISTORY-01
requirement_ids: [LEG-05, LEG-13, LEG-14, LEG-16]
canonical_docs: [docs/spec/01-estimands-and-contracts.md, docs/spec/06-service-and-ui.md]
estimand_version: <applicable or not-applicable>
dgp_scenarios: [<versions and IDs>]
truth_contract: <method, information set, numerical uncertainty>
source_ids: [<supporting evidence IDs>]
failure_policy: <declared failure and abstention behavior>
owner_role: service
owner_thread: <observed subagent thread ID>
agent_model: gpt-6.1-sol
reasoning_effort: high
effort_escalation_reason: null # required when implementation increases to xhigh
helper_requests: [] # task, inputs, expected summary, dependency, queued/running/done
depends_on: [P0-CONTRACTS, P1-REPLAY]
base_commit: <observed commit>
write_paths: [<assigned paths>]
inputs: [<versioned contracts and fixture IDs>]
outputs: [<implementation, tests, documentation>]
acceptance: [<observable checks and commands>]
reviewer_role: invariant-review
reviewer_thread: <separate subagent thread ID when assigned>
reviewer_model: gpt-6-astra
reviewer_reasoning_effort: medium
status: queued # running | needs_review | failed | blocked | complete
evidence: [<result manifests and artifact paths>]
blocker: null
```

### Worker assignment prompt

```text
You own task <ID>: <concrete behavior>.
Assigned model/effort: <model>/<effort> from the entry point's model policy.
Report unavailable settings; do not silently substitute. For difficult Sol
implementation, increase high to xhigh if supported and record the reason.
Only the orchestrator assigns tasks or spawns agents. Request Luna help from
it with the bounded question, inputs, expected summary, and whether you can
continue independent work. Helpers share the global two-subagent limit.
Send user questions and decisions to the orchestrator; do not solicit feedback
directly or manage the master plan. Return a checkpoint if asked to free a slot.
Apply the playbook's Codex guide rules: act promptly, batch independent reads,
use native tools and patching, reuse code, preserve type safety and unrelated
edits, surface failures, and finish through verification. Set shell workdir.
Read plan.md sections <sections>, implementation-prompt.md, applicable
AGENTS.md, and contracts <paths/versions>. Base commit: <commit>.
Dependencies already accepted: <IDs and evidence>. Write only <paths>.
Coordinate shared-interface changes with the orchestrator before editing them.

Implement <specific outputs>. Cover <normal flow>, <failure flow>, and
<invariants>. Use actual computation where required; label fixtures and cached
results with their generation provenance. Do not change plan scope or claim
stakeholder approval. Inspect existing code and tests before adding abstractions.

Run <task-specific checks>. For visible UI changes, request an orchestrator-routed
Playwright MCP handoff using <case IDs>, <URL>, and <expected behavior>.
You are not done until required verification and independent review are accepted.

Return: task ID; actual agent model/effort and escalation reason; helper requests
and results; changed files/commit or patch; contract versions; exact checks
and outcomes; seed/data/model versions; evidence paths; limitations; blockers;
and integration instructions. Distinguish observed results from expectations.
```

### Review prompt

```text
Use gpt-6-astra at medium in a thread separate from the implementing worker.
Review task <ID> independently against plan.md sections <sections>, contract
<version>, and accepted base <commit>. Inspect the diff and verification evidence.
Check causal/temporal leakage, state transitions, invalid actions, fabricated
outputs, and relevant failure paths. Reproduce targeted checks where needed.
Return findings ordered by severity with file references and reproduction steps.
Include actual model/effort, acceptance checks and outcomes, evidence paths,
blockers, and any Luna helper requests routed through the orchestrator.
For technical plans, critique dependencies, feasibility, and acceptance criteria
before implementation. Do not edit the implementation or approve your own work.
Route findings and user questions to the orchestrator for assignment or feedback.
If no findings, state the reviewed scope and remaining evidence gaps. You cannot
approve an unexecuted acceptance check on the basis of an implementer's assertion.
```


## Phase map, dependencies, and acceptance evidence

Use `plan.md` section 15 as the phase sequence. The suggested package names below organize the work; derive finer tasks from every requirement in sections 1–18. In particular, enumerate all section 6 scenarios, all section 12 assignment states, all section 16 invariants, and all section 17 demonstration cases in the requirement map.

| Phase and delegated packages | Dependencies and reviewable output | Gate evidence |
| --- | --- | --- |
| **0: workflow, estimands, contracts, UX prototype** | Read the plan index and G0 bundle; define clinical and learning states separately, permissions, intercurrent-event strategies, per-component consent, eligibility/holds, configurable thresholds, evidence registry, and source-to-design map | Versioned data dictionary and estimand contracts; sketch both dashboards and each assignment stage; distinguish provisional engineering assumptions from actual clinician/human-factors review |
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
