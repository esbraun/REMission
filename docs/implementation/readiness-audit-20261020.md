# READY-01 launch readiness audit

**Audit date:** 2026-10-20

**Status:** repaired candidate READY-FIX-01; original READY-REVIEW-01 returned changes_requested. Fresh exact-head/base Astra review pending. Historical launch observations below are dated; current orchestration is in [launch status](launch-status-20261020.md). This audit is repository and launch readiness only; it is not a clinical, statistical, or implementation acceptance.

## Repository and base

The original audit ran only in `C:/Users/erics/Documents/Projects/REMission-worktrees/readiness-audit-v2`, branch `launch/readiness-audit-v2-20261020`, initially at `50403963d11cc51e6109a635f9a2b6b1031b8cf4`. The checkout was clean before that report. The selected integration base is the local accepted documentation/workflow commit; the live remote `refs/heads/main` was observed by `git ls-remote` at `c7cdf4a8415073d0b275064a0b0aca188fc022fe`, while stale local tracking `origin/main` was `462f66eac2ce146c4166219b5cdf6a53f54c8b5e`. Remote main has not been reconciled as the launch base. Use the selected base until that reconciliation is explicitly accepted.

At the original audit checkpoint, the branch contained the specification, plans and evidence documents, with no application source, package manifest, lockfile, application tests or implementation ledger. This integrated repair now includes the planning ledger; it remains documentation only. The only main-checkout changes originally observed were unrelated untracked `.codex/`, `.dockerignore`, `.env.example`, `.gitignore`, and `infra/`; these were not copied, read for secrets, or included. The main checkout's existing `.env` was not opened.

The prior readiness worktree remains intact at `C:/Users/erics/Documents/Projects/REMission-worktrees/readiness-audit`, branch `launch/readiness-audit-20261020`, clean at `dbece0fbbed1e1ce736ded7877bc43cbad3ee9db` (`docs: require isolated subagent worktrees and reviewed merges`). That worktree is separate from agent-thread inventory. The two G0 worktrees provisioned by the orchestrator are also separate checkouts, not evidence of open threads: planner `C:/Users/erics/Documents/Projects/REMission-worktrees/g0-plan-20261020` on `launch/g0-plan-20261020` and critique `C:/Users/erics/Documents/Projects/REMission-worktrees/g0-critique-20261020` detached, both at the selected base.

## Runtime and dependency readiness

The host exposes Git 2.55.0, Node 22.20.0, Python 3.13.7, Docker client/server 29.8.0, npm/npx, and GitHub CLI. A Docker server responds. R/Rscript is not installed. In the system Python, NumPy, SciPy, and statsmodels are discoverable; FastAPI, PyMC, ArviZ, scikit-learn, DuckDB, and PyArrow are not. No project virtual environment or dependency lockfile is present, so these observations do not establish a supported application environment or package compatibility. No application package installation, database/service startup, browser automation, or project build was attempted.

The specification selects React/TypeScript with Python/FastAPI, local event/snapshot storage and DuckDB/Parquet analytics, PyMC with native NUTS, and compatible ArviZ. Offline RBesT/SBC/MRTAnalysis artifacts, StochTree, COBA and conditional nutpie are specified in the methods plans. These dependencies and the required Playwright MCP handoff remain to be provisioned and qualified later; their absence in the current system Python is not a failed implementation check. The original audit reported no exposed Playwright MCP tool; READY-REVIEW-01 corrected that claim. Tool discovery exposed `mcp__playwright__browser_*`, and `browser_tabs({action:"list"})` succeeded with one about:blank tab according to root/critic. This establishes responding tooling only; no application/UI workflow or persisted-service test was run. Required model assignments are documented, but the current collaboration controls do not expose an agent close/release operation or a model/effort change operation.

## Canonical G0 inputs and conflict status

