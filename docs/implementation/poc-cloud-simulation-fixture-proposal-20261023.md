# Bounded Linux simulation fixture qualification proposal

Status: repaired source proposal, **UNEXECUTED**; requires refreshed independent Astra review of the exact candidate and root's matching authorization. This local CS-T1 check for the [cloud runbook](poc-cloud-simulation-runbook-20261023.md) is not CS3 deployment or a new planning gate. No cloud resource, publishing, credential read, existing database/volume, accepted native bundle, archive or training action is included. One attempt only; actual failures return to the existing repair/review queue.

The concrete operator is [run_cloud_fixture.py](../../tooling/foundation/run_cloud_fixture.py). It reuses accepted [analysis_lifecycle.py](../../tooling/foundation/analysis_lifecycle.py) literal-CID watchdogs, typed states, independent terminal receipt comparison, capped commands, stop/kill and child reaping. It does not discover, retry or remove resources. Both stopped containers and the exact internal network remain for root's accepted inspection, including on failure.

## Images and actual source qualification

Immutable local IDs, **built, not runtime-qualified**:

- App `sha256:a950cdb0dd9b3bbdeb176c6da71903180406a9bf2160ea3d23faf4be3c0f5e72`: component `9b3a61b0f02f881fe3a8fe7e60c11015074b3e9a`, source `4a903a01a7aa90938bb2b69c0911dafaff4cce7c` (app/UI unchanged through CS0 base `de4a0c5d8a8146a02101617c0fcf8f655aba6474`). Actual build manifest Git blob `095937fc083ecffd5040b484d88d56718a25e5f4`, source manifest `25049bace2c7fbcef442705f51b3f91a39909983`, Dockerfile `2cfe56acb6472ea16489ae137e2ff492743ab529`.
- Generator `sha256:d64907d76a2810d2e6cad8acaa012f3df132ced69bfe2636c7eb07f7090b4eee`: build candidate `6168302a2db95a3d8ee9f4b8ce17c678bef9b575`, canonical source `de4a0c5d8a8146a02101617c0fcf8f655aba6474`, 28 COPY files plus Dockerfile, 299375 canonical context bytes. Actual build manifest `475bd91f7703195db00097b5dc916daf61cb59e0`, raw SHA256 `9285b0e3aab9d87a73b3f66475642364103f814cf781f1271229d7ff3d1d62bd`. Successful build and reaped host process establish build completion only.
- Foundation runtime parent `sha256:ce346feace2ae607ebd574e1bb681d594c9b676c06b56f8ba8d50b858a577faa`. No historical generator, mutable tag, rebuild, pull, dependency fetch or UI rebuild is included.

[image-closures.json](evidence/cloud-simulation-prep-20261023/image-closures.json) maps actual `/app` destinations to preknown copied-source SHA256 values: 74 app files and 28 generator files, derived from those source manifests and Dockerfile COPY instructions. Preparation checked every expected source hash against its referenced Git blob. Each role binds its source commit and raw actual-build-manifest SHA256. This is expected source association, not a claim about uninspected image contents.

Before work inside each container, the exact frozen `python -B -c` qualifier hashes the actual complete `/app` regular-file set, excluding bytecode caches, and compares the copied-source set and every hash to that closure. It rejects application symlinks/unexpected sources, verifies Linux amd64 and actual UID/GID, and imports the real role module. Both roles reject learner/evaluator/methods/dispatcher source; the app also rejects generator/DGP source; generator rejects app source. Neither role import may load NumPy/SciPy/PyMC/PyTensor/statsmodels. Generator then execs its existing server; app runs the isolated fixture. No `/app` source overlay can satisfy the hashes.

Generated `/app/web/dist` has no previously independently known hash. The app qualifier requires `index.html` and a JavaScript asset and captures its complete actual destination-to-SHA256 inventory in sanitized stdout, labeled **first observed inventory, not a prior independent asset-hash match**. Immutable image/build provenance and the pinned Node/package-lock build bind these assets. Generator must have no frontend assets. Review this distinction rather than inventing expected asset hashes.

