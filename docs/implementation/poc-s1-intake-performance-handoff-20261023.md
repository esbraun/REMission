# S1 intake: remove adjacent duplicated verification work

Source candidate only. Base is accepted main `810b643249bcb99214cd2f5b00ae9d5691d159db`, branch `fix/poc-s1-intake-performance-20261023`, exclusive checkout `C:/Users/erics/Documents/Projects/REMission/artifacts/s1-app/artifacts/replay-latency-sol`. Actual worker remains `gpt-6.1-sol` / `xhigh`; escalation reason is the measured near-900-second intake interval crossing archive proof, lineage, cutoff replay and persistent integrity. Independent exact-source review and later qualified-image/full-P2 review/GO remain required.

## Evidence and limits

The failed once-only full-P2 run is frozen separately on preserved branch `fix/poc-s1-replay-latency-20261023`, head `d18a580289ef0a549e6f52230f13ba75f3d8f0d7`, raw index `46b9d534af8b92000b4b751b19dc2c58fea36be6`, summary `affa9df43c743982491857fe1c406db134e8c707`, checks `7b3f47428cb877581f13eaabaf6454d8e0c17747`. It executed old runtime source `772d385c43eaf84778fef671add36915232e6730`, candidate `85c614ca75a707587851fa541aad35def084e301` and spec SHA256 `b03a43594234d7b1dd4f2cab42a0ecac79bd84d1d851bd55efc2a8ef7a69271f`. It did not execute main810 or this repair.

Final progress shows first intake plus its immediate count query consumed 894.518171394011 seconds, returned after its HTTP200 check at elapsed 895.731521472102, then began idempotent intake at 895.7315700660693. It reached the unchanged 900-second bound with no idempotent completion, GET, negative fixture or final P2 result. The stop/reap evidence is confirmed and all private state retained. This coarse phase localizes elapsed work; it does not prove its internal cause or establish receipt/count acceptance assertions that occur later.

The earlier accepted selected-public profile (`cb99c63146021791699b3279c80d02b893c65d9e`) measured two chosen full-history/day14 replays, not SQL, full intake, all 72 GETs or late cuts. It recorded 288 artifact reads / 7.1366 seconds, 2,864 pathlib lstat calls containing 1,432 is_symlink calls, and 1,607 evidence resolves / 1.1997 cumulative seconds. Cumulative timings overlap. Its reader differs from intake's existing request-local artifact cache, so its filesystem weighting cannot be projected onto full intake. The static map `5586a0546b48000b9b242e2c13f729b224df5df4` corroborates repeated paths, without timing them. These observations justify checking obvious adjacent repetition; neither selected profile nor phase timing establishes either change as the dominant 895-second cost.

## Minimal source delta

- `contracts/runs/support_research.py:read_artifact` now obtains one lstat snapshot per path/ancestor, using `stat.S_ISLNK` and the same Windows reparse bit. It still visits the file, every parent, configured root and above-root ancestry before resolution; strict root resolution, containment, ordinary file, link count, read, byte size and SHA checks remain. No ancestry or artifact result survives a read, and no descriptor/API/schema changes.
- `services/foundation/protocol.py:project_protocol` shares construction of a reduced reference after resolution. `context_ref` still resolves every context reference at the projection cutoff and, when supplied, the separate causal cutoff before testing whether its kind is included. It passes the already-verified record to reduction instead of immediately calling `exact` to repeat the same adjacent pair. Other `exact` callers preserve their own kind/hash/patient/head/cutoff checks. Included and omitted context, strict clocks, correction/retraction and recursive reduction behavior remain.

There is no new cache, skipped proof, global state, dependency/model/migration change, changed owner/receipt/DB/artifact binding, or production progress framework. `evidence_v2.py` and `support_archive.py` are byte-identical to base. The existing artifact cache was not duplicated. All full-P2 assertions, negatives and 72 required GETs remain required in a separately authorized future run. No cap increase is proposed.

## Source verification

Commands use the existing read-only scalar environment with Python3.13.7/Pydantic2.14.1/FastAPI0.157.0/Starlette1.9.0/httpx0.28.1:

```powershell
& 'C:/Users/erics/Documents/Projects/REMission/artifacts/s1-app/artifacts/source-check-env/Scripts/python.exe' -B tests/run_s1_intake_source.py
& 'C:/Users/erics/Documents/Projects/REMission/artifacts/s1-app/artifacts/source-check-env/Scripts/python.exe' -B tests/run_nof1_source.py
```

The targeted runner passed 13 tests in 16.592 seconds: scalar ordinary/size/hash/missing/directory/hardlink/containment checks; injected POSIX-link and Windows-reparse metadata at leaf, parent, root and above-root ancestor; S0/S1 included and omitted context at all three cuts; bad exact hashes, causal equality cutoff, later correction/retraction and mutation between projections; and six existing hand-authored proof/inventory/source/runtime/consent/hold regressions. Metadata fault injection keeps link/reparse rejection testable on Windows without symlink privilege. It does not claim a POSIX runtime reproduction. The import tripwire loaded no scientific or generator modules.

The existing shared N runner passed all 65 controls in 19.359 seconds with its scientific-import tripwire. A separate source-only comparison against accepted base810 matched exactly in 24 cases: canonical S0/S1 projection bytes at cuts14/42/84 and exact rejection class/message for bad hashes, corrections, retractions, ordinary/bad-size/bad-hash/missing paths and link/reparse ancestry. Its script is frozen as a raw Git blob in the evidence index for reproduction; it only uses hand-authored fixtures, never the accepted archive or private Store.

Initial test drafting failed because the new fixture omitted required nightly rows (fixed in the fixture), an ambiguous test-module import selected a different module (removed from this targeted runner), and an unrelated existing full-v2 host-configuration fixture requires unavailable tzdata. The initial failed tool chunks are retained as explicitly transcribed observations, not falsely labeled original file logs. The untouched accepted-reader/projector host-configuration test reproduces `ZoneInfoNotFoundError: No time zone found with key UTC`, with its actual captured traceback bound in the raw index. No timezone substitution or dependency install was made. Unrelated full-v2 suites are not claimed passed.

Evidence is in `docs/implementation/evidence/s1-intake-performance-20261023`: source bindings/checks, exact baseline comparisons, raw check/log/script index, shared-run logs, baseline timezone failure and honest tool observations. No host scientific imports, accepted-archive benchmark, Docker/image action, retained Store/private read or runtime retry ran for this source task. Net full-P2 benefit is unmeasured; engineering source review cannot upgrade failed runtime acceptance, same-Store service/job/browser or human/clinical gates.
