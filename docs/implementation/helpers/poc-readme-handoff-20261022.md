# README handoff — 2026-10-22

Added the root [README](../../../readme.md) as an engineer and physician-super-user entry point. It describes the supported synthetic patient workflow and bounded single-patient visit analysis, distinguishes research UI from qualified methods, links to canonical runtime/specification/runbook sources, and states synthetic-data and clinical-use boundaries. It does not claim support for general cohorts, broad borrowing qualification, N-of-1 analysis, MRT/WCLS, adaptive support, the bounded validation study, or clinical validation.

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
- On the follow-up branch, verified the clean candidate base `f0c26ba4945ca14ed7d80db8b202ad782554e4c4` before the bounded label correction.
- No app code, runtime, dependency, or infrastructure files changed. No builds, tests, containers, or fits were run for this documentation-only change.

The runtime guide remains the source of truth for the full supported local launch procedure. This README intentionally links to it instead of presenting a partial command sequence as a complete application launch.

## Independent review repair

Independent Astra documentation review of candidate `89061ab346d885a29686f425690dad1b94ac146d` requested clarification that the base `live_stack.py` example does not enable the optional generator or analysis dispatcher (report object `61e0b00ced9654b87e3a1445bc683fb16e69b986`). This revision states the required `--generator-image $images.images.generator` option for generated panels, the additional `--analysis-dispatcher` option for asynchronous visit-analysis jobs, and links to the runbook's complete launch recipe. It also identifies the pinned service and historical runtime images as pre-existing prerequisites checked by the build/launcher, not bootstrapped by the README command.

## Analysis-label correction

Root review of the primary frozen independent acceptance report `4e5db97ec9a646317d1d665f1d0f99e0e9a47c29` corrected the prior V0 label. The report, titled “one native day14 borrowing fit,” accepts one synthetic single-patient day-14 fit using the restricted borrowing V1 configuration with two external study summaries and persisted ingestion. The README now describes only that bounded result; it does not claim a V0 runtime fit, day-42 refit, broader cohort/borrowing/scenario qualification, or clinical/statistical validity. The report explicitly leaves day-42 refit and broader acceptance open.
