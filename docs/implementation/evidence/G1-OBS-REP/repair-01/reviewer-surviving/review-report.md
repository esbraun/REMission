# Independent exact-code review: OBS-REP-02

Disposition: **changes_requested**. This candidate is not ready to ship. Two P2 admission defects below reproduce at the actual public wire verifier. No source changes, commits, PR or merge were made by this reviewer.

Reviewed head: ceb5a5fc786f487045fd948986bc4bb8b8a43bf4
Accepted target/base and observed merge-base: 6bc8bd998e8a0baaef9884998e740665fb5fd7b1
Own detached checkout: C:/Users/erics/Documents/Projects/REMission-worktrees/g1-obs2-code-review-astra-20261021
Own HTTPS clone: same path/.review-artifacts/https-clone
Assigned reviewer: gpt-6-astra / medium. No independent effective-model introspection is available; no substitution was requested or made. Thread environment CODEX_THREAD_ID: 01a1604e-013b-7d92-8e5f-ffc6c092c0c5; task /root/g1_obs2_code_review_astra.

## Findings, severity ordered

### P2: Bind every hold record to its containing export run and partition

Location: contracts/runs/admission_v2.py:239-245, particularly the hold_transition_bundle branch at244; related contracts/domain/evidence_v2.py:148 onward.

The final admission loop validates a hold bundle against its internal predecessor/review references, but never compares the bundle's run_id/partition_id with manifest.run_id/partition.id. The same missing boundary applies to hold_review_evidence (including standalone review records). validate_hold checks review-to-bundle and predecessor-to-bundle equality, so a mutually consistent foreign chain passes. RecordBinding.identity can identify the legitimate enclosing run while the typed administrative records identify a different run/partition. A canonical hash authenticates those conflicting bytes; it does not resolve the conflict.

Reproduction source blob: 5b8bef5d0ed5fe749316e5bd5ed8c625d385dc5a. This is the complete executable probe; it reads only the own candidate fixture source, builds an unchanged positive fixture, then builds a variant changing exactly the two fixture constructor occurrences of run_id=run_id, partition_id=partition_id, hold_episode_id= to foreign-run/foreign-partition. It does not change any candidate implementation. Fixture construction recomputes exact references/raw hashes and the explicitly fixture-only authority. Both variants are parsed from serialized public bytes through verify_export_v2.

Expected: unchanged fixture accepted; foreign embedded hold identities rejected even with internally consistent refs and hashes. Actual stdout blob2039080d735ed187ac94b4d1703bb70d1834e1ec:

positive ACCEPTED obs2-fixture-run obs2-partition [('obs2-fixture-run', 'obs2-partition'), ('obs2-fixture-run', 'obs2-partition')]
foreign-hold-run-partition ACCEPTED obs2-fixture-run obs2-partition [('foreign-run', 'foreign-partition'), ('foreign-run', 'foreign-partition')]

Raw command blob01192dfda3079b87575e953da830ca577c37d883; stderr empty e69de29bb2d1d6434b8b29ae775ad8c2e48c5391. Applicable accepted R1 section6 exact patient/run/episode identity and independent pre-code case17. Repair should reject mismatched bundle and review identities at the enclosing partition boundary, including unreferenced review evidence, while retaining same-patient historical facts with valid exact identities. Add real-wire positive/reject regression cases. The current clinical rejection guard still rejects the hold partition; this finding concerns archive correctness, not demonstrated live authorization bypass.

### P2: Reject generated symptom reports beyond day84 while permitting day85 administrative bookkeeping

Location: contracts/runs/admission_v2.py:112-125 (record validation checks receipt bounds and diary fields but not generated observation horizon); related contracts/runs/private_v2.py:146-152 (correct day-key equality does not constrain the allowed generated symptom day).

The accepted R1 explicitly keeps DGP generation at -14..84 and permits only the non-symptom administrative endpoint link at day85. The verifier checks day84 endpoint links for undefined/outside_generated_horizon, but accepts an additional generated DailyReportV2 at local day85 with a numeric diary and quality. A later receipt cutoff does not authorize that extra symptom process. The public trusted schedule already contains time-zero/timezone/planned horizon, so this is an enforceable representation distinction rather than a request to invent a scientific law.

