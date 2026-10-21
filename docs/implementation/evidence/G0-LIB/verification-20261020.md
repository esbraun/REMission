# G0-LIB observed verification

Runs span2026-10-20 and2026-10-21 UTC; session filenames stay20261020. Base6c3fb070d36bfefbd070f2a2c33ccba7631734be. Exact committed checkpoint is returned in handoff. Needs independent review and held-out DR decision; no G0/empirical acceptance. [Qualification](../../library-qualification.md) describes runtime pins, sources, algorithms, initial failures and exact limits.

From the exclusive integration checkout, actual commands used:

```powershell
docker build -f tooling/library/python.Dockerfile -t remission-python-locked:20261020 .
docker build -f tooling/library/offline-r.Dockerfile -t remission-r-qualification:20261020 .
docker run --rm --mount 'type=bind,source=C:/Users/erics/Documents/Projects/REMission-worktrees/g0-sol-integration-20261020,target=/workspace' remission-python-qualification:20261020 python tooling/library/probe-python.py
docker run --rm --mount 'type=bind,source=C:/Users/erics/Documents/Projects/REMission-worktrees/g0-sol-integration-20261020,target=/workspace' remission-r-qualification:20261020 Rscript tooling/library/probe-offline.R tooling/library/__pycache__/outputs tooling/library/__pycache__/outputs/r
docker run --rm --mount 'type=bind,source=C:/Users/erics/Documents/Projects/REMission-worktrees/g0-sol-integration-20261020,target=/workspace' remission-r-qualification:20261020 Rscript tooling/library/probe-rbest-map.R
docker run --rm --mount 'type=bind,source=C:/Users/erics/Documents/Projects/REMission-worktrees/g0-sol-integration-20261020,target=/workspace' remission-python-qualification:20261020 python tooling/library/probe-coba.py
docker run --rm --mount 'type=bind,source=C:/Users/erics/Documents/Projects/REMission-worktrees/g0-sol-integration-20261020,target=/workspace' remission-python-qualification:20261020 python -m tooling.library.qualify-exchange
docker run --rm --mount 'type=bind,source=C:/Users/erics/Documents/Projects/REMission-worktrees/g0-sol-integration-20261020,target=/workspace' remission-python-locked:20261020 python -m tooling.library.check-runtime
.venv-contracts/Scripts/python.exe tests/contracts/run_checks.py
.venv-contracts/Scripts/python.exe -m unittest discover -s tests/library -v
git diff --check 6c3fb070d36bfefbd070f2a2c33ccba7631734be
```

Later `.command.json` files preserve UTC start/end, exact arguments and exit; earlier raw logs lack automated timestamps. Python and R API/file probes succeeded with diagnostic warnings retained. NUTS Rhat1.0277159130972902/bulkESS183.69102282080675/tailESS241.87426247123406 fail final criteria; gMAP largestRhat1.05/lowESS likewise. SBC calibration, recovery, mixture approximation validation, null/policy study and20-fit pilot were not run. Python/R WCLS coefficients agree1e-12; SE methods differ explicitly. SBC800 actual native-PyMC draw coordinates/values roundtrip. Six real output manifests are preserved and validate.

Locked Python build succeeded with51 exact wheel hashes; imagebe4bbf7978bb318b8c3d2901e8e9510b746aa8554d5c0dbfc8eea5928d9f07f7 has exactly equal distribution versions to original stable qualification imageac5e5d6cb2b2a4e4b955dab171c6dd917b22c5ba4b2466c59ee16ef178bd1e7c. R image2d24b2af23795f11935fd917486dd132c708f2d22e90cf706d540bcd647100d5. Actual pip-audit2.10.1 queried51 pins with no known vulnerabilities, exit0, not OS/full R security clearance. Initial capture wrapper hit Windows stdout cp1252 only after saving audit/build subprocess exit0; UTF-8 printing is fixed. Raw successful Docker build, image inspection, audit JSON and locked-runtime checks corroborate outcomes.

PyMC6.3.2/ArviZ0.22.0 intentionally fails resolution, exit1, dependency conflict retained. Discovery failures remain unchanged: removed PyTensor device flag, optional BCF None-term assertion, WCLS non-string column arguments, gMAP beta-prior shape. Corrected API probes passed. COBA exact fixed stochastic IPS gives[1,6,18], learning forbidden; stock held-out DR is rejected, not passed.

Seven rejection groups cover positive manifest/worker roundtrip, unsupported request/schema/sampler/precision/artifact catalog, hash tampering, producer failure/context/path, unit/mixture/shape, duplicate/missing/nonfinite draws, WCLS probability/analysis. All bad cases invoke costly worker zero times. Required final checks are captured in integrated-contracts/artifact-regressions/whitespace logs and command JSON. Contract runner checks pip,17 domain schema/dictionary exports,27 accepted fixtures,635-row preservation/coverage/inverse references/final dependencies and immutable reviews; artifact schema/real files are separately checked. PR11 review/parents are now asserted without weakening earlier checks.

A fresh no-local single-branch clone is checked after checkpoint commit without modifying candidate files; exact outcome is returned in handoff. The checker uses only reachable published planning/contract baselines, never unpublished original c239dca/8315ee9 objects. This is an engineering checkpoint with original OPE obligation unresolved, not full G0-LIB completion.

Minimal root tooling is required for executable qualification: `.dockerignore` excludes local environments/evidence from builds; `.gitattributes` preserves exchange bytes across Windows/Linux so SHA256 is meaningful, and retains raw process logs/R session as binary captures (their original trailing spaces/control sequences are not rewritten). Full-base whitespace checks apply to source/manifests/docs; raw binary captures are preserved evidence. Root manifests/locks remain sole integration-owner scope. New tests use stdlib unittest and the accepted maintained Pydantic dependency, with no new validation framework.
