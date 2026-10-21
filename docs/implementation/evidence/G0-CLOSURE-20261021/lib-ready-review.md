# Independent full G0-LIB review

2026-10-21. **Disposition: ready_to_ship for the full pending G0-LIB qualification package at the exact head/base below.** No unresolved blocking finding identified. This accepts the bounded library/API/artifact qualification and implemented DR-EXCEPTION-R1 exception, not G0 overall, G2/G4 statistical validation, an application, or human/clinical acceptance.

- Head: `142f61217c850b132c3fcd21f59a5657fd9bbcfa`.
- Accepted target base and observed merge-base: `f11e90536b635a7db08cfed640445bec197a415c`.
- Exclusive detached reviewer checkout: `C:/Users/erics/Documents/Projects/REMission-worktrees/g0-library-dr-review-20261021`.
- Reviewer: `/root/dgp_r2_critic_astra`; requested `gpt-6-astra` / `medium`. Assignment is observed; independent effective-model/effort introspection is unavailable. No substitution, escalation or helper.
- Root alone manages integration. Changed head/base requires refreshed review and affected checks.

## Scope and preserved decisions

Verified checkout root, detached exact HEAD, base ancestry and clean status before source inspection/execution. Used explicit workdir, only this own checkout and an own ignored HTTPS clone. Reused only the previously qualified reviewer contract interpreter and locked dependency image; no author checkout or unpublished source overlay. No candidate edits, staging, commits, PRs, merges or agents were created. The only new nonignored file is this report; reviewer scripts/outputs are under `contracts/artifacts/__pycache__/dr-review/`, with ignore coverage verified.

Read bounded entry/index/runtime/delegation/engineering, gate and G0-LIB technical-plan requirements, library decisions and approved exception, affected source/tests/runner/verification/portability evidence. Prior full reviews remain part of this same review history and were recovered through Git: original plan `052677a20145fb14f5e1d2f509592a4de4942ef4`, original implementation `113f4f258a94ba9cc7fccce4b5fbb74bf0a72a49`, and accepted plan/repair review `bd9eb376680c7225cfdad3c0ac162d1698326063`. The last report accepted the plan before implementation; this report supplies the previously missing full implementation/runtime disposition. No whole-package load or new library tournament.

Original CSV arity/blank-patient-ID and wrong WCLS producer/input-lineage defects remain resolved by the unchanged R1 repair. Current 11 artifact groups pass, including before-worker rejection and leading-zero string identity preservation. The prior independent R1 review actually reproduced original failures, actual revised Python WCLS bytes, R WCLS results and SBC coordinates/values; those observations are historical, not new executions in this turn. The integrated preservation checks establish all original/R1 evidence outside additive DR remains unchanged against d842037, including original incorrect manifests, failed attempts, fit warnings and raw reports. Locks/Dockerfiles remain unchanged. Accepted domain/DGP/workflow sources and tests remain unchanged against f11e905.

## Findings and implementation assessment

No P1/P2 or other unresolved ship-blocking finding was identified within the assigned G0-LIB scope. Existing limitations below are not silently treated as solved.

`methods/ope/functional.py:59-77` is the single authoritative ordinary score: exact two-action integration plus factual residual correction, with ordinary IPS separately returned. It does not fit, learn, sample actions, self-normalize, clip or estimate propensities. `:22-56` validates full logging/target vectors, canonical availability and exact row order, rather than inferring counterfactual support from factual p alone. Duplicate patient outcome windows/daily contributions reject. Empty availability is accounted separately; missing eligible rewards abstain for the entire frozen roster. Deterministic compatible data are allowed without being called an MRT contrast.

`contracts/artifacts/ope.py:8-10,13-83` establishes strict integer action identity, finite features, exact finite basis/regularization/solver, versioned patient/time provenance and provisional training feasibility. `methods/ope/nuisance.py:20-35` validates before actual StandardScaler/Ridge fitting, uses only prior training inputs, and records raw source/training/plan/model bytes. `:38-71` supplies both action predictions from the sealed model in a reward-blind stage. Simulated event times are explicitly distinguished from execution clocks; future simulated labels are not claimed prospective observations. The finite fixture basis is not selection of the final scientific feature set.

`functional.py:97-160` binds protocol/roster/Q/target/receipt to the trusted caller's hashes, enforces disjoint evaluation membership and forward-time cutoffs, and rejects incompatible policy/source/row/action data before scoring. This is deliberately not authentication: a caller able to replace the entire trusted manifest can forge a new claim. The future G2/G5 immutable, role-aware catalog/process boundary remains required. The approved plan explicitly retains that responsibility, so this qualification does not pretend a self-declared receipt proves provenance.

