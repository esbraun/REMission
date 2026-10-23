# Bounded Linux simulation fixture qualification proposal

Status: source proposal only, not executed or authorized by this document. This is the local CS-T1 preparation check for the [cloud runbook](poc-cloud-simulation-runbook-20261023.md), not CS3 deployment, an analytics study, or a new planning gate. After exact-candidate review, root binds the remaining image identities/source manifests and explicitly authorizes the runtime stage. No cloud resource, publishing, credential/account read, existing database/volume, accepted native bundle, archive or training action is included.

Inputs to freeze in the execution receipt: this candidate commit plus the physical byte hashes of `tooling/foundation/cloud/*` and `tests/deployment/linux_simulation_fixture.py`; service image `sha256:a950cdb0dd9b3bbdeb176c6da71903180406a9bf2160ea3d23faf4be3c0f5e72` and its accepted exact copied-source association; the new exact-current generator image ID and 29-file/Dockerfile build association (pending the separate generator worker); foundation runtime parent identity `sha256:ce346feace2ae607ebd574e1bb681d594c9b676c06b56f8ba8d50b858a577faa`; exact Linux platform and command environment. The historical generator image is excluded. Do not resolve mutable tags at runtime or fetch dependencies for this stage.

The approved operator supplies one unique task prefix `remission-cloud-fixture-<random>` and absolute source paths from the frozen candidate. Two Linux containers only: private generator UID20000 and fixture process UID10001, each capped at 2CPU/2GiB, 256 PIDs, read-only root, cap-drop ALL, no-new-privileges and a 256MiB noexec/nosuid `/tmp` tmpfs. One new internal Docker network; no host ports; no durable volume; no private or broad repository mount. Mount only the manifest-pinned cloud directory read-only at `/deployment` and the one fixture file read-only at `/qualification/linux_simulation_fixture.py`. The new SQLite database, bootstrap and generated state exist only under the fixture's private `/tmp`; the generator receives neither that database nor a source mount. No existing listener, service, database, account, private store, native mount or archive is inspected.

Proposed commands below are **not run**. `SERVICE_IMAGE` is the exact ID above; `GENERATOR_IMAGE` remains an unresolved required exact ID. `SOURCE_COMMIT` must identify the frozen reviewed source, and `CLOUD_SOURCE`/`FIXTURE_SOURCE` must resolve to the reviewed physical files. Root must bind these plus the unique prefix before authorization. The surrounding runtime harness captures child statuses/stdout/stderr and source/image/config hashes without environment values containing secrets. It must enforce a 180-second fixture timeout, retain failures, then clean up only the exact task-owned resources.

```bash
docker image inspect "$SERVICE_IMAGE" "$GENERATOR_IMAGE"
docker network create --internal "${PREFIX}-private"
docker run --detach --name "${PREFIX}-generator" --label "remission.task=$PREFIX" \
  --network "${PREFIX}-private" --network-alias generator --user 20000:20000 \
  --cpus 2 --memory 2g --pids-limit 256 --read-only --cap-drop ALL \
  --security-opt no-new-privileges --tmpfs /tmp:rw,noexec,nosuid,size=256m "$GENERATOR_IMAGE"
docker run --name "${PREFIX}-fixture" --label "remission.task=$PREFIX" \
  --network "${PREFIX}-private" --user 10001:10001 --cpus 2 --memory 2g --pids-limit 256 \
  --read-only --cap-drop ALL --security-opt no-new-privileges --tmpfs /tmp:rw,noexec,nosuid,size=256m \
  --mount "type=bind,source=$CLOUD_SOURCE,target=/deployment,readonly" \
  --mount "type=bind,source=$FIXTURE_SOURCE,target=/qualification/linux_simulation_fixture.py,readonly" \
  --env PYTHONPATH=/deployment:/app --env PYTHONDONTWRITEBYTECODE=1 \
  --env REMISSION_GENERATOR_URL=http://generator:8780 \
  --env "QUALIFICATION_SOURCE_COMMIT=$SOURCE_COMMIT" \
  --env "QUALIFICATION_SERVICE_IMAGE=$SERVICE_IMAGE" \
  --env "QUALIFICATION_GENERATOR_IMAGE=$GENERATOR_IMAGE" \
  "$SERVICE_IMAGE" python /qualification/linux_simulation_fixture.py
```

Before the fixture, inspect actual service/generator source hashes against their accepted build closures and assert service UID/source purity (no generator implementation or learner/evaluator code/mount). Readiness is a bounded TCP probe to generator:8780 from the new fixture network, with timeout and recorded failure rather than an arbitrary sleep. The test uses the real existing FastAPI authentication middleware, Argon2 and Linux SQLite, with actual HTTP to the separate private generator. It initializes a fresh no-archive bundle using the existing activation contract, generates two random in-memory synthetic passwords without printing them, creates two accounts through the new seam, and exercises wrong/unknown login, anonymous denial, cookie flags, origin/CSRF rejection, default12 generation, cross-account read/mutation denial, explicit rationale/choice, actual day14 advancement/outcomes/history, stale rejection, empty analysis results, app recreation on the same files, logout, reset and controlled-clock expiry. No fitter is imported or run. The test does not send passwords to stdout, and assertions avoid printing cookie/token values. Capture only success/failure and sanitized assertion output.

Afterward inspect container exit/OOM/resource/mount/network state, preserve the source-bound command receipt, remove only `${PREFIX}-fixture` and `${PREFIX}-generator`, then remove `${PREFIX}-private`. A retry requires diagnosing retained failure evidence; do not silently retry generation or expand the runtime. No host Python import of NumPy/SciPy/PyMC or Windows flock shim is allowed.

The existing `tests/generator/test_service.py`/`test_restricted.py` retain seed/bounds/replay/causal-path and failed-generation rollback coverage; affected inherited qualification may be run only within the same frozen Linux runtime proposal with its exact read-only test/source closure identified first. This source proposal does not authorize a broad test campaign. The minimal fixture above is not a substitute for those inherited checks or the deployed CS-T3–T7 browser/API/durable-disk/reboot checks.

Limits: the fixture uses TestClient for the app ingress and an ephemeral filesystem; it cannot validate Uvicorn/proxy ingress, public trusted TLS, actual Compose/systemd startup, Persistent Disk, VM reboot or cross-identity recovery. Those remain the parameterized cloud execution stage after project/budget/domain/access inputs are resolved. Actual Caddy image/registry references also remain unresolved.