## Freeze, root authorization and one launch

From the committed reviewed checkout, freeze exact physical paths/bytes into a fresh ignored directory. This uses host stdlib and Git only, with no Docker access:

```powershell
python -P -B tooling/foundation/run_cloud_fixture.py --freeze docs/implementation/evidence/cloud-simulation-prep-20261023/image-closures.json --prefix remission-cloud-fixture-8d7d04c17b65 --output artifacts/cloud-simulation-fixture-20261023
```

The plan records full candidate SHA; physical hashes of every cloud asset, fixture, operator and lifecycle helper; absolute mount sources; expected closures; literal create argv; unique prefix; parent/images; and budgets. Root must retain/read `plan.json` and its printed raw SHA256. A replacement prefix/path before any attempt needs a new concrete freeze and authorization of that hash. Do not silently change an authorized plan.

Root supplies `authorization.json` separately, matching **exactly** this schema with the actual raw plan SHA256 replacing the descriptive value. This document does not provide authorization:

```json
{"authorized":true,"scope":"one-local-CS-T1-fixture","plan_sha256":"<actual raw plan.json SHA256>","attempts":1,"retain_resources":true,"cloud":false,"training":false}
```

After refreshed Astra acceptance and root authorization, launch:

```powershell
python -P -B tooling/foundation/run_cloud_fixture.py --launch artifacts/cloud-simulation-fixture-20261023/plan.json --authorization artifacts/cloud-simulation-fixture-20261023/authorization.json
```

`--launch` implements the external watcher: capture literal child PID/argv, wait at most 400 seconds, kill/reap a timed-out operator with a two-second reap cap, and retain its terminal receipt. Operator parent budget is 300 seconds. Generator's absolute watchdog deadline is operator start +240 seconds. Fixture receives at most 180 seconds, additionally capped at start +225 seconds. Cleanup reserves 60 seconds: exact-CID stop/kill/inspect commands have existing independent short caps and supervisor clients have bounded reaping. No unbounded wait, child or retry is introduced. Parent death leaves each started workload with its already armed independent deadline watchdog. External timeout means **STOP UNCONFIRMED**, never pass inferred from a killed Docker client.

## Create, inspect, prearm, start, stop and retain

Only two task containers: generator UID/GID20000 and fixture UID/GID10001. Each uses `--cpus 2 --memory 2g --memory-swap 2g --pids-limit 256 --read-only --cap-drop ALL --security-opt no-new-privileges --tmpfs /tmp:rw,noexec,nosuid,size=256m`. One new labeled `--internal` network, generator alias `generator`, no published ports. Generator has no mounts. Fixture mounts exactly the frozen cloud directory at `/deployment:ro` and fixture file at `/qualification/linux_simulation_fixture.py:ro`. SQLite/bootstrap/generated state exist only in private fixture `/tmp`. No existing listener, database, account, store, native mount or archive is inspected.