The authoritative navigation and requirements are `plan.md`, `implementation-prompt.md`, `docs/spec/08-gates-and-release.md`, `docs/spec/00-scope-and-invariants.md`, `docs/spec/01-estimands-and-contracts.md`, and the cited `docs/spec/dgp-reference.md`, scenarios, and evidence records. `docs/spec/traceability/g0.md` maps legacy source units to canonical homes; the requirement map and revision history record migration dispositions. G0's gate row requires a temporal DAG/factorization, reviewed synthetic parameter table, outcome/decision contracts, citation limitations, and task mapping, with generator coefficients surfaced rather than hidden in code. G0 precedes G1 and detailed UI design. G0 qualifies library/runtime support and offline artifact contracts.

The traceability baseline records 483 original units, 477 preserved and six intentionally revised with dispositions in revision history. The canonical documents state that gates are unexecuted and G0 still requires review of equations, additional implementation parameters, and final estimand-specific analysis contracts. This bounded audit found no new unresolved canonical-source conflict; it did not resolve or certify every scientific requirement. The G0 planner should report any discovered conflict explicitly before contracts or code depend on it. The requirement-to-task-to-test ledger is not yet present.

## Historical delegation and lifecycle finding

At audit checkpoint, the orchestrator reports 0 open non-Luna workers and 1 spawned Luna helper (this audit), with total spawned-thread capacity 3. The planner and critique worktrees are reserved but unowned. Explicit requested model/effort were Luna/high for the original task; effective settings were not independently introspected; future planning and critique require Astra/medium, implementation requires Sol/high, and independent review requires a separate Astra. The exposed controls include spawn, message, follow-up, interrupt, list, and wait. They do not include close/release or changing an existing thread's model/effort. A completed or interrupted turn therefore cannot be counted as a released slot.

The Astra planning and separate Astra critique can be dispatched in sequence within the two non-Luna slots. Sol implementation then remains queued unless a supported lifecycle/reuse path frees a non-Luna slot while preserving the independent review requirement. Do not switch model by creating an untracked top-level task, use nested agents, count interrupted threads as released, or substitute solo technical work. Raise this exact lifecycle limitation to the orchestrator; it controls whether implementation can launch.

## Readiness and bounded queue (original launch checkpoint)

Repository/documentation readiness is sufficient to begin G0 planning on the selected base. Application implementation readiness is not established: no source, implementation ledger, qualified dependencies, executed statistical checks, or application validation exists.

1. **Astra/medium G0 plan:** use the reserved planner worktree; read the bounded G0 bundle; identify decisions/parameters that need contracts, task/test mappings, and conflicts; commit a bounded plan and ledger proposal.
2. **Independent Astra/medium critique:** pin a separate reviewer checkout to the exact planner candidate; return findings against that SHA. Resolve and re-review changes before accepting the G0 package.
3. **Sol/high G0 contracts and ledger:** queue until the orchestrator demonstrates an available Sol thread/worktree under the effective two-open-non-Luna and total-capacity rules. Record accepted requirements, task/test IDs, owners, dependencies, and evidence states.
4. **Runtime/package qualification:** later, provision a project environment and lockfile; verify platform compatibility, licenses and versions; establish Playwright MCP/browser coverage and clean-checkout reproduction before claiming implementation readiness.

Synthetic engineering/statistical validation, human-factors review, clinical review, and clinical validation are not started and remain outstanding. No outcomes, sample sizes, package qualifications, or clinical claims are inferred from this audit.

## Repair and current lifecycle update

READY-FIX-01 removes the trailing whitespace and distinguishes live remote from local tracking state. The historical lifecycle blocker above was subsequently resolved by root: a verified existing planner child was archived, then native live inventory confirmed actual removal before Sol/high was spawned. No direct model change occurred. See [runtime audit update](runtime-resume-audit-20261020.md#superseding-root-verified-resolution) for exact identities, rejected app-input attempt and operative lifecycle procedure. Both rejected original candidates remain changes_requested; this integrated repair awaits independent exact-head/base review. G0 contracts remain unexecuted. Human-factors/clinical review is deferred by the user and does not block independently reviewed synthetic engineering assumptions.
