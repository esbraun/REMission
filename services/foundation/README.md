# Synthetic foundation

Run from the repository root with Docker Linux containers and Python 3.13. The accepted numerical dependency image `remission-python-locked:20261020` must have exact image ID `sha256:be4bbf7978bb318b8c3d2901e8e9510b746aa8554d5c0dbfc8eea5928d9f07f7`. Build tooling checks that identity before using it; it never overlays another checkout's source.

```powershell
python tooling/foundation/build.py
python tooling/foundation/run_stack.py --skip-build
```

The second command provisions exclusively named task resources and seeds an empty database. It refuses an existing database; use `--resume --skip-build` to replace the task's service container while preserving its database and private evaluator. It never deletes another task's resources. Source-free curated images run the API, observed-only learner reader and private evaluator canary. Visit http://127.0.0.1:8765. Synthetic demonstration accounts: `alice` / `Synthetic-Alice-2026!`, `bob` / `Synthetic-Bob-2026!`. These are public fixture credentials and must not be reused elsewhere. No real patient data or account integration is present.

The service has real SQLite migrations, server sessions, ownership and CSRF. Ordinary care approval atomically persists bundle, immutable display, task and audit/idempotency receipt. History links reload saved displays; later outcomes are requested separately. All ten ASSIGN states are visible, with unavailable engines labeled and randomization denied. No patient is assigned a treatment by opening a page.

The administrative CLI supports explicit empty-database seeding, password reset/session revocation and validated observed-manifest replay:

```powershell
python -m services.foundation.cli --help
```

Use that CLI inside the qualified service runtime with its database volume. Replay admits only typed observed envelopes, tracks durable cursors/receipts and uses authoritative availability/correction cutoffs. The learner's strict observed export reader does not implement a model. Generator/calibration/truth/report engines belong to later packages and are unavailable here.

`build.py` records qualification, image IDs, source hashes, typecheck/client tests/build and 18 service integration groups. `run_stack.py` records positive evaluator and negative consumer storage/source/network probes. With the qualified contract Python interpreter, run `python tooling/foundation/verify_integration.py` for existing contract/library/DR/ledger and accepted-source preservation checks. It overwrites only current foundation check-result outputs, preserving historical failed logs. Browser acceptance requires the actual official Playwright MCP tools, not a CLI replacement. Detailed observed evidence and limitations are in `docs/implementation/evidence/G1-FOUNDATION-20261021/verification.md`.
