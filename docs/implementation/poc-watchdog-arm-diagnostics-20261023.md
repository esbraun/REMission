# WATCHDOG-ARM-DIAGNOSTICS: source candidate only

Base `3089956477ada4fc14da34bd2ca4fd365dbba596`; branch `fix/poc-watchdog-arm-diagnostics-20261023`; exclusive root `C:/Users/erics/Documents/Projects/REMission-worktrees/watchdog-arm-sol-261023`, verified clean before edits. Actual worker remains root-verified `gpt-6.1-sol` / `xhigh`; escalation reason is cross-process Windows launcher identity and cleanup uncertainty affecting safe prearm. Old S1 sources, private state, raw evidence and preparation drafts are untouched. No S2 work was performed.

## What the accepted failure establishes

Fully read accepted FAILURE_ONLY review `6aa31e3d6d0aaa012a158d6dbf757d8cab562e65` / checks `dd5f67a25e17470b3acc408525902e718243d5c8`, original failure handoff `3b811583be2d61360904e33b970cb419ce5e4543` / checks `11bc3cd2b2f4246b4d724f16bb7fd14d79fddd44`, raw index `e9218f4beb96daa27f50054bb8f8d572e70465e2`, and Luna static map `c6dbbd093437a2f559cea157098d305612d07568`. Only these frozen public Git objects and source were consulted; no retained process or Docker object was inspected.

Image attempt 8208/base4141 failed before the first qualifier started. Its literal CID was created/nonrunning/PID0, its ready receipt was rejected, no live ACK or attach or watchdog-terminal receipt existed, and the exact watchdog Popen was reaped with exit1. The parent's expected Popen PID/interpreter were not persisted. A Windows venv redirector PID difference is a hypothesis, not an established cause. Host descendant termination remains UNKNOWN; confirmed nonrunning container state does not upgrade that uncertainty. No role or updated controls image was qualified.

## Narrow diagnostic delta

`tooling/foundation/analysis_lifecycle.py` adds fields to existing retained `supervision.json`: selected interpreter, exact `-P -B` flags/argv/creationflags, expected and received public CID/nonce/deadline/PID identities, fixed mismatch field names, receipt identity match, two existing Popen liveness checks, and whether live prearm passed before start. Only the four public identity values are selected from a received dictionary; arbitrary extra receipt values are not copied. Exact equality still rejects missing/extra keys or any different identity. A PID reported by a child never replaces the parent-owned Popen PID or authorizes cleanup.

Exact attach/watchdog Popen creation, owned PID, reap success and returncode are also retained. An absent attach is explicitly not created/not reaped. `host_descendant_termination` is always UNKNOWN: this patch adds visibility; it does not add descendant custody or infer all descendants stopped. Existing literal-CID cleanup, independent state audit, finite deadlines, wait/kill/re-wait caps, terminal receipt checks, failure/STOP UNCONFIRMED behavior and command order remain. There is no new process manager, source role, dependency, image plan or application change.

## Source controls

```powershell
& 'C:/Users/erics/Documents/Projects/REMission/artifacts/s1-app/artifacts/source-check-env/Scripts/python.exe' -I -B tests/run_watchdog_arm_source.py
```

The new mismatching-PID double keeps matching CID/nonce/deadline but publishes PID102 for parent-owned Popen PID101. It proves refusal before attach/start, cleanup on the same literal CID, exact owned handle reaping, both identities and PID-only mismatch retained, a live pre-receipt poll, no post-receipt ACK, and descendant UNKNOWN. Existing successful completion orders also check matched/live prearm diagnostics. Adjacent unchanged controls cover atomic ready publication, early exit/arm deadline, strict typed state, missing/foreign terminal receipts, late command return, ambiguous cleanup and dispatcher gates. Real subprocess.run/Popen are blocked except explicit test doubles, and scientific/generator imports trip a guard. These are host source controls, not a native launcher reproduction.

Final targeted run passed all 12 tests, zero failures/errors, in 1.722 seconds. The existing lifecycle function ASTs and signatures are unchanged except the body of `supervise`; its signature is unchanged. Both the earlier passing draft run and final run logs are retained, with the final invocation explicitly using `-I -B`. Git whitespace and source binding checks accompany the candidate; no broad application suite or native launch is claimed.

The bounded test record/raw log bindings are in `evidence/watchdog-arm-diagnostics-20261023`. No real child/native launcher probe, Docker even metadata, Store/archive/private input, scientific computation, browser/cloud operation or old PID inspection/termination ran. The small inert probe proposal below is deliberately separate from production source and needs a separately frozen executable, independent review and new root GO before any real launch. Source diagnostics may be reviewed/merged independently; they do not authorize an image retry or S1 operation.