`functional.py:80-94,151-160` implements pooled eligible-decision means and conditional whole-patient ratio resampling. It sums sampled patient score sums and eligible counts, uses shared sampled patients for policy differences, and holds target/Q/training fixed. At least 30 eligible independent patients and exactly 2,000 replicates are provisional engineering guards. Pooled adaptive inference is rejected; diagnostic point scores do not claim complete-cohort learning-algorithm uncertainty. The named target is current-action value over behavior-generated histories, not target-policy rollout or distal ISI. These boundaries agree with the accepted plan.

## Independent mathematical and adversarial reproduction

Recovered the unchanged preimplementation references through Git into own ignored artifacts:

- reference.py: `300b5fe79fc3fa35af5ed86a50c4fe0c82e9e5ce`.
- reference-output.json: `5b97e46fbd26b1d50c2c15ef279a73725ebb64a0`.
- exact-bootstrap-distribution.json: `38d36faf4b483aa90ccaf3bf906ce24388e52f42`.
- hashes.json: `b60023a3dbbe71c02b0ed8910d0e5308adb9751b`.

Fixture version `review-dr-reference-1.0.0` predates the candidate. Six independent rational score expectations are 11/3, 1, 8/3, 3, 4 and 3: nonuniform stochastic logging/target with nonzero Q; negative residual; zero Q/IPS; zero residual; zero target mass on factual action; deterministic probability-one action. Candidate outputs match at absolute 1e-12. The committed regression also passes the prespecified unequal-patient denominator fixture: pooled 25/9 versus equal-patient 7/3.

The independently prepared bootstrap population has 30 patients, ten each with 1/2/4 eligible rows and per-row scores 1/2/4. It has 70 rows and pooled value 3; a paired policy has each score reduced by 2, hence value 1 and difference B-minus-A=-2. Exact whole-patient bootstrap variance is 0.051329862520321234; incorrect row resampling variance is 0.02040816326530612. Candidate PCG64DXSM seed 2026102101, 2,000 replicates gives variance 0.051204058887324 and 95% linear-percentile interval [2.4825317604355717,3.3703703703703702]. Paired interval is [-2,-1.9999999999999998]. Independently looping sampled patient-type counts/sums reproduces every candidate replicate with maximum error 0. The saved sampled-index hash identifies the exact seed stream.

Compared the candidate empirical CDF with the preimplementation exact rational distribution: maximum difference 0.012925980751121002, below the two-sided 99% DKW bound 0.036394770800720934 for 2,000 independent replicates. This explicitly allows finite-bootstrap Monte Carlo variation; the earlier stdlib RNG reference is not falsely required to share NumPy's sequence. None of this establishes clinical sampling coverage or model validity.

Additional composed public-file mutations, with outer raw hashes and roster bindings legitimately resealed to reach deeper validation, reject before the sole score worker with zero calls: boolean in available-action vector, float factual action, same patient/day with different window ID, infinite feature, unsupported counterfactual target while factual support remains valid, target sealed after cutoff, prediction before fit, and reversed protocol policy order. These supplement the candidate's 11 groups covering training patient/future feature/reward/warm-up/basis corruption before Ridge.fit, raw file/source/model/Q corruption, missing/absent training/insufficient units, row identity, deterministic/empty availability and pooled dependence. Valid training control reaches actual fit.

Independent script/output: `contracts/artifacts/__pycache__/dr-review/independent.py` and `independent-results.json`. It uses test setup/resealing utilities only for file construction/zero-call observation; mathematical expectations and bootstrap population come from the preserved independent reference.

## Actual runtime, access and byte identity

Inspected runner/probe/stage/source before execution. Reused Python image `sha256:be4bbf7978bb318b8c3d2901e8e9510b746aa8554d5c0dbfc8eea5928d9f07f7` and own pinned Python 3.13.7 contract environment. No installs or costly unchanged NUTS/gMAP/BCF fits were repeated.

Executed the actual qualification recipe with only its WORK/EVIDENCE globals redirected to this reviewer's ignored directories. Production source was not patched. Four separate network-disabled read-only containers trained real Ridge, predicted from the frozen model without rewards, scored without training/model access, and rescored changed rewards with fixed Q/targets/receipt. Actual two forbidden-read attempts per stage were denied; training/prediction record maintained API calls, scoring records no fit/learn/predict/choice and no sklearn import. All stages pass. The own outputs retain commands/timestamps/exit codes, access traces, raw exchange, model and source manifests. This is a bounded fixture capability demonstration, not a hardened service authorization/security audit.

