# Independent G1 generator-interface implementation review

Disposition: changes_requested.
Reviewed head: 2a7726be23864cf9c933295f1d33da3d6fbedd1b
Reviewed base/merge-base: 69e6ae9dc5bf85ddbf39976d2ce4ce70bce1ea1e
Branch: launch/g1-generator-interfaces-20261021
Reviewer: gpt-6-astra / medium as assigned; independent effective-model introspection unavailable; no substitution requested/performed.
CODEX_THREAD_ID: 01a15f90-84f8-7b61-ae72-46eaec069201
Exclusive detached review worktree: C:/Users/erics/Documents/Projects/REMission-worktrees/g1-generator-interfaces-review-astra-20261021
Fresh independent HTTPS clone: the review-clone subdirectory of that worktree, fetched from https://github.com/esbraun/REMission.git and detached at the exact reviewed head.
No helper requested or spawned. No PR, merge, production filter, simulation, calibration, Bayesian fit, UI/browser operation or live database reset. Existing stacks/ports 8765-8768 were not operated.

## Severity-ordered findings

P1 — Bind conditional-ISI precision to its own authenticated matched pilot before computed admission.

Locations: contracts/runs/private.py:382, :539-541; contracts/runs/private_admission.py:118-129. Accepted R1 plan lines 19 and 37-45 preserve the separate symptom pilot/precision rules; the probability-only exception cannot supply their comparator SE.

InterruptionPrecision checks only that a computed numerical component names an evaluator_result artifact and a positive smallest_estimator_se. verify_truth never reads the matched_pilot references of symptom components. validate_truth_response cross-checks symptom count/mean/numerical MCSE against truth paths but never binds the claimed matched SE to a symptom pilot. The request comparator_pilot is the probability pilot plan on this path, not authenticated symptom comparison evidence. The committed positive roundtrip itself supplies that probability plan as the ISI matched pilot.

Independent fixture mutation retained the authenticated request, probability files and expected response structure, but changed both computed symptom matched_pilot references to missing/symptom-pilot.json with an arbitrary digest/size; verify_truth admitted it. A separate mutation supplied smallest_estimator_se=1000000 and was admitted. Updating the expected response digest in these probes models an authorized producer emitting internally inconsistent evidence; digest authenticity must not substitute for validation of its claimed dependencies.

Impact: a computed full vector can assert symptom precision without the required separately matched ISI comparison. For nonzero symptom MCSE an inflated SE can loosen the relative criterion. The conditional EST-INT branch also returns before the scalar conditional-accuracy check, so its separate symptom approximation tolerance must be bound explicitly rather than silently inherited from the probability epsilon. That conditional extension is a source inspection observation; the observed complete mutation fixture is unconditional.

Repair: require authenticated, target/action/history/configuration-matched symptom pilot evidence and recompute/verify its retained comparison summary using the unchanged accepted symptom rule. Check symptom conditional accuracy at the symptom epsilon where applicable. If this bounded interface package does not implement that qualification yet, fail closed for computed symptom/full-vector admission while preserving labelled partial outputs. Add missing-file, wrong-probability-pilot, inflated-SE and smaller-actual-SE faults; a generic hash/role or self-declared positive number is insufficient.

P1 — Do not accept IID truth from the smaller batch MCSE while its pooled Bernoulli diagnostic materially disagrees.

Location: contracts/runs/probability.py:264-281, particularly :276-281. R1 plan line31 requires diagnosing material disagreement between pooled IID and outer-batch uncertainty rather than selecting the smaller number.

truth_statistics calculates pooled_iid_mcse but admission checks only the batch MCSE and boundary term. There is no unresolved/investigation gate or reviewed disposition for the disagreement. Independent deterministic counts comprising 32 complete batches alternating 4999 and 5001 events in every component yielded mean .5, batch MCSE .000017960530202675507 and pooled IID MCSE .0008838834764831844. At epsilon .0001 the helper admitted the data. The IID diagnostic exceeds the tolerance by about 8.84 times and the selected MCSE by about 49 times. This same strongly underdispersed batch shape appears in the committed positive fixture.

These constructed counts are a deliberate diagnostic fault, not a simulated event-rate result. The point is that the purported qualification helper silently accepts the contradictory precision evidence. Reporting both numbers after granting computed status does not meet the accepted investigation requirement.

Repair: implement an explicit discrepancy policy that cannot silently authorize the favorable estimate. A conservative bounded implementation can require the IID pooled criterion as well and leave material uncertainty disagreement unresolved pending a separately recorded investigation; if a new statistical discrepancy threshold is needed, document/review it rather than inventing an unreported cutoff. Add the independent count example and a valid ordinary IID fixture, preserving conditional batch units and the existing sample/cap rules.

P2 — Cross-check the returned event-time and symptom-uncertainty payload against the qualified evidence.

Location: contracts/runs/private.py:531-541; contracts/runs/probability.py:337-377.

Probability qualification reads complete paired paths, but the public/private result vector's death_times_days and admission_times_days are never compared to those paths. The nested conditional_isi.isi.standard_error is also not checked against the recomputed symptom MCSE; only the separate precision record is checked. An independently mutated complete computed response with death_times_days=[999.0] and admission_times_days=[] was admitted although its qualifying paths contain day20 deaths and day10 admissions. A separate response with embedded symptom standard_error=999.0 was admitted while its precision record and recomputed MCSE are zero. The original positive fixture already uses embedded .005 versus recomputed zero.