1. Reject missing/mismatched root authorization or changed candidate/physical bytes before Docker. Exclusively reserve `attempt/`; no second attempt can overwrite it.
2. `docker image inspect --format <IMAGE_FORMAT> <literal-ID>` selects only ID/OS/architecture/user **inside Docker, before stdout**, for parent and both images. Assert exact IDs/platform and role users.
3. Create the task network, bind its exact 64-hex ID, inspect only ID/name/internal/labels. `docker create` both workloads using frozen argv; accept only exact returned 64-hex CIDs, retained immediately.
4. `docker inspect --format <CONTAINER_FORMAT> <literal-CID>` on each **created** container selects identity/user/task-label/command, typed state/restart count, memory/swap/CPU/PID/read-only/privilege/capability/no-new-privileges/tmpfs, auto-removal/publication/restart policy, mounts/network. Verify the complete tuple before either starts, including equal 2147483648-byte memory/swap and exact internal network ID. Normalize Docker Desktop drive-path forms only for comparison with the same frozen Windows mount source. Full inspect and `Config.Env` are never emitted or logged. Both exact format strings and create argv are in the operator/plan.
5. Spawn generator's accepted watchdog against its literal CID **while created**. Require exact CID/nonce/deadline/PID ready receipt and live watchdog, then spawn `docker start --attach <CID>`. No detached `docker run` remains.
6. Use accepted `life.supervise` for the created fixture: prearm its own exact-CID watchdog before attached start. During polling, fail if either generator client completes before intentional stop. Fixture readiness uses bounded TCP, not arbitrary sleep.
7. Fixture completion in either attach/watchdog order requires both statuses, typed terminal `exited`/PID0/non-OOM/exit0, fresh independent state equal to its CID/nonce/deadline watchdog receipt, and reaping. Then inspect generator still running, retain **intentional-stop** receipt, stop exactly its CID, wait boundedly for both clients in either order, and compare typed terminal state to its watchdog receipt. Service exit143/137 after intentional signal is distinct from successful natural one-shot completion. OOM/dead/watchdog/client inconsistency fail.
8. On success/failure, freshly prove PID0/stopped for each exact CID, attempt bounded stop/kill where needed, reap clients, and recheck frozen physical bytes. Preserve commands/selected states, watchdog/attach streams, source qualification, intentional-stop/terminal/result receipts. Missing bounded-stop or reaping proof means **STOP UNCONFIRMED**. Retain terminal containers/network. Root owns later accepted exact-ID cleanup; no broad cleanup or automatic retry exists.

Moby can leave endpoint `NetworkID` empty while a container is created: it initializes configuration at create and allocates endpoints on start ([primary implementation](https://raw.githubusercontent.com/moby/moby/v27.1.1/daemon/container_operations.go), `updateContainerNetworkSettings`/`allocateNetwork`). Prestart qualification therefore verifies the configured network name, rejects any foreign populated ID, and freshly resolves that exact unique name back to the audited internal network ID before either start. After fixture completion, selected attachment inspections require both allocated IDs to equal that owned ID. It does not fabricate a prestart allocated endpoint.

No Docker logs or secret environment values are collected. The fixture generates two random in-memory synthetic passwords without printing them. Assertions and source/asset hashes do not expose passwords, cookies, tokens or database contents.

## Behavioral coverage and limits

The existing [linux_simulation_fixture.py](../../tests/deployment/linux_simulation_fixture.py) uses real FastAPI middleware, Argon2, Linux SQLite and actual HTTP to the separate generator. Through existing initialization/account seams it exercises no-archive initialization, wrong/unknown login, anonymous denial, cookie flags, origin/CSRF rejection, default12 generation, cross-account read/mutation denial, explicit rationale/choice, actual day14 advancement/outcomes/history, stale rejection, empty analysis results, app recreation on the same files, logout/reset revocation and controlled-clock expiry. No fitter runs. Existing generator bounds/replay/causal-path and failed-generation rollback evidence keeps its original scope; this fixture does not claim a broad new campaign.

Host doubles cover missing/foreign prearm receipts, both service completion orders, early generator exit/OOM, swap/privilege/mount/network/argv drift, authorization rejection before children, retained failure/no retry, and STOP UNCONFIRMED on unavailable daemon proof. They cannot establish actual image/runtime behavior. No host numerical imports or Windows flock shim are permitted.

TestClient/ephemeral storage cannot establish Uvicorn/proxy ingress, trusted public TLS, Compose/systemd, Persistent Disk/VM reboot, cross-identity recovery or browser rendering. CS3/CS-T3–T7 and Caddy/registry qualification remain unexecuted. Maxima total 4GiB plus proxy/host, not measured fit for a 2GiB VM; measure actual working set and disk footprint in later authorized work. Canonical training remains deferred until after the first physician simulation milestone.
