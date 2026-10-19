# Verification And Handoff

Read [execution entry point](../../implementation-prompt.md) and your assigned gate bundle first. This document governs future application implementation, not the documentation migration.

## Statistical evidence contract

Use [VAL-01–03](../spec/07-validation-protocol.md) and [RELEASE-01](../spec/08-gates-and-release.md#release-01--separate-evidence-statuses). A smoke run never satisfies recovery or SBC. Record unsuccessful attempts and truth uncertainty. Keep development and confirmation seeds separate; changing an estimator or threshold after inspecting confirmation requires a new protocol/version and fresh runs.

Review [source records](../evidence/README.md) before claims are released. Metadata-only or legacy-unverified records cannot silently support a new quantitative claim. Separate synthetic-engineering acceptance from human-factors, clinical review and clinical validation.

## Verification, prompt evaluation, and handoff

Each task proposes checks that test its actual risk and acceptance contract. Do not require expensive MCMC for every CSS change, and do not treat UI screenshots as evidence of statistical calibration. Separate smoke plumbing, genuine saved-model demonstration, and repeated evaluation runs; the smoke preset is not evidence about borrowing performance.

Before marking a phase accepted, the orchestrator checks that all required tasks have owners, reviews, executed checks, versioned outputs, and no unacknowledged failures. Retain failures and abstention in the report. Model runs must record seeds, distinct observation IDs, priors/transport assumptions, data cutoff, fitting configuration, diagnostics, runtime, and output lineage. Evaluation summaries report Monte Carlo uncertainty and distinguish calibration under model-consistent simulations from robustness under misspecification.

Evaluate this prompt with a small representative suite before broad instruction changes: cold-start prior-only display; consent withdrawal; frozen support during a block/washout; a late upload excluded from an old snapshot; stale approval after a new hold; and sharp-null evaluation reporting. Measure completion against requirements, hard-constraint violations, unsupported claims, rework, latency, and reproducibility. Compare one targeted instruction change at a time across multiple runs; report observed tradeoffs instead of declaring a universally best prompt.

Before compaction, worker reassignment, or session end, persist the integration commit, plan revision, ledger status, contract versions, artifact manifests, failed checks, pending workers, unresolved decisions, and exact next tasks. On resume, verify repository state and dependencies, read those records, and continue unfinished IDs. Do not overwrite accepted historical evidence or forget an outstanding human-review gate.

The release/documentation subagent must reproduce the demo from a clean checkout using the documented commands and pinned versions. The final implementation PR should explain the runnable behavior, include the requirement/gate report and verification evidence, and identify genuinely blocked reviews or computations. Do not call phase 6 complete without the plan's required real usability evidence, or call the synthetic app clinically validated.

For documentation revisions, include all changed specification, execution and evidence files. Application code and generated validation results belong to subsequent implementation work. The plan index and its canonical linked specifications govern requirements.
