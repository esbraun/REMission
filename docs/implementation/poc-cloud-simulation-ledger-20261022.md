# Cloud physician simulation task and test ledger

Revision: 2026-10-22. Canonical requirements: [immediate PoC milestone](../spec/poc-amendment-20261021.md#immediate-physician-simulation-milestone-2026-10-22). Status: plan candidate; independent critique pending. No cloud resources, deployment, browser verification or fitting was performed for this amendment. Historical local POC-1–3 evidence is retained with its original scope.

## Deployment decision and limits

Use one Compute Engine VM, one service container running the existing FastAPI/React app, its existing private synthetic generator container on the same VM, and a separate retained Persistent Disk mounted at the existing SQLite data directory. Keep a single app instance; bind SQLite, WAL/SHM and all required persisted app artifacts to the durable directory. An HTTPS reverse proxy terminates a trusted certificate for the selected origin; expose the app only through that proxy, configure the existing HTTPS origin/cookie/CSRF settings and restrict administration access. Use a pinned container image and startup script or cloud-init with restart policy; mount the identified disk before starting the app, and fail startup rather than silently create an empty store when the mount is absent. Never format or reseed an existing disk on reboot. Retain the disk on VM deletion and document backup/restore and explicit teardown handling.

This is a bounded engineering choice to preserve SQLite, not a claim that Google mandates this topology or that it is highly available. A single VM entails downtime during restart and operator maintenance. Choose machine/disk sizing and recurring-cost limit only after the project/region/budget inputs are known. No Cloud SQL migration, Kubernetes, Terraform, OAuth, new framework or model worker is needed for this milestone. Cloud Run's disposable instance filesystem is not a durable SQLite store; do not silently substitute horizontal instances or a bucket-mounted database.

Official primary sources checked 2026-10-22:

- [Google Compute Engine container startup agent migration](https://docs.cloud.google.com/compute/docs/containers/prepare-for-container-agent-shutdown), updated 2026-10-20: the deprecated container-declaration path must be replaced; startup scripts/cloud-init support continuing a single-VM container workload. This plan uses those supported mechanisms, not `gce-container-declaration` or `create-with-container`.
- [Google Persistent Disk](https://docs.cloud.google.com/compute/docs/disks/persistent-disks): persistent block storage is the basis for the attached database disk; exact disk type/size and retention configuration are implementation inputs.
- [Google Cloud Run container contract](https://docs.cloud.google.com/run/docs/container-contract#file_system_access): instance filesystem writes do not persist when the instance stops. This rules out an unchanged SQLite deployment to that filesystem.

## Existing seams and concrete work

Here, service-only means the interactive app plus its required synthetic generator and HTTPS proxy, excluding analytics workers; generation is simulation, not model training.

Source baseline: `4a903a01a7aa90938bb2b69c0911dafaff4cce7c`. `services/foundation/server.py` creates the app without starting a learner. `app.py` already owns session/login/logout, Secure cookies for HTTPS, origin/CSRF checks and account authorization; `configuration.py`, `cli.py` and `store.py` provide settings, explicit synthetic account provisioning and persistent state. `services/foundation/simulation.py:product` requires `REMISSION_GENERATOR_URL` and calls the private generator for panel generation/advancement. Preserve that isolated generator and its image identity; expose no generator port publicly. Provision the required immutable control bundle and runtime settings through existing preparation contracts. Reuse these contracts. `tooling/foundation/build_live.py` currently builds all roles and `live_stack.py` requires a learner image even without analysis dispatch. Adapt or add a minimal service-only option without breaking the existing scientific workflow. This source observation is not deployed validation.

| Task / owner role | Dependencies | Output and acceptance IDs | Initial status |
|---|---|---|---|
| CS0 Plan / Astra medium | Accepted baseline and latest user scope | This canonical amendment, source-backed deployment choice, requirement/test mapping; separate Astra exact-candidate critique before implementation | Needs review |
| CS1 Service packaging / Sol high | CS0 accepted | Pinned app-plus-generator build/start and documented settings; preserve synthetic panel/decision/advance/history without learner/evaluator images or jobs; CS-T1 | Queued |
| CS2 Cloud runbook / Sol high | CS0 accepted; CS1 image contract | Parameterized commands/config for VM, disk, proxy HTTPS, account provisioning, restart, rollback and cleanup; no embedded secrets or invented project; affected source checks and CS-T2 | Queued |
| CS3 Deploy and exercise / Sol high | Reviewed CS1/CS2; resolved cloud inputs and authorization | Actual exact-revision/image deployment, health plus deployed browser/API evidence CS-T3–T7 | Blocked on cloud inputs; not executed |
| CS4 Independent release review / separate Astra medium, reproduction by Sol high | CS3 evidence and exact candidate | Reproduce affected checks, inspect deployed evidence, resolve findings, record reviewed head/base and disposition; CS-T8 | Queued |

The orchestrator assigns exact worker/reviewer thread, isolated worktree/branch/base and candidate IDs when each task starts, under the existing delegation contract. Plan owner: `/root/cloud_simulation_plan_astra`, Astra/medium, `C:/Users/erics/Documents/Projects/REMission-worktrees/cloud-simulation-plan-a-261023`, branch `docs/poc-cloud-simulation-plan-20261023`, base above. Reviewer, reviewed head/base, PR and merge are pending; no independent acceptance is asserted. Do not create another planning gate after CS0: proceed with the bounded packages and ordinary exact-candidate reviews. Changes to scope or storage contracts require only affected review.

## Requirement to test and evidence map

All checks are **not executed for Google Cloud**. Use existing meaningful foundation/generator integration tests and official browser workflow; add only coverage for changed seams. Each evidence record identifies UTC time, source SHA, immutable image digest, configuration fingerprint without secret values, target project/zone/VM, HTTPS origin, action/command, exit/status and result. Bind tests to the deployed image rather than just the local checkout.

| Check | Requirements | Evidence required |
|---|---|---|
| CS-T1 Service-only qualification | POC-1/2/3, POC-CLOUD-03/05 | Clean app-plus-generator build/start without analytics images/jobs; seeded generation, explicit rationale/choice, advance/read/history and unavailable analysis behavior. Existing enabled invariants and meaningful auth/generator integration checks pass. |
| CS-T2 Deployment preparation | POC-CLOUD-01/04/05 | Reviewed pinned deployment/runbook; disk mount/retention and startup failure behavior; HTTPS/cookie/origin settings; no default public fixture passwords; documented rollback/backup/cleanup. Actual cloud execution remains pending CS3. |
| CS-T3 HTTPS/authentication | POC-CLOUD-01/02 | Actual GCP resource and image identity; trusted HTTPS browser/health; correct login; wrong password and unknown account rejected; anonymous protected read/write denied. Verify session cookie attributes and origin/CSRF rejection over ingress. Redact tokens/passwords. |
| CS-T4 Session lifecycle | POC-CLOUD-02 | Logout, old-session protected denial, fresh login; expiry and password-reset revocation checked against the deployed service with isolated synthetic accounts. Record any bounded test TTL configuration and restore the intended configuration; never weaken production checks to get a pass. |
| CS-T5 Owned physician workflow | POC-1/2/3, POC-CLOUD-03 | Two accounts cannot list/read/mutate each other's patients. Browser generates default12 seeded panel and exercises selection, eligible explicit plan/rationale/confirmation, advancement, outcomes/history, stale/ineligible rejection and no-result states. Retain bounded 2–24, replay/different-seed and causal-path checks from POC-1–3 in affected integration coverage. |
| CS-T6 Durable state | POC-CLOUD-04 | Before/after saved-record comparison for reload, service container recreation and VM reboot using the same retained disk; health and re-login; no reseed; history unchanged and next advancement works. Record disk/mount identity, not database secrets. |
| CS-T7 Active-loop browser quality | Workflow portions of POC-6, POC-CLOUD-05 | Keyboard operation, readable chart/table alternatives, errors/no results, console/network failures, desktop/narrow render inspection under existing browser guidance. |
| CS-T8 Reviewed handoff | POC-CLOUD-05, RELEASE-01 | Reproducible clean-checkout instructions, exact head/base independent disposition, affected checks, CS-T3–T7 artifacts, unresolved limits, separate simulation/analytics/human statuses, PR and resulting merge identity. |

## Inputs before actual cloud execution

Unknown: intended Google Cloud project and billing authorization, permitted region/zone, resource budget/size/lifetime, operator IAM/deployment access, artifact registry location, domain/DNS and certificate setup or an available trusted HTTPS endpoint, and secure provisioning/delivery of two synthetic physician credentials. Consult connected context before requesting missing factual inputs; do not invent them. Provisioning billable resources and publishing the endpoint require those resolved inputs and applicable authorization. Documentation and service preparation can proceed meanwhile. Deployment tooling availability must be verified; an absent Google Cloud CLI is setup work, not a reason to change the acceptance goal.

Use least necessary deployment/runtime permissions and the existing account-hash/reset contracts. Supply secret values through an approved secure channel at execution time; keep them out of source, shell history, image layers and evidence. Do not reuse public local fixture passwords on the exposed service. Document resource IDs, estimated recurring cost, rollback to the preceding image with schema compatibility checked, and how to stop/delete resources while retaining or explicitly deleting synthetic data as intended.

## Deferred analytics ledger boundary

Existing analysis, borrowing, protocol, cohort and truth-ablation ledgers retain all statuses and evidence. POC-4/5, fitted POC-6 representatives, APPT-01–05 and POC-VAL (V0/V1, N0/N1, S0/S1/S2, accuracy/freshness/latency and confirmation) are later analytics acceptance. No fitting, training, saved-model qualification or scientific study is on CS1–CS4's dependency path. No completed cloud/auth/analytics/human/clinical claim follows from accepting this plan.