Source preparation is truthful: `tooling/library/probe_dr.py:25-37` converts the curated code tree to LF before execution and hashes those exact bytes. The actual own executed nuisance/functional/stage bytes equal the committed captured snapshots. Current Windows nuisance.py has 71 CRLFs and raw SHA256 3a4ca0dd0670fa6a381c8d32ea78f70e3f3be441de844cd40bd417aed3315878; LF execution/clone SHA256 is 835b428c894d4e6cdc46957d39a854325138868858a3d864928e498dcae83391. These are explicitly different identities, not mislabeled as equal raw sources.

Payloads are never normalized. `.gitattributes` marks DR exchange and logging-definition.json -text. Both Windows reviewer checkout and LF clone preserve the raw behavior definition SHA256 5f5cfad990ee6a10c4c92e285c7fc93182a94383f51d6587f8f8f2d17be08be2, matching the protocol. Request bytes likewise agree. `tooling/library/verify_dr.py` checks all captured raw sources, input/model hashes, behavior definition and exact complete saved score/bootstrap outputs. The earlier Windows failure and bounded correction remain preserved, not rewritten as success. Original R1 snapshots retain their explicitly documented LF provenance.

## Integrated and clean-checkout checks

All 14 read-only runner commands pass in the reviewer checkout, without --record: host pip; domain, DGP and ten OPE schema exports; 60 accepted contract tests; 11 artifact groups; 11 DR groups in locked Docker; ledger; locked pip/runtime/artifacts; complete DR replay; old/R1 evidence preservation; locks preservation; accepted domain/DGP/workflow preservation; full-base whitespace. The runner's source determines test counts; individual failures would produce nonzero aggregate exit.

Performed a genuine HTTPS clone with `git -c core.autocrlf=false clone --single-branch --no-local --branch launch/g0-library-20261020 https://github.com/esbraun/REMission.git contracts/artifacts/__pycache__/dr-review/fresh-clone`. Verified exact 142f612, clean status, HTTPS origin, single assigned branch fetch mapping, no alternates, and failed object lookups for unpublished c239dca/8315ee9. Source files are observed LF. All 14 commands pass there again with only that clone mounted. No local transport, source overlay or unpublished dependency was used.

Reviewer-only invocation corrections: the first independent script invocation omitted PYTHONPATH and failed import before any candidate code ran; setting PYTHONPATH=/workspace resolved it. One exploratory nonexistent proposal path and one Windows wildcard rg argument failed; the actual proposal is library-qualification.md and was read. These are not candidate failures. Source and output files were retained. An initial preservation pass used normal Git filters; final evidence blobs use --no-filters and raw SHA256, so raw byte identity is preserved explicitly.

Evidence manifest Git blob `376fec50de6dda096c20b85ff570b56dec6444de` lists raw SHA256 and raw Git blob IDs for reviewer scripts, both runner logs, numerical/byte outputs and actual stage evidence. Full own raw exchange/source/model outputs remain unchanged in the ignored artifact directory. Preimplementation reference originals remain unchanged.

## Limits and integration disposition

The original actual PyMC/native NUTS, ArviZ/DataTree, BCF, offline RBesT/SBC/WCLS and COBA fixed-IPS observations remain qualified historical API evidence. Original Rhat 1.0277159130972902 and ESS below 400 still fail final G2 thresholds; R warnings remain. No new convergence, repeated SBC, recovery/null, DR misspecification/propensity stress, ESS/clipping bias, MAR correction/MNAR sensitivity, simulator truth, empirical coverage or complete-cohort algorithm experiment is accepted here. G4 must validate the scientifically frozen model/protocol and required scenarios without reducing sample/repetition requirements. G2/G5 must implement actual consumers, role-aware immutable artifacts and access enforcement.

No fresh advisory sweep, complete OS/R source closure or image rebuild was performed. Existing release/license/audit observations remain dated evidence with their limitations. Human-factors, manual accessibility, clinical review and clinical validation remain deferred and separate. No real clinical systems, patients, messages or wearable accounts were used.

**Full G0-LIB: ready_to_ship at 142f61217c850b132c3fcd21f59a5657fd9bbcfa against f11e90536b635a7db08cfed640445bec197a415c.** Root may integrate after applicable checks/dependencies/protections. This does not close G0 overall or any later statistical/application/human gate.
