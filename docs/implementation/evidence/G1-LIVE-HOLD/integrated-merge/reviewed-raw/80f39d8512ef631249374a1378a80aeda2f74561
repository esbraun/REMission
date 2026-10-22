# Independent G0-TIME-R1 exact-head review

Date: 2026-10-21. Disposition: **ready_to_ship for G0-TIME-R1 only**, at the exact head/base below. No unresolved blocking finding was identified in this bounded temporal amendment. This is not approval of G0, the DGP candidate, G0-LIB, statistical methods, application, browser, human-factors or clinical gates.

Reviewed head: `62e6ce85299b477b0c21a18d70b49392a68e1522`.
Reviewed accepted main base and observed merge-base: `6c3fb070d36bfefbd070f2a2c33ccba7631734be`.
Exclusive detached review checkout: `C:/Users/erics/Documents/Projects/REMission-worktrees/g0-temporal-r1-review-20261021`.
Reviewer: `/root/ope_critic_astra`, thread `01a15d56-cc14-7a43-8e66-9da3e290da2e`.
Requested model/effort: `gpt-6-astra` / `medium`; explicit assignment observed, independent effective-model/effort introspection unavailable. No substitution or escalation.

Verified root, detached HEAD, exact base ancestry and clean initial status before inspection. Candidate diff has the assigned 22 files. No candidate source or committed evidence was edited. Review artifacts use only this checkout's ignored `contracts/domain/__pycache__/time-review/`; this new report is the only untracked nonignored addition. Prior reports/artifacts remain preserved in the reviewer's previous checkout, which was not needed for source execution. No author checkout/environment, staging, commit, PR or merge was used.

## Findings and temporal resolution

The amendment resolves the specific DGP timing ambiguity recorded in review blob `94b100b39558fce4c6c17f9f79a6acad0c159b04`: reporting previously occurred before its declared current observed pain parent. The new canonical text in `docs/spec/01-estimands-and-contracts.md` under TIME-01 and `docs/spec/dgp-reference.md` under reporting/availability consistently distinguishes the prior-night outcome event at 07:00, independently observed current pain available by 08:00, report observation/recording at 08:01, and upload availability measured from recording. The 0/1/3-day delay values and .7/.2/.1 probabilities remain unchanged. The independently keyed wearable stream retains default 07:00 availability. Current unobserved quality stays evaluator-only for MNAR generation; the MAR mechanism and numerical coefficients are not silently changed.

`contracts/domain/temporal-v2.json` and `TemporalContract.no_future_or_same_phase_cycle` encode an acyclic same-day sequence: morning measurements, independent wearable availability, current clinical L, observed pain, pre-report history, report observation, report availability, later decision history, interruptions/administrative guards, eligibility and assignments. An independent enumeration checked that every same-day parent has lower phase and all lagged edges point backward. Required and exact parent restrictions prevent direct hidden/current-outcome MAR parents and report/pain parents on wearable availability. The generation DAG can retain latent structural causes without exposing them as observed MAR predictors.

`ReportingDecision.observed_pain_and_clock` validates the patient's exact history cutoff, separate event/recording/availability clocks, an active clinical Observation resolving the pain record ID, current pain event ordering and strict predecision availability. `Observation.observation_clock` independently binds nested pain times to its record. `LearnerHistory.validated_projection` verifies same-patient provenance, active lineage heads and strict-before visibility. The new decision additionally rejects current/future daily reports from the pre-report snapshot, avoiding self-conditioning even when such a record would otherwise be available before the decision.

`ReportingDecision.mar_predictors` derives exactly previous observed quality, missing-history flag and current observed pain. It cannot accept caller-supplied current quality or latent truth fields. Latest eligible quality is selected by event time with deterministic available/recorded/ID ties; absent usable history produces quality7 and an explicit missing flag. A validated observed record is not cryptographic proof of its clinical origin: the candidate correctly leaves independent generation/source authenticity to DGP/G1, rather than claiming that a DTO proves it.

Strict-before history excludes all exact-cutoff arrivals. Stable replay ordering does not make an equal-time report available. Existing `boundaries.py`, `entities.py` and original `test_domain.py` are byte-identical to the accepted base: current consent/hold precedence before assignment, active correction/retraction handling, prior-night symptoms, recall windows and no-postdeath outcome guards remain unchanged and their original tests still run. The new known-death reporting rejection also passes. Actual transactional guard ordering remains the G1/G5 responsibility already documented; this amendment does not claim to execute it.

## Version and provenance identities