Reproduction source blob ae8f19352ad6ad1fb8411a44a927f245d0217f6e. Complete probe builds a positive partial fixture at day85 10:00 and a variant with one extra generated diary report at day85 07:00, recorded/available08:01. The extra report has source version1.2.0, patient_report adapter, canonical full raw provenance and correct day85 identity. No day84 outcome slot is replaced and no candidate source changes are made. Actual verify_export_v2 result stdout blob353229f42e0a95d1efdf53e9ebb803537b49b89d:

positive-no-day85 ACCEPTED [('2026-01-02T07:00:00+00:00', -25.0)]
forbidden-day85-diary ACCEPTED [('2026-01-02T07:00:00+00:00', -25.0), ('2026-03-27T07:00:00+00:00', 400.0)]

Expected positive accepted; additional generated day85 symptom record rejected. Command blob bfa88d3e8d229300cd4c039a47eb3138c9c8a9ed; stderr same empty blob. Applicable R1 section7 and independent pre-code case8. Repair must distinguish generated clinical observations from permitted administrative links/closures/reviews and delayed arrival of in-horizon reports. Do not broadly forbid records received after day84 or forbid day85 endpoint bookkeeping. This probe establishes public admission behavior; a complete private verify_result_v2 wire reproduction of this exact mutation was not performed. The private time-key observation above is source inspection, not a claimed private-wire execution result.

## Review basis and direct inspection

Verified checkout root, HEAD, clean tracked state and merge-base before review; explicit own workdir used throughout. Read implementation-prompt, delegation/engineering instructions, plan index and gate/scope/service requirements, the complete accepted R1 replacement including original sections1-5 and normative sections6-8, author README/checkpoint, runner implementations and independent pre-code oracle a9c7958fc15133c87635fe3619322d6c58a397f2. No repository AGENTS.md found. No author checkout or unaccepted generator/evaluator engine checkpoint was read. No subagents spawned.

Inspected changed domain records, explicit version/kind dispatch, full raw replay, evidence resolution/strict cutoffs, support decision/outcome/closure relationships, trusted coverage/receipt validation, private run/result/truth admission, shared admission changes, service archive/routes/replay/current guard, migrations and curated Docker copy lists. Reviewed current consent/approval rejection and whole-partition preflight placement. The source is unchanged relative to tested f049 under the frozen manifest scope; own verify_frozen_evidence passed for194 source files and764 raw artifacts. Root supplied separate Luna byte inventory blob2af51bf2ed403e11ffa0895143d80cc535aa2026; this is supplementary, not substituted for own execution.

No web source/client diff or new visible UI was found. New routes are API/archive endpoints; no MCP browser validation was needed for a visible UI change. The existing client builds/typechecks/tests in the curated build. This does not close outstanding browser/human gates elsewhere.

## Independently executed checks

All Docker probes used own source or own freshly built images. Ordinary runtime jobs were capped at2CPU/2GiB with network none, read-only root/source and bounded temporary storage. The numerical image is be4bbf7978bb318b8c3d2901e8e9510b746aa8554d5c0dbfc8eea5928d9f07f7; the service image is ce346feace2ae607ebd574e1bb681d594c9b676c06b56f8ba8d50b858a577faa. The service tag was checked against that exact ID. Curated npm acquisition used existing pinned lock and authorized registry access during build only. No versions/lockfiles were changed.

Own checkout service-base runs, complete raw logs in numbered command records:
-004 schema_checks.py: all five old/new domain/DGP/run exporters --check, pip check, actual foundation runtime qualifier,11library/artifact tests and11DR/OPE tests passed.
-005 tests/contracts:67passed.
-007 tests/run_contracts:49passed, including four private-v2 actual-wire calibration/evaluation-roster/execution/run/truth-roster/full-key/receipt tests.
-012 tests/integration/replay:25passed, including real cookie/CSRF/ownership routes, immutable raw archive, entire hold partition current denial including v1/direct route, SQLite before/after commit/restart, and allowlisted clinical subset.
-016 check-ledger:635 mappings and repository consistency passed.

Own HTTPS clone was acquired from https://github.com/esbraun/REMission.git with core.autocrlf=false and checked out detached at exact ceb5. Initial/final status empty. Every executed check path originated in that clone or /app mounted from it; no foreign preservation.py was used. Clone logs017(schema/runtime/artifact/DR),018(domain67),019(run49),020(service25),021(ledger635),022(clean status) all passed. The preserved final-checks/002 verifies exact HEAD;003 clean status;004 confirms HTTPS origin. Clone source was not modified.

