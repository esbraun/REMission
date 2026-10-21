# G0-DGP R2 bounded repair verification

2026-10-21. Status: candidate needs independent exact-head/base Astra review. This is not G0 acceptance, statistical validation or a human/clinical review.

Exclusive checkout: `C:/Users/erics/Documents/Projects/REMission-worktrees/g0-dgp-workflow-r2-20261021`; branch `launch/g0-dgp-workflow-r2-20261021`. Verified root, clean status and HEAD at accepted main `b24c3c0fb78bf19928750eae29e852141bd649a7` before commands. Merged preserved unaccepted checkpoint `2c76f4c34bc1536714f3e1988fc68da7372eb807` without conflicts, then repaired DGP timing locally. No other checkout was accessed. Only Git blobs/commits supplied prior work.

Ownership: CODEX_THREAD_ID `01a15eb8-0f9a-7cb2-b796-608d4ce5864b`. Explicit assignment: gpt-6.1-sol / high. Independent effective model/effort introspection is unavailable; no substitution or escalation. No helpers or nested agents. Root owns user communication, task/ledger integration, publication, independent review, PR and merge.

Consumed accepted TIME-01 2.0.0, wire schema 1.0.0, normalized-source SHA256 `fd2fe478e1fbf5237a307af8a2067fd6d485183763086ac7e10c133fda002275`. Hash rule: exact UTF-8 source bytes, CRLF normalized to LF, no JSON reserialization. Read accepted independent raw review blob `80f39d8512ef631249374a1378a80aeda2f74561`; source verification and typed contract checks pass. Historical TIME v1 is unchanged.

DGP parameter/catalog/timing version is 1.2.0; CalibrationBinding schema remains 1.1.0, independent analytic fixtures 1.0.0. Inventory remains 185 parameters, 73 variant rows, 82 cells. The stable `*-v1.json` filenames contain explicit current versions. Parameters, catalog and generated timing manifest bind the exact accepted temporal identity. Calibration target-specification hashes additionally bind that temporal identity.

The new clock contract sets outcome event 07:00, separate clinical pain observation/recording/availability 08:00, reporting decision/recording 08:01, then independent upload delays 0/1/3 days from recording. Wearable sync defaults to 07:00 with its own delay key. `report_decision` composes actual accepted ObservedHistory/ReportingDecision guards, checks the separate synthetic clinical-pain source and prevents a missing or report-only pain fallback. `mar_offset` preserves canonical coefficients and observed parents. Source identity does not prove source authenticity or independent generation; those remain G1 obligations.

Seven new DGP test groups cover exact temporal/version/hash binding, canonical observed MAR inputs, first-morning absent-history behavior, equal-time delayed previous reports, bad source/time/current-report rejection, crossed report/wearable delays and strict 07:00/08:01/09:00 cutoffs, S23/S24/S31 preservation, and distinct keyed measurement/observation/upload identities. These are deterministic contract/analytic checks. They do not execute random draws or prove stochastic independence, achieved missingness rates or a longitudinal simulator.

Read the bounded entry/index, scope/G0 gate, runtime/delegation/engineering requirements, approved task/technical plan and relevant ledger rows, canonical DGP/reference/scenario/TIME passages, accepted observed-history/record/reporting guards, original raw changes_requested review `94b100b39558fce4c6c17f9f79a6acad0c159b04`, partial checkpoint, candidate DGP/tests/evidence and workflow input boundary. Large concatenated reads were truncated; needed timing/guard/runner/fixture/ledger passages were fetched separately in bounded ranges. No claim of loading the whole package.

Created a new isolated ignored `contracts/dgp/.venv/` with Python 3.13.7; installed exact `requirements-contracts.txt` pins (pydantic 2.14.1, pydantic_core 2.50.1, annotated-types 0.8.0, typing_extensions 4.16.0, typing-inspection 0.4.4). Inspected the runner before execution. No methods stack installed.

Executed from this checkout:

```text
contracts/dgp/.venv/Scripts/python.exe -m contracts.dgp.export
contracts/dgp/.venv/Scripts/python.exe -m unittest discover -s tests/contracts -p test_dgp_timing.py -v
contracts/dgp/.venv/Scripts/python.exe -m contracts.dgp.checks
contracts/dgp/.venv/Scripts/python.exe -m contracts.dgp.checks --record
git diff --check b24c3c0fb78bf19928750eae29e852141bd649a7
```

Final full runner passes all seven commands: pip consistency, DGP generated exports, domain generated exports, all 60 contract tests (18 preserved DGP groups including S02/calibration reproductions, seven new DGP groups, 27 original domain groups and eight accepted TIME groups), ledger checks, working diff whitespace and full accepted-base whitespace. The initial full run exposed two stale test fixture DGP identities; `first-run-failure.md` preserves that failed attempt and its repair. Final raw command outputs/package versions/source hashes are in the additive R2 `check-results-20261021.json`.

Verified the original G0-DGP 43-test evidence, R1 partial/raw-review evidence and original workflow evidence are unchanged versus checkpoint 2c76f4c. Root subsequently authorized a minimal workflow Inputs paragraph update to accepted TIME 2.0.0 and DGP 1.2.0 candidate, linked to additive G0-WORKFLOW/R2/consumer-update.md. Scoped comparison confirms all other workflow text unchanged. No domain/canonical/root manifest/lock/master ledger edits. Earlier workflow acceptance is not carried blindly to the updated combined candidate; fresh independent exact-head/base review is required.

No fresh remote exact-candidate reproduction is claimed: this candidate was not published by this worker. Root must publish its exact head for independent clean HTTPS reproduction and exact-head/base review. All G1 generator/PRNG/distribution/rollout/truth denial and achieved calibration/pilot work, later statistical/policy gates, human-factors/manual accessibility and clinical review/validation remain outstanding. Human/clinical review is deferred explicitly; no real systems, patient messages or clinical actions were used.
