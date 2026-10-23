# S1 focused source repair

Repair source `969b9d0b5bc49bedaf87330fb24e77f38022930c`, branch `fix/poc-s1-source-review-20261023`, own worktree `C:/Users/erics/Documents/Projects/REMission/artifacts/s1-app`. Repair base `9f557b0abb91134e9c476d83d9b806d92b646630` is preserved. Integration/review comparison base remains `f124726432799103cde410ba98b7ab6992759591`. The final review candidate is the documentation commit containing this report, supplied explicitly to root after its creation. Assigned model/effort remains gpt-6.1-sol/high; no escalation or helpers.

This addresses the four mandatory findings in independent changes-requested report blob `b7ef8ede5c10ddc27bcf2295eb25a9013aaf2931`. Independent counterexample script/output blobs `08f11b63cdf314c02bf10377aec78dedb5b83d37` / `4857655759749c0e9cb4b00428ecee250bd08eba` remain original evidence.

| Finding | Repair and focused evidence |
|---|---|
| Incorrect completed interval could repeat consistently in output/diagnostics | Both endpoints must match coefficient ± t(.975,df)×SE for admitted df7..11, and strictly enclose the coefficient. Typed completed summary-gate positive now uses the declared formula. Zero-width, normal/wrong critical, asymmetric and consistently changed wrong-df counterexamples reject. |
| Displayed R1 range could disagree with nine cells | Available range must contain two finite numbers exactly equal to min/max of the nine finite coherent cell estimates. Withheld sensitivity requires null range. Typed wrong-range and available-null cases reject. Rehashed corrupted interval/range artifacts fail ingestion before state mutation; an explicitly corrupted persisted completed shape yields no served result/accepted badge through authenticated generic job read. |
| Primary missingness restriction absent from visible result | One sentence beside interval/counts now states complete observed rewards under the synthetic independent10%MCAR reporting law, without an identified adjustment for outcome- or action-dependent missingness. No panel/workflow was added. |
| Literal mojibake in old/new panel strings | Restored UTF-8 middle dots and ellipses. Explicit UTF-8 decode/source scan passes; retained inspected lines in the raw source-scan artifact. No permanent test asserts exact prose. |

The completed fixtures are explicitly hand-authored scalar summary-gate shapes. Their toy histories contain no randomized decision cohort; they are not fitted results or genuine P2/P3 evidence. No estimator run or scientific import was used to repair the gates. Existing `data.py`, `wcls.py`, config/model descriptors, closed old branches and dependency lockfiles remain unchanged.

## Critical constants and tolerances

The scalar table contains only the five values possible for the admitted8..12contributing clusters. It introduces no numerical backend or general quantile implementation. The 0.975 column for a two-sided95% interval follows the [NIST Student-t table](https://itl.nist.gov/div898/handbook/eda/section3/eda3672.htm). Public primary educational outputs were read on2026-10-23, without executing their code:

| df | t(.975,df) | Read-only reference |
|---|---|---|
| 7 | 2.3646242515927844 | [DTU regression solutions, section5.2/page7](https://02323.compute.dtu.dk/enotes/solutions5-Python.pdf), indexed primary-source output for `ppf(.975,7)`; full current PDF extraction did not expose that number, so the indexed output is the precise retrieval evidence. |
| 8 | 2.306004135204166 | [DTU Chapter9 exercises, page22](https://02403.compute.dtu.dk/enotes/chap9_exercisesWithFacit.pdf), `ppf(.975,12-4)` output. |
| 9 | 2.2621571628540993 | [University Düsseldorf mathematics notebook, Out4](https://www.math.uni-duesseldorf.de/~internet/bio2425/lektionen/lektion22.html), `t(9).ppf(.975)`. |
| 10 | 2.2281388519649385 | [University Arizona CSC580 lecture04, slide46](https://www2.cs.arizona.edu/~pachecoj/courses/csc480-580_spring25/lectures/lec04_practicalissues.pdf), printed0.975/df10output. |
| 11 | 2.200985160082949 | Existing accepted day84 result blob `89cf5ea6735447e36a9f42ba4c14d0175f08df85`: coefficient `.418201139591797`, SE `.05449099548884957`, interval `[.29826726716221863,.5381350120213754]`, df11. The table yields those endpoints within the bound below; no accepted fit was repeated. |

Endpoint admission uses `math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-10)` after finite scalar checks and strict positive width. This is `abs(actual-expected) <= max(1e-10,1e-9*max(abs(actual),abs(expected)))`; it covers floating serialization/library roundoff without accepting normal critical values, wrong degrees of freedom or zero width. R1 range uses exact min/max equality because both range and cells serialize the same stored point estimates, with no additional arithmetic or quantile approximation.

## Actual checks

- Before repair, new scalar CI/range counterexamples produced eight expected subcase failures in `artifacts/source-checks/repair-counterexamples-before.log` (15tests,2.792s). This complements the independent typed counterexamples above.
- `artifacts/source-check-env/Scripts/python.exe -B tests/run_support_s1_scalar.py`: **16/16PASS**, no skips,3.385s; scientific-import tripwire passed, no blocked modules loaded. This includes the typed completed gates and rehashed completed ingestion/serving negative regression plus the existing13focused checks. Exact existing pinned non-scientific environment is retained; no dependency changes.
- `npm run typecheck --prefix web`, `npm run build --prefix web`: PASS. UTF-8 source scan: PASS. The six unchanged request/context helper tests retain their previous pass; no unrelated rerun was needed. Browser/rendering proof remains pending.
- `git diff --check`: PASS. WCLS/features/dependency lockfile comparison against9f557: unchanged. Original candidate, accepted offline evidence, original stages and other worktrees were untouched.

Raw repair logs/source scan and the existing exact-pin environment remain under ignored own `artifacts/`; tracked `evidence/s1-app-source-preparation-20261023/repair-manifest.json` binds the raw file hashes. No genuine archive admission, original-stage access, numerical computation, worker invocation, Docker/build/pull/run, server, browser, cloud or credential operation occurred.

## Remaining verification and retention scope

The prior handoff's authority/public materialization, exact role-image/COPY/dependency/operator freeze, one disposable Store P2 import/reimport/all72genuine projections, one NEW same-Store day84 app WCLS job and accepted coefficient/SE/full covariance comparison remain required and unexecuted. No runtime GO follows from these fixes. Human/clinical review remains later.

The ambiguous submission key lives only in the mounted panel's ref. It survives in-panel cutoff/mode selection; navigation, reload or reauthentication can remount the panel and clear that ref. Persisted attempts and session-scoped receipts remain server-side. The later browser/reconciliation cases must include navigation/reload/same-doctor reauthentication during an unknown submission outcome, saved-attempt discovery and safe explicit reconciliation before another command. This nonblocking limitation is disclosed rather than presented as persistent client intent storage. The later browser check must also verify the visible MCAR restriction, UTF-8 text, narrow/keyboard layout and actual stale-response behavior.

Source repair is ready for independent exact-head re-review, not self-accepted or runtime-qualified.
