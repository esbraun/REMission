# REMission

REMission is a synthetic research prototype for exploring longitudinal insomnia-care decisions and clinical analytics. It connects a fictional patient workflow to an observed-data analysis while keeping clinical decisions explicit and preserving what was known at each decision cutoff. It is intended only for synthetic research and demonstration, not patient care.

All patients, reports, plans, effects, and medication identifiers in the runnable demonstration are synthetic. MED_A and MED_B are fictional identifiers. Do not enter real patient information, connect an EMR or wearable account, or reuse demo credentials outside the local fixture environment. The prototype has not established clinical safety, efficacy, or suitability for patient care.

## Current state

The current implementation supports generating a seeded panel of 2–24 fictional patients (default 12), selecting a patient, reviewing eligible plans, making an explicit decision, advancing simulated time, and inspecting persisted observations and history. Accepted evidence verifies one synthetic single-patient day-14 visit-analysis fit using native PyMC/NUTS with the restricted borrowing V1 configuration and two external study summaries. Its reported interval crosses zero. This evidence covers that one input, configuration, and persisted result; it does not establish broader statistical or clinical validity or a V0 runtime fit. The code has a refit path for later observations, but end-to-end day-42 refit verification remains pending. Results include the cutoff, forecast horizon, uncertainty, and diagnostic/status information; a failed, pending, or inconclusive attempt is not an accepted estimate.

The N-of-1 protocol interface supports an explicitly consented fictional protocol workflow, but N0/N1 analysis is unavailable pending accepted methods. General multi-patient/cohort inference, borrowing qualification across scenarios, MRT/WCLS, adaptive support selection, and the bounded accuracy/timeliness ablation study are not complete. Some research controls and source views exist; their presence does not mean those methods or studies have passed qualification. Clinician review, human-factors evaluation, and clinical validation remain future work.

## Local use

The immediate milestone is the physician simulation on Google Cloud with tested username/password login. The [cloud simulation runbook](docs/implementation/poc-cloud-simulation-runbook-20261023.md) prepares one VM with the existing app, required private generator, trusted HTTPS and retained SQLite storage. `build_live.py --simulation-only` builds only app and generator; training/fitting and learner/evaluator workers are later analytics work. Cloud execution and deployed authentication/persistence verification remain pending in the [cloud ledger](docs/implementation/poc-cloud-simulation-ledger-20261022.md).

The supported application stack uses Docker with Linux containers and host Python. The runtime also checks a pinned service image; native Windows SQLite is not supported for that stack. Follow the [foundation runtime guide](services/foundation/README.md) for the complete build, qualification, and launch procedure. Its main build entry point is:

```powershell
$evidence = 'docs/implementation/evidence/local-live-' + [guid]::NewGuid().ToString('N')
python tooling/foundation/build_live.py --evidence "$evidence/build"
```

The pinned service-runtime and historical-runtime images are pre-existing prerequisites: the build validates the service image and the launcher inspects the historical image; this build command does not bootstrap them on a fresh machine. Choose a fresh evidence directory and an unused local port, then use an isolated demo stack with a fresh synthetic database. To enable generated panels, pass the built generator image with `--generator-image $images.images.generator` to `live_stack.py`. Its former `--analysis-dispatcher` option is retired and rejects before provisioning. Background analysis preparation now follows the [ordinary source procedure](docs/implementation/poc-cohort-ordinary-prep-20261022.md), whose independent source review, service image/Linux qualification, concrete runtime bindings and authorization gates remain pending. Its unbound templates are not runnable launch instructions. The [analysis runbook](docs/implementation/poc-analysis-runbook.md) retains the earlier verification context.

For web-only development checks, the scripts below are declared in [`web/package.json`](web/package.json). They typecheck, test, and build the React/Vite client; they do not start the API or the complete application.

```powershell
Set-Location web
npm ci
npm run typecheck
npm test
npm run build
```

## Architecture and workflow

The browser UI talks to the FastAPI service, which owns account-scoped state and persistence in SQLite. A restricted synthetic generator creates fictional trajectories. The analysis path exports a reduced, cutoff-bound observation history to an isolated learner; evaluator-only truth and generator internals are kept outside that learner input. Typed contracts and run artifacts record identities, configuration, and outcomes.

```mermaid
flowchart LR
  UI[React and Vite UI] --> API[FastAPI service]
  API <--> DB[(SQLite state and history)]
  GEN[Restricted synthetic generator] --> API
  API -->|reduced observations at cutoff| L[Isolated learner]
  L -->|result and diagnostics| API
  E[Evaluator-only truth]
```

The evaluator's private truth remains outside learner inputs.

The usual synthetic walkthrough is: generate a panel with a recorded seed and count; select a patient; review eligibility and explicitly approve a plan; advance one day or to the next 14-day visit; inspect reports and scheduled ISI; then review the protocol/history and, where available, submit or inspect an analysis. The generator currently advances within its 84-day fictional horizon. A newer observation cutoff creates a new analysis attempt; earlier results keep their original cutoff and are marked stale against current data.

For clinical analytics, distinguish clinical state (eligibility, consent, holds, and approved plan) from learning state (protocol phase, assignments, delivery, adherence, and model status). An analysis uses only records available at its declared cutoff; observation gaps remain visible and are not silently treated as observations. Decisions and history are explicit and version-bound. A component-specific consent or oversight requirement, current eligibility, hold, and stale-state check must be satisfied before a randomized action can proceed. The model does not approve a plan or assign treatment by opening a page.

## Project guide

- [Implementation entry point](implementation-prompt.md) and [active PoC scope](docs/spec/poc-amendment-20261021.md)
- [Shared scope and invariants](docs/spec/00-scope-and-invariants.md)
- [Runtime and workflow](docs/execution/runtime-and-workflow.md)
- [POC analysis runbook](docs/implementation/poc-analysis-runbook.md) and [analysis evidence/limits](docs/implementation/poc-analysis-verification-20261021.md)
- [Validation protocol](docs/spec/07-validation-protocol.md) and [gate definitions](docs/spec/08-gates-and-release.md)

The specifications describe intended later capabilities as well as current constraints. Treat implementation and evidence status as authoritative; a requirement or UI placeholder is not proof that a method is implemented or validated.
