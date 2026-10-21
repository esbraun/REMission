# G0-CONTRACT independent re-review R1

2026-10-20. Disposition: **ready_to_ship**, scoped to G0-CONTRACT only.

Exact reviewed head: `abd511c5870d41269980f4554be89407b31749d6`.
Exact reviewed main base: `e7965b998fa70df82e63a89ef720a6c8ad46ce6d`.
Reviewer: `/root/g0_critic_astra`, independent of Sol author, explicitly assigned `gpt-6-astra` / `medium`, unchanged; effective settings not independently introspectable.
Exclusive checkout: `C:/Users/erics/Documents/Projects/REMission-worktrees/g0-contract-review-20261020`, verified detached at exact head. Prior untracked changes_requested report preserved.

## Findings and resolution

No remaining actionable findings in this bounded re-review. Inspected source/test/schema/documentation changes from original head 939dd29254bc4a6f2c4f6c92330bd1c3fc11c9d4 and current evidence/ledger. All three earlier findings are resolved:

1. Consent.permits rejects retracted records; approval resolves available validated lineage heads, retains retraction tombstones, and fails closed on missing ancestry. Independent probes permit the earlier valid authorization before a later retraction, reject exactly at retraction availability and afterward, reject a lone retraction missing its predecessor, and reject the original retracted-root payload. No superseded authorization was revived.
2. ObservedHistory now projects to distinct LearnerHistory active values plus value-free lineage headers. Independent composition probes included original R1, corrected R2 and a later duplicate of R2. Before correction availability, and exactly at its timestamp under strict learner cutoff, valid LearnerInput retains only R1/7.0. At the later cutoff it retains only R2/3.0, with three available provenance headers and no sleep-quality values in those headers. Both earlier and later projections validate; duplicate/superseded clinical values do not enter the likelihood records. Regressions also reject missing ancestry, doubled active values and mismatched request cutoff.
3. Endpoint validation now binds registered units/direction for every target and names the quality reward for policy value. Independently reran all three original bad payloads (N1/MRT/policy with ISI_points and lower_is_better); each raises ValidationError. The expanded tests independently vary wrong unit and wrong direction for all seven targets, and reject missing/unknown policy rewards.

## Executed checks

- Verified root, exact candidate and prior report preservation. Reused the reviewer's previously installed isolated pinned venv under ignored `contracts/domain/__pycache__/review-artifacts/venv`; no dependency changes required reinstalling.
- Ran `tests/contracts/run_checks.py` without --record: pip check, deterministic schema/dictionary export, full unittest discovery (27 tests, including the three new regression groups), and ledger preservation checker all passed. No candidate evidence was overwritten.
- Full-base `git diff --check e7965b998fa70df82e63a89ef720a6c8ad46ce6d HEAD` passed, exit 0.
- Ran the independent consent, projection/duplicate/equal-cutoff and endpoint probes described above; observed expected success/rejection in every case.
- In the prior genuine HTTPS clone inside the ignored artifact directory, fetched only the published branch and detached at exact abd511c. No local overlay or shared-object import. HEAD verified exact; .git/objects/info/alternates absent. Both unpublished original c239dca and 8315ee9 objects still absent (`git cat-file -e` exit 1 for each).
- Reused that clone's separate pinned venv and reran the same read-only runner: all four checks passed. Full-base whitespace check passed there too. Published-baseline reproduction remains independent of unpublished author commits.

The checker continues to verify all 635 stable coverage/test rows, canonical sets, inverse references, retained final acceptance, feasible pilot/release dependencies, published planning blob identity and immutable prior reports. New evidence remains per-task; it does not close multi-task requirements or accept G0 as a whole.

## Acceptance boundary

This approves the reviewed executable contract package and repaired pure guards, generated consumer schemas/dictionary and fixture evidence. It does not establish persistence/authentication/atomic race safety, process/storage truth denial, real artifact-import/worker behavior, DGP numerical completeness, library qualification, empirical methods, UI or browser acceptance. No application, simulation, fit, statistical study or human session was run. G0-DGP, G0-LIB and G0-WORKFLOW and downstream gates remain outstanding; human/clinical review remains separately deferred without blocking reviewed synthetic engineering assumptions.

Root may integrate this exact head/base under repository checks and protections, then assign integrated verification. Any new head or target base requires refreshed review and affected checks. Prior changes_requested evidence is preserved and is not retroactively rewritten. No PR/merge or G0 gate acceptance is claimed by this reviewer.

Only this new untracked report and ignored verification artifacts were written; candidate files unchanged. No staging, commits, helpers, other-worker checkout access or lifecycle actions. This report may be published unchanged as a bounded Git blob for root's evidence handoff.
