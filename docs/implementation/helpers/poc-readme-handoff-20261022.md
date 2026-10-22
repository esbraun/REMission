# README handoff — 2026-10-22

Added the root [README](../../../README.md) as an engineer and physician-super-user entry point. It describes the supported synthetic patient workflow and single-patient V0 analysis, distinguishes research UI from qualified methods, links to canonical runtime/specification/runbook sources, and states synthetic-data and clinical-use boundaries. It does not claim support for general cohorts, qualified borrowing, N-of-1 analysis, MRT/WCLS, adaptive support, the bounded validation study, or clinical validation.

## Sources checked

- [`implementation-prompt.md`](../../../implementation-prompt.md) and the [functioning synthetic PoC amendment](../../spec/poc-amendment-20261021.md) for active scope and limitations.
- [Foundation runtime guide](../../../services/foundation/README.md) and [runtime/workflow guidance](../../execution/runtime-and-workflow.md) for prerequisites and launch procedure.
- [Restricted V0 analysis runbook](../poc-analysis-runbook.md) and [analysis verification/evidence](../poc-analysis-verification-20261021.md) for the single-patient cutoff-bound fit/refit behavior and evidence limits.
- [P1 protocol handoff](../poc-protocol-p1-handoff-20261022.md) and [`Nof1Panel.tsx`](../../../web/src/Nof1Panel.tsx) for the distinction between protocol UI and unavailable N0/N1 analysis.
- [`web/package.json`](../../../web/package.json) for the web-only npm scripts.

## Checks and scope

- Verified this checkout is at accepted base `2c100bcdc45c96c9f973d702ef4ea895571d1bb7`, on `docs/poc-readme-20261022`, and clean before editing.
- Confirmed the referenced tracked files and runtime entry points exist; the npm script names match `web/package.json`.
- Reviewed the README links and commands for consistency with the checked docs and tracked scripts.
- No app code, runtime, dependency, or infrastructure files changed. No builds, tests, containers, or fits were run for this documentation-only change.

The runtime guide remains the source of truth for the full supported local launch procedure. This README intentionally links to it instead of presenting a partial command sequence as a complete application launch.
