# Synthetic foundation

Run from the repository root with Docker Linux containers and host Python. The service runtime is Linux Python 3.13.7 with SQLite 3.54.1: `remission-foundation-runtime:candidate` must resolve to `sha256:ce346feace2ae607ebd574e1bb681d594c9b676c06b56f8ba8d50b858a577faa`. The build checks this identity before every image build. The numerical dependency image is insufficient for the service. Native Windows SQLite admission is unsupported.

Choose a fresh evidence directory and an unused localhost port. The following PowerShell example refuses a listener on the selected port; it does not stop or reset any existing stack. Replace the port if another task owns it. Ports 8765–8768 and existing task volumes must be preserved.

```powershell
$port = 8773
if (Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue) { throw 'Choose an unused port; preserve the existing listener.' }
$evidence = 'docs/implementation/evidence/local-live-' + [guid]::NewGuid().ToString('N')
python tooling/foundation/build_live.py --evidence "$evidence/build"
if ($LASTEXITCODE -ne 0) { throw 'Build failed; inspect captured stdout/stderr.' }
$images = Get-Content "$evidence/build/source-images.json" -Raw | ConvertFrom-Json
python tooling/foundation/live_checks.py --group domain --group runs --group service --group artifacts --group schemas --group runtime --evidence "$evidence/checks"
if ($LASTEXITCODE -ne 0) { throw 'Qualification failed; inspect captured stdout/stderr.' }
python tooling/foundation/live_roles.py --build "$evidence/build/source-images.json" --evidence "$evidence/roles"
if ($LASTEXITCODE -ne 0) { throw 'Copied-image role qualification failed.' }
python tooling/foundation/capture.py --evidence "$evidence/copied-tests" -- docker run --rm --network none --cpus 2 --memory 2g --read-only --cap-drop ALL --security-opt no-new-privileges --tmpfs /tmp:rw,noexec,nosuid,size=256m $images.images.tests
if ($LASTEXITCODE -ne 0) { throw 'Copied integration-test image failed.' }
python tooling/foundation/live_stack.py --port $port --service-image $images.images.service --learner-image $images.images.learner --evidence "$evidence/deployment"
if ($LASTEXITCODE -ne 0) { throw 'Deployment failed; retain its resources and inspect captures.' }
Get-Content "$evidence/deployment/deployment.json" -Raw
```

The old `build.py` and `run_stack.py` entrypoints are retired and refuse before Docker actions. `build_live.py` produces unique image tags and records exact image IDs, source bytes, lock hash and child exit status in `source-images.json`. Builds use no network. If pinned npm acquisition fails with the captured DNS/connection error, an explicitly authorized rerun may add `--allow-pinned-npm-network`; the exact existing lock must remain unchanged. Keep source stable between build, copied-image checks and launch.

`live_stack.py` creates uniquely named resources. It seeds an isolated historical ec18 database using its exact historical image, starts and drains that worker, disables its restart, then activates a separate private database volume with the explicit composed control bundle, archive authority and review rules. Only the offline provisioning process mounts source. The current service mounts its own database and read-only fixture volume; it never mounts the historical database. The launcher checks copied code bytes, current capability, old-worker route refusal and volume separation. It does not resume or upgrade an existing deployment. A failed invocation retains its own resources and captures for diagnosis; choose fresh evidence and resources for a new attempt.

Visit the URL recorded in `deployment.json`. Synthetic demonstration accounts: `alice` / `Synthetic-Alice-2026!`, `bob` / `Synthetic-Bob-2026!`. These are public fixture credentials and must not be reused elsewhere. The installed fixture bundle is only a structural synthetic demonstration. It is not a qualified scientific producer, accepted threshold clearance law, real patient data or clinician participation.

The service has real SQLite migrations, server sessions, ownership and CSRF. Ordinary care approval atomically persists bundle, immutable display, task and audit/idempotency receipt. History links reload saved displays; later outcomes are requested separately. All ten ASSIGN states are visible, with unavailable engines labeled and randomization denied. No patient is assigned a treatment by opening a page.

The administrative CLI supports explicit empty-database seeding, password reset/session revocation and validated observed-manifest replay:

```powershell
python -m services.foundation.cli --help
```

Use that CLI inside the qualified service runtime with its own database and configured `REMISSION_CONTROL_BUNDLE`, `REMISSION_ARCHIVE_CONFIG` and `REMISSION_RUNTIME_REF`. Normal startup/CLI operations cannot silently migrate an old database or fabricate current control. Offline cutover and stopped capable-003 upgrade are explicit administrative operations; neither is an instruction to reuse another task's database. Replay admits typed observed envelopes, tracks durable cursors/receipts and uses authoritative availability/correction cutoffs. The learner's strict observed export reader does not implement a model. Generator/calibration/truth/report engines belong to later packages and are unavailable here.

The build runs client typecheck/tests/build. `live_checks.py` captures domain, run, service, artifact/DR, exporter and runtime checks without overwriting historical outputs. `live_roles.py` checks copied source/probe bytes, actual service UID10001 and learner UID10002 private-file/list/import/write/network denials, evaluator UID20000 positive controls, and public fixture product consumption. The copied integration-test image runs independently of a source bind. Every command has UUID stdout/stderr and a command-start source manifest; a build alone is not runtime qualification. Browser acceptance additionally requires the actual official Playwright MCP tools on the exact deployed candidate. Current evidence, failures, source/image bindings and remaining limits are in `docs/implementation/evidence/G1-LIVE-HOLD/README.md`; the foundation verification report remains historical.
