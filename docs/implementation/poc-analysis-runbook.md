# Restricted V0 analysis runbook

PA1 plus thin PA2 extends the existing application. It is not POC4–6/study or human/clinical acceptance. Configuration `poc-visit-v1`, reduced history `poc-analysis-history-v1`, target `EST-VISIT:poc-hstar-v1`. One patient is an explicitly declared compatible cohort. Later borrowing, N-of-1, support, evaluator study and reproduction packages remain pending.

The [frozen author verification and evidence handoff](poc-analysis-verification-20261021.md) records actual day14/day28 app fits, retained failed pilots, copied image identities, migration faults, boundaries and browser checks. Computational configuration1.1.1 keeps the original statistical target and gates, uses the independently checked exact-guide parameterization and native target_accept0.995. Independent final release readiness is separate from that author evidence.

Build unchanged locks with `python tooling/foundation/build_live.py --evidence artifacts/pa12/build`. If the recorded offline build fails specifically during pinned npm acquisition, the authorized fallback adds `--allow-pinned-npm-network`; it does not change dependencies. The learner copies only public contracts and the visit method; the service has no numerical method or Docker socket.

The former `live_stack.py --analysis-dispatcher` launch and unbound `analysis_dispatcher.py --deployment ...` command are retired. The exposed stack option rejects before provisioning; it cannot start a background worker. Follow the [ordinary source preparation procedure](poc-cohort-ordinary-prep-20261022.md) for the replacement one-shot contract. Independent exact source review, changed-service image/COPY/Linux qualification, concrete persistent service invocation, actual queued-request/deployment bindings and explicit authorization remain pending; null/unbound JSON templates are not runnable commands. The workflow and restart description below records the earlier PA1/PA2 release and its immutable verification evidence, rather than authorizing current-source launches or retries.

Sign in as the synthetic fixture account, generate/select a patient, explicitly approve a behavioral plan, advance to day14, then open Analysis and submit. Submission commits the receipt, frozen public input and attempt in one SQLite transaction and returns promptly. Native NUTS runs separately in UID10002/network-none/2CPU/2GiB/read-only-root containers with a read-only public input volume and separate writable output. Future adherence is integrated in independent batches per retained draw; AR and endpoint measurement randomness are integrated exactly conditional on each adherence path. The whole integration cap is30minutes/K65536. No accepted interval is exposed on diagnostic or precision failure. Advance to day28 and submit a new attempt; earlier cutoffs stay visibly stale.

Logs, large posterior/predictive/expected-effect arrays and manifests are in task-private `analysis-jobs/<attempt>` artifacts and Docker output volumes, not Git or SQLite blobs. Concise results and diagnostics persist in `analysis_attempts`. Restart first stops previous learner containers, preserves their logs/output and marks interrupted attempts failed. Deliberate retry creates a linked new attempt; uncertain HTTP retry retains its original key. Historical decision/bundle bytes never change on completion. New decisions may freeze a saved accepted analysis reference. Holds and consent rules still control assignments independently.

## Explicit schema installation

Fresh activation applies001–005 offline. Normal service startup requires exactly schema1–5 and never migrates. To preserve an existing schema4 database: stop routing, service/dispatcher/learner processes and restart policies, back up the database, then run this release's `python -m services.foundation.cli upgrade-004 --database <stopped-DB> --bundle <installed-bundle>`. Run the command in the deployment's offline container with the actual database and admission-lock volume together, same UID10001, and mounted read-only installed bundle. It validates physical/control identity and performs005 in one explicit transaction. Start the service only after success; do not copy physical DB/lock files into a different volume and expect their stored identity to remain valid.

Historical003→004 is deliberately preserved byte-for-byte in `upgrade003.py`; the CURRENT CLI refuses `upgrade-003` before opening a DB. Its supported environment is the complete immutable schema4 SERVICE release `sha256:a92d7bda327ce7eb06a1d8ee03193d4090f148f48034bee63655d3cd8402dbcb`, corresponding to accepted POC1–3 source `a7ab7e60`. The numerical base image alone is insufficient. With all old processes stopped, run that service image's existing command:

```
python -m services.foundation.cli upgrade-003 --database /data/new.sqlite --historical-source /historical/old.sqlite --bundle /configuration/old-bundle.json --next-bundle /configuration/new-bundle.json
```

Mount old database/lock together at `/historical`, a NEW private writable target volume at `/data`, and the exact bundle files read-only. Keep routing disabled. After the schema4 command succeeds and its container stops, use the CURRENT service image against the SAME target volume and new bundle:

```
python -m services.foundation.cli upgrade-004 --database /data/new.sqlite --bundle /configuration/new-bundle.json
```

The first phase creates the new physical/control identity and generation exactly once.005 does not replay generation effects or rewrite old payloads. A failed/abstained analytical attempt is retained as such; retry never silently changes the model or thresholds. Exact chained migration and old-environment regression evidence remain required before release.