- Historical TIME-01 v1 file remains Git blob `2a197d76b938dbda3279a26a6645cada78a89508`, identical to accepted main.
- Proposed TIME-01 v2 version is `2.0.0`, with wire schema `1.0.0`.
- Independently recomputed v2 source SHA256: `fd2fe478e1fbf5237a307af8a2067fd6d485183763086ac7e10c133fda002275`.
- The hash uses exact UTF-8 source bytes with CRLF normalized to LF, without JSON reserialization. This is the documented source-version convention, not the byte-exact offline payload checksum convention.
- `consumer-version.json`, the task ledger and checker agree on the identity. The historical v1 payload still validates; v2 requires its reporting rules; attaching v2 rules to v1 or using an unknown temporal version fails.

The generated temporal/reporting-decision schemas and dictionary match typed source through the exporter. The ledger preserves all 635 mapped requirements and original stable test IDs, places G0-TIME-R1 before dependent DGP work and final reproduction, and verifies unchanged raw accepted/DGP/OPE report blobs. It does not require unpublished c239/8315 author objects.

## Independent execution

Created a new isolated virtual environment at `contracts/domain/__pycache__/time-review/venv`, then installed only the existing exact pins from `requirements-contracts.txt`. No shared author environment, methods runtime or package selection change was used. Ran the read-only candidate runner without `--record`, preserving committed evidence:

```text
<own-venv>/Scripts/python.exe docs/implementation/evidence/G0-TIME-R1/run_checks.py
<own-venv>/Scripts/python.exe -m unittest discover -s tests/contracts -v
<own-venv>/Scripts/python.exe contracts/domain/__pycache__/time-review/adversarial.py
```

Observed results:

| Check | Result |
|---|---|
| pip consistency | Pass |
| Domain exports: 18 schemas and dictionary | Pass |
| Original27 plus new8 temporal regression groups | All35 pass |
| Ledger, coverage, inverse mappings, dependencies, immutable reviews/version identities | Pass |
| Full-base whitespace | Pass against exact accepted base |
| Independent graph order and normalized consumer hash | Pass |
| Additional composed boundary checks | Pass, detailed below |

Adversarial checks beyond the eight author groups reject cross-patient decision/history, cross-patient record, changed pain source hash without matching provenance header, unavailable nested pain, v1 on the new reporting decision, unsupported two-day upload, backdated recording, and current-report self-conditioning inside an otherwise valid projected history. Separate positive checks show that a delayed newer report does not replace the latest available quality, a valid correction replaces the prior quality, and its subsequent retraction restores the missing-history fallback. These use actual typed validation and public projection methods, without mocks or bypassing model validation. Reproducer and outputs are retained in ignored `adversarial.py` and `adversarial.log`; standard outputs are `checks.log`, `tests.log` and `install.log`.

Performed a genuine HTTPS clone into a new owned ignored directory:

```text
git clone --single-branch --branch launch/g0-temporal-r1-20261021 --no-local https://github.com/esbraun/REMission.git contracts/domain/__pycache__/time-review/fresh-clone
```

The clone resolves to exact `62e6ce85299b477b0c21a18d70b49392a68e1522`, has only the assigned branch fetch mapping, is nonshallow, has no `.git/objects/info/alternates`, and is clean. Running the full read-only amendment runner from that clone using the reviewer's own pinned environment passes pip, exports, all35 tests, ledger and full-base whitespace again. No object copying or other checkout linkage was used. Logs: `clone.log`, `clone-checks.log`.

## Scope and remaining gates

Read the exact changed temporal source, generated exports, amendment consumer/evidence/runner/handoff, canonical TIME-01 and reporting/MAR/DGP timing equations, accepted record/projection/lineage types, relevant prior DGP finding and ledger revisions. The unchanged entry/index, scope/invariants, delegation, engineering and gate requirements remain the bounded context used in the preceding reviews; targeted current-checkout reads confirmed the relevant amendment and preserved guard boundaries. No whole-repository load or broader package/method tournament was undertaken.

This acceptance allows root to integrate this exact temporal amendment under the existing reviewed-merge procedure. DGP still must consume the accepted version/hash explicitly, implement the independent pain/report/upload streams and timing, preserve calibrated scenario semantics, and pass its own full/fresh review. This review does not execute a generator, prove independently keyed random streams at runtime, fit a model, run the20-fit pilot, validate MAR/MNAR recovery, or close G0-LIB/OPE/G4/G5. Original and repaired DGP candidates remain separately unaccepted. Deferred human/clinical review is not a blocker for this labeled synthetic engineering amendment.

Final disposition: **ready_to_ship, G0-TIME-R1 only, head `62e6ce85299b477b0c21a18d70b49392a68e1522` against base `6c3fb070d36bfefbd070f2a2c33ccba7631734be`**. A changed head or target base requires refreshed review and affected checks. G0 and all remaining synthetic/statistical/application/human/clinical gates retain their existing unfinished status.