Repair: derive or cross-check retained event times with an explicit documented aggregation/mapping from the qualified paths, and enforce agreement between the nested symptom estimate's uncertainty and its precision record (or require that optional field be absent if the precision record is authoritative). Preserve admission-before-death and full denominators. Add wrong-time, omitted-admission and conflicting-uncertainty mutations. These are inconsistent accepted outputs, not a request to qualify a future statistical producer now.

## Scope reviewed and successful independent verification

Verified clean initial exclusive worktree, detached exact HEAD, accepted merge-base and entire actual 79-file head/base diff (the assignment's 76 excluded the parent plan-document integration). Inspected all handwritten run/export/admission/probability contracts, adapters, Docker COPY changes, fixtures/tests, exporter, ledger/preservation/reconciliation scripts and the documentation/evidence changes. Generated schemas/dictionary were checked by deterministic regeneration rather than treated as independently handwritten logic. Read the canonical consumed estimand/truth/validation contracts and bounded execution/G1 instructions; accepted plan and critique history remained byte-identical. No author live checkout or uncommitted file was inspected.

Built fresh clone images with prefix remission-astra-2a7726, setting REMISSION_INTERFACE_IMAGE_PREFIX to that prefix before verify_interfaces.py. Reused only the exact accepted dependency runtime sha256:ce346feace2ae607ebd574e1bb681d594c9b676c06b56f8ba8d50b858a577faa; it was verified before builds. No author source overlay was mounted. Host Python initially lacked pydantic; an isolated reviewer venv installed the exact already-selected pydantic dependency versions, with no repository dependency/lock edit. This host environment observation is not a candidate failure.

All 17 runner commands passed from the reviewer clone: pip check; domain/DGP/OPE exports; 60 domain/DGP tests; 11 artifact tests; 11 DR tests; full DR replay; runtime inventory; 635-row ledger/ancestry; run schema/dictionary/bindings regeneration; 28 interface groups; 21 backend groups on read-only cloned source and in the curated test image; preservation; whitespace; and physical consumer probes. The exact accepted foundation-head to merged-base executable-tree comparison also passed. This preserves the accepted foundation without reopening unrelated UI or expensive method work.

Actual service UID10001 and learner UID10002 each admitted two public-only fixture partitions, excluded equal-time values from learner projections, denied observed writes and denied imports of private run/admission/probability/export, DGP/evaluation, simulation and truth modules. The service replayed into a new temporary SQLite database and verified two event rows. Consumer probes mounted public fixture bytes/authority only, not source. A separate independent no-mount byte probe hashed actual image public modules and compared them against this exact HTTPS clone: all service, learner and test-image copies matched.

Reviewer image IDs:
service sha256:740f1a1ef17cbb2702c433ad5007a47a40fc2a1b766a4d61141e8390494477b8
learner sha256:e5af6f2c9d431d373c97af01b90264d793fe091a31a47402533b963ce78984f5
tests sha256:9f7675689ed228ffdf1ea538c8f61373f6589d23aae0d62c6e87c45d9ce2b1e8

Independent precomputed oracle fixture (30 single-event trials, 970 zero-event trials, n_arm30) matched the helper's sample SD .0056890859575477, SD MCSE .0004954235000930 and lower .0048741142998947; its additional exact CP lower binding is .00474109334894243. The reviewed per-environment filter reuse/provenance guards, final-epsilon paired pilot refinement, fixed counts/levels and boundary-cap checks are present and their relevant bounded tests passed. The new findings concern admission requirements not covered by those passing checks.

## Evidence, preservation and limits

Raw independent mutation script blob: 7b16ef9cfb52cfd9304c6802eb2c8a8e8463ff3f.
Full observed mutation/oracle output blob: e5f2e1309b166234fb96a5d69ad377b416732650; process exit0, with the four bad-payload mutations explicitly ADMITTED and the underdispersed IID helper result retained.
The accompanying immutable evidence manifest records runner/build/consumer/source-binding files and Git blobs. The original review worktree's tracked files and author's evidence are unchanged. The nested disposable reviewer clone contains runner-produced evidence changes plus own untracked review artifacts/venv; it has no implementation source changes. Earlier author failure logs remain committed and unchanged. My prior accepted PLAN report c68541474c6e63b8f1cf9902c0d8c2b41def100e and independent oracle blob4deccc7a564f0ec12e21f137022735c82386fccd remain unchanged.

Digest/receipt checks establish artifact consistency relative to trusted external authority; they do not prove actual independent producer execution. This candidate correctly documents that no generator/filter/calibration/truth producer is qualified yet. I do not raise the absence of future jobs as a failure. Real source/runtime producer qualification, mandatory throughput/memory/storage measurement and all G1 statistical work remain pending, with no reduction in trials, caps, samples or later G2-G7 obligations. Human and clinical review remain deferred.

Root should route these bounded repairs to Sol, preserve this rejected exact-head report, then request refreshed exact-head/base independent review and affected checks. This report grants no merge acceptance.