Both own checkout and clone passed independent53-file V1 Git blob checks against frozen baseline inventory; final-checks/v1-own.json and v1-clone.json contain expected/actual IDs. Separate task-preservation.json records exact original coverage635 plus every original task ID/test_ids/requirement_ids/depends_on, not just counts. Candidate v1 parser/history/schema exports remained distinct and passed old/new exporter checks.

Fresh curated images under remission-obs2-astra-review-20261021-* built from this candidate: actual serviceUID10001 and learnerUID10002 passed public-v2 admission, cookie archive route and private imports/file/read/list/network/write denials, with evaluatorUID20000 positive canary file and HTTP controls. Consumer inspections confirm networknone, read-only volume-only mounts, no source mount; actual copied code bytes were compared to own checkout. Complete raw37-command build/probe/cleanup record in curated-attempts/000/commands.json and inventory.json. Separate final-checks/001 ran the curated tests image as actualUID10001 and passed25/25 service tests. Resources were uniquely named and removed by own runner; no old8765-8768 stacks/databases/MCP state touched. Images remain available for inspection.

These are bounded wire/engineering checks, not producer/scientific qualification. Existing suite tests address the listed temporal/probability/stale-reference/closure/private-admission controls; passing their counts is not proof every independent oracle case has complete integration evidence.

## Failures and evidence limitations

Initial numeric-image schema runner reached all schema checks and pip then failed foundation qualify because argon2 was absent. Initial numeric run-contract import similarly lacked argon2; service tests lacked fastapi. These were environment-selection failures, not candidate regressions. Correctly pinned service-base reruns above passed. The initial custom hold probe also failed once because PYTHONPATH was missing; probes/000 preserves it, and the next call adds PYTHONPATH=/app and reproduces both positive/negative facts.

Reviewer instrumentation mistake: reproduce.py and service_reproduce.py initially shared a length-based output-number allocator while overlapping. Four original records were overwritten by subsequent complete command records: own numeric run-contract failure, own numeric service failure, original HTTPS clone acquisition command output, and clone numeric run-contract failure. The surviving numbered records have matching stdout/stderr hashes; none is mislabeled. Initial numeric schema failures002/010 and clone numeric service failure013 survive. Original tool-session output and reproduction script retain the fact/commands of the overwritten attempts, but their complete raw streams are unavailable. This report does NOT claim full preservation of every original reviewer attempt. Later service and clone final results are complete; independent probe and curated directories were separate and unaffected. No author evidence was overwritten or changed.

Unexecuted acceptance: no independent newly authored complete85-decision/day85-terminal wire fixture was executed; no new actual producer process qualification, full likelihood/density implementation, generator/evaluator calibration execution, full statistical suite or live hold latch was implemented/reviewed. Existing terminal coverage unit cases and fixture tests are limited evidence, not substitutes. The two findings suffice to reject this candidate; a repaired head requires fresh review/checks, including appropriate positive complete administrative endpoint evidence and negative horizon/identity cases.

B-OBS2-LIVE-HOLD / T-OBS2-LIVE-HOLD remains a required separately accepted ENGINEERING prerequisite. The current rejection guard is not live invalidation, owned review or evidence-gated clearance and is not deferable to G5/humans. No new burden/clearance law was invented. No acceptance of wholeG1, G2-G7, real patients/orders, human factors, clinical review or clinical validation. Affected consumers remain HELD pending repair, fresh exact-head review, root integration/integrated verification and explicit dispatch.

## Evidence storage and reproduction

All surviving raw command metadata/stdout/stderr, independent probe sources, curated fixture bytes/inventory and review helper sources are indexed with byte lengths/SHA256/Git blobs in artifact-manifest.json. Blobs were written using git hash-object -w --no-filters in this own repository, with no staging/committing. HTTPS clone contents and __pycache__ are excluded from the evidence inventory; their verified source head and clean-state logs are retained. Manifest excludes itself to avoid a cycle. FULL report is meant to be consumed by root and routed to Sol; findings are not resolved by a summary or claimed fix.
