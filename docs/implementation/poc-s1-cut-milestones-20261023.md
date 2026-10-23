# S1 early cut return milestones: source and qualifier preparation

PREPARATION ONLY; no build, qualifier, application, Store, archive or P2 run.
Base `8c32371d15d04a5d155f50ddec6c0b9169abfa08`. Proposal
`ffff2a415635d28a6a24ed970bf65da26c4bd6a9` and different-reviewer critique
`63729cda61e0294a62256d7fbcd9ab557a7d1675` are plan-only. Consumer map
`dbd7cbf820d2ae6b57d14b24702bb70101968d31` identifies the unchanged consumers.

The accepted stopped failure recorded 17 completed trajectories, 53 completed
cut intervals and 235 diagnostic rows. Its last event was trajectory18/cut3
before. A watchdog three-second inspect observation timeout ended that container
after584.399604seconds, before the configured900-second limit. Its watchdog
terminal field was null; cleanup, parent independent final and outer cleanup
confirmed stopped/PID0/exit137/nonOOM/restart0, with owned handles reaped.
No subcall cause, successful intake/commit, private count or P2 result follows.
Failure review `e22abb48b4a0ca590df2ad1aff1783713e19a3b6`, checks
`bbdb7fe10abd01fdb6a8979501a0c35090efcb15` remain failure-only.

The sole production change adds `cut_projection_return` immediately after the
existing `project_protocol` call and `cut_reader_return` immediately after the
existing original-projection reader call. Each is guarded by
`trajectory_ordinal == 1` at its call site. The existing `IntakeDiagnostics`
request filter excludes these new detailed names from later requests; they are
added to `STAGES`, never `COARSE`. No callback request attribute is assumed,
and no global state, cache, app option, read/stat/query/hash is added. Default
None, arguments, order, results, exceptions and all validation remain unchanged.
The existing `cut_after` still closes comparison and bookkeeping. Intervals are
wall-clock boundary samples, not pure function/CPU costs. One early trajectory
cannot attribute all histories, both modes, later persistence or the cohort.

All18 guarded host source controls pass without real processes, scientific
imports, application/API/Store/archive execution. They compare exact accepted
baseline source, strip only the two guarded calls to prove full archive AST
equivalence, exercise three-cut order, first-trajectory/request-only emission,
plain callbacks without attributes, projection/reader/comparison exceptions,
default-off equivalence, broken sink/clock/write-then-fail and transaction/fault
semantics. Existing24 assertions/72GET-loop ASTs and two authenticated409 fixture
assertions are unchanged. The frozen host parser copy must equal the updated
schema source; the final-result requirement and original live observer remain.

The complete maximum-width fixture emits409rows/45153bytes, exactly six extra
rows, with zero unintended suppression. All rows fit384bytes. Caps remain
512rows/49152diagnosticbytes and existing150progress rows at320bytes each plus
32768final-result bytes: combined maximum129920<131072. No cap increases.

```powershell
& 'C:/Users/erics/Documents/Projects/REMission/artifacts/s1-app/artifacts/source-check-env/Scripts/python.exe' -I -B tests/run_s1_intake_diagnostics_source.py
```

The subsequent one-role COPY qualification proposal reuses accepted controls
`sha256:e8070f001bddc1154b2ec516b64c91b593ce5012a57bb208f332b3b30a94f4c7`,
its complete196 map and actual proof0a4c801/b8f065. Only support_archive.py and
support_diagnostics.py need replacement; app.py remains inherited unchanged.
The expected-map COPY under /qualify accompanies those two production COPYs.
No RUN/USER/dependency/service/learner change is needed. The inherited strict
probe, IMAGE05 host helper and a63 lifecycle remain byte-identical. New exact
source/recipe/map/namespace/plan/command bindings require independent SOURCE+OP
review and new root GO; child image/CID stay UNKNOWN. No P2 executable spec is
prepared until actual image qualification and independent acceptance.

A later separately reviewed operation must target the early request1/trajectory1
three-cut sample while preserving all full-P2 assertions, original900work and
watchdog/resource/cleanup caps. It must explicitly accept possible fail-closed
termination before completion: instrumentation does not fix supervisory
reliability. If the same observation failure prevents useful new evidence,
retain it and return for a separately scoped supervisory diagnosis. No blind
rerun, timeout growth, retry, optimization, cache or partial-Store probe is
authorized. All older source/raw/private/resources remain retained unchanged.
