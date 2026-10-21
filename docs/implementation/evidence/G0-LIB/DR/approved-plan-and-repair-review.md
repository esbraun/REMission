# Independent G0-LIB-R1 repair review and DR-EXCEPTION-R1 plan critique

Date: 2026-10-21. Two scoped dispositions:

1. **DR-EXCEPTION-R1 plan: ready_to_proceed** with the bounded implementation specified in the reviewed proposal. The prior plan findings are resolved. This is approval to implement and qualify that plan, not acceptance of an unimplemented estimator or statistical results.
2. **Artifact/library repair implementation: accepted within the reviewed repair scope.** The two original blocking implementation findings are resolved, with no new blocking finding identified. **Full G0-LIB is not ready_to_ship**: mandatory DR implementation, actual qualification probes and independent exact-head review remain unexecuted. G0 overall and application/statistical/human gates remain unfinished.

Exact reviewed head: `d84203709b0164a0824913950c1d7cd7be25a2fb`.
Exact accepted main base and observed merge-base: `f11e90536b635a7db08cfed640445bec197a415c`.
Exclusive detached checkout: `C:/Users/erics/Documents/Projects/REMission-worktrees/g0-library-r1-review-20261021`.
Reviewer task: `/root/dgp_r2_critic_astra`; CODEX_THREAD_ID `01a15ec2-f67d-7522-9ade-45b236fd41bc`.
Requested configuration: `gpt-6-astra` / `medium`. Explicit assignment is observed; independent effective-model/effort introspection is unavailable. No substitution, escalation or helper was used.

## Scope, isolation and preserved history

Verified root, detached exact HEAD, accepted base ancestry and initially clean tracked/untracked state before reading or executing candidate code. All commands used explicit workdir. No other live checkout was accessed. My previous DGP review worktree was preserved; only its already-created pinned contract Python environment was reused as an interpreter/dependency environment, as authorized. Source imports and checks ran against this new checkout or its own fresh HTTPS clone. Docker mounts used only this checkout/clone and this checkout's ignored review artifacts. No author worktree or source overlay was used.

Read both complete original raw reports through Git: plan `052677a20145fb14f5e1d2f509592a4de4942ef4` and implementation `113f4f258a94ba9cc7fccce4b5fbb74bf0a72a49`. Their committed R1 copies hash to those exact blobs. Read bounded LIB-01/02/03, OPE-LIB, OPE-01, MISS-01, VAL-02/03, software evidence, G0-LIB ledger/profile, current proposal and affected artifact/lineage/runner/probe source and evidence. The established entry/index/runtime/delegation/engineering/scope context remains applicable from the preceding review; current task/base/source requirements were checked locally. An initial combined read was truncated; the omitted beginning of the original plan report was read separately. No whole-package load or library tournament was undertaken.

All original G0-LIB evidence outside additive R1 is unchanged against `d9ad54e899b2f38b286bd100aff037625edf160b`. This preserves the wrong original producer/input manifests as historical failed claims, original API observations, raw warnings, source records, rejected dependency/probe attempts and draw artifacts. Accepted domain/DGP/workflow sources and tests are unchanged against f11e905. Python/R Dockerfiles and dependency locks are unchanged against d9ad54e. The read-only runner verifies these preservation boundaries. R1's initial whitespace failure and pre-PR13 successful capture remain separate historical evidence.

Only this new untracked report and ignored files under `contracts/artifacts/__pycache__/r1-review/` were written. No candidate source edit, staging, commit, PR or merge occurred.

## Implementation finding resolution

### Original P2 CSV arity and missing patient identity: resolved

Locations: `contracts/artifacts/manifest.py:169-173` CSV parsing/exact keys and missing-field guard; `:193` Identifier validation; `:210` dispatch boundary; `tests/library/test_artifacts.py:test_review_extra_short_rows_and_patient_identity_reject_before_worker`.

The new exact-row check rejects DictReader's surplus-field None key and short-row None values. Expected header validation still rejects wrong/duplicate columns. WCLS patient IDs are validated with the existing nonempty string Identifier contract before returning rows; they are not numerically coerced.

Independently loaded the historical manifest module from `git show d9ad54e:contracts/artifacts/manifest.py` into an ignored reviewer file. Using real validated requests/manifests and correctly rehashed malicious bytes, reproduced all three original failures: one draw row with an extra field, one WCLS row with an extra field, and a WCLS row with blank ID each returned `done` and invoked the worker once. The identical compositions against R1 raise ContractViolation with zero worker calls.

Essential reproduction bytes (the manifest payload SHA256 must be recomputed after changing bytes):

```text
chain,draw,quantity,value
0,0,mu,1.2,extra

id,time,y,action,logging_probability,numerator_probability,availability,x
P1,0,3,1,.5,.5,1,2,extra

id,time,y,action,logging_probability,numerator_probability,availability,x
,0,3,1,.5,.5,1,2
```

Additional independent compositions reject short draws/WCLS rows, malformed UTF-8, nonfinite values/probabilities, whitespace/tab patient IDs and duplicate patient-time decisions with zero calls. Valid IDs `001` and `1` at the same time remain two distinct strings and pass. A valid first artifact followed by a malformed second artifact also invokes no worker: validation is completed for the whole batch before dispatch. These checks exercise the public boundary rather than monkeypatching validation or asserting only schema construction.

### Original P2 wrong producer/direct input lineage: resolved

Locations: `tooling/library/lineage.py:15-58`, `tooling/library/wcls_fixture.py`, `prepare_exchange_r1.py`, `probe-offline.R:55-57` and `:73-80`, and seven R1 exchange manifests.

The historical WCLS manifest still identifies the R image, reproducing the prior finding. The R1 WCLS input now identifies the actual Python dependency image, deterministic WCLS generator source and explicit definition; its direct inputs do not include unrelated normal-normal fit/draw files. The separately typed R WCLS result identifies the R producer, exact WCLS input and analysis byte hashes, coefficient names and its distinct variance convention. Mixture artifacts identify their actual fixed R recipe/source, not PyMC draws or a gMAP-derived prior. SBC lineage identifies the historical PyMC source/draw bytes and current R transformation.

Independently ran the actual Python generator in the locked Python image; its 72-row output is byte-identical to R1 wcls-input.csv. Independently ran the actual revised R CLI on the committed R1 inputs, writing solely into reviewer-owned ignored output. It passed real RBesT native/project JSON roundtrips, SBC import/conversion and MRTAnalysis WCLS. All seven relevant returned payload/analysis files (four mixtures, SBC return, WCLS analysis, WCLS result) are byte-identical to the committed R1 versions. The actual SBC matrix is now checked against chain-major source values and its values are exported; the original CSV echo weakness is addressed.

Observed WCLS coefficients are approximately `[0.99995814199918587, 0.19844325809964478, 1.99959764799069450]`. The 800 SBC coordinates/values are preserved at the specified 1e-12 tolerance. Python/R coefficient agreement remains separate from variance agreement: MRTAnalysis's hat-matrix correction and statsmodels' cluster correction are explicitly different. No repeated SBC calibration, final WCLS variance validation, mixture approximation quality or clinical prior claim follows.

Independent newline-byte mutations to WCLS generating source or R mixture source fail dispatch against accepted manifests and fail recipe reconstruction with stale source hashes. Artifact hashing correctly does not normalize those bytes. Author lineage tests additionally demonstrate corresponding definition/source hash changes while unrelated mixture identity stays fixed. Rehashed WCLS result payloads with wrong input hash, wrong analysis hash or incompatible units reject before worker calls. The new stored manifests reconstruct exactly from the source-specific builder.

This remains a narrow qualification mapping, not authentication. A flat accepted VersionRef set is not a role-aware immutable artifact catalog, and matching checksums do not prove a claimed producer executed. Actual G2/G5 consumers must require the correct accepted artifacts/configurations/transform roles and enforce source/process access. Those limits are explicitly retained rather than claimed solved by this helper.

## DR-EXCEPTION-R1 plan critique

Reviewed proposal: `docs/implementation/library-qualification.md:33-66`, linked coherent revisions in LIB-01, OPE-LIB and sw-ope. **ready_to_proceed for plan only.** No additional unresolved design choice blocks its bounded implementation. The implementation must turn the proposal's acceptance criteria into observed results before full G0-LIB review.

The original three plan concerns are addressed:

- Stock OBP 0.5.7 is explicitly rejected as the default maintained runtime, while its historical mathematical source remains available. No legacy Python container, relaxed pins, patched metadata or default installation is required. Independently verified the committed 1,306,068-byte primary sdist SHA256 `3060d67fedfcfadf1e7a6f2608987f74412b5eb74d2c567edeb147595c68f2a0` and read its declared Python `>=3.8,<3.11` from the archive without extraction/import/execution. The earlier primary-source maintenance/EOL observations are preserved historical evidence; this review does not claim a fresh vulnerability audit or exhaustive current maintainer search.
- The revised decision concretely names ownership, target aggregation, external-Q provenance, warm-up, missing-reward behavior, independent-unit guard and uncertainty regime. It promotes the already-proposed narrow project-owned functional, not a new framework or backend. Maintained NumPy and scikit-learn remain numerical/regression dependencies; PyMC remains the sole live Bayesian backend.
- COBA source anchors are corrected. Independently inspected the actual locked COBA installation: OpeRewards starts at line 1501, internal `vw.learn` is at 1601, and its signature has no external-Q argument. COBA fixed stochastic IPS remains historical qualified evidence; stock held-out DR remains rejected. Optional transport is omitted, avoiding any suggestion that transporting project-computed scores makes them built-in COBA DR.

### Functional and target coherence

The proposed ordinary score is `sum_a pi[a]*Q[a] + pi[A]/p[A]*(R-Q[A])`, with ordinary IPS `pi[A]/p[A]*R`. Both actions are integrated exactly. The target and Q are fixed before scoring; no target sampling, learning, fitting, self-normalization or silent clipping/renormalization occurs there. This is a contextual intervention on the current eligible action over the behavior-generated observed-history distribution, not the history distribution induced by a long-run target policy.

Independent rational example: row 1 has A=0, p=1/4, pi=(1/3,2/3), Q=(1,3), R=2, yielding DR=11/3. Row 2 has A=1, p=3/4, pi=(1/2,1/2), Q=(2,4), R=1, yielding DR=1. The two-row mean is7/3. If patient 1 contributes two copies of row 1 and patient 2 one row 2, the specified pooled eligible-decision mean is25/9, whereas the unrequested equal-patient mean is7/3. This independently confirms the denominator distinction and exact stochastic action integration. It is reviewer algebra, not execution of a proposed production estimator.

The frozen roster includes every prespecified eligible window, with at most one contributing decision per daily outcome. Unavailable windows are counted separately; no eligible windows is undefined/abstained. Any missing/pending/undefined eligible reward causes abstention for this ordinary complete-reward functional, rather than post-hoc row deletion or zero insertion. That is a valid narrow initial API boundary because the proposal explicitly leaves the mandatory MAR observation correction and MNAR sensitivities to separate G4 acceptance; it does not elevate complete-case analysis to the primary missingness method.

Availability and support rules correctly exclude target mass on unavailable/unsupported actions and factual unavailable actions. Deterministic one-action data are admitted only with compatible probability-one target/logging and are not mislabeled a randomized two-action contrast. Implementation must carry enough authoritative logging/eligibility information to establish support for every target action, not infer support solely from the observed action's scalar propensity. This is an implementation consequence of the already explicit support rule, not a missing new estimator choice.

### Held-out nuisance and uncertainty coherence

The training-only cohort is disjoint from all evaluation patients; F0 precedes the first evaluation decision; training features predate their own assignments and training rewards predate F0. This stricter single held-out split satisfies the patient/forward-time boundary without needing a general fold framework. Offline prediction time may be later, but only with a sealed earlier model and predecision histories in a reward-blind process. Actual source access and immutable manifests must enforce this; self-declared metadata alone cannot establish it.

The proposed real Ridge API probe, fixed finite basis/action interactions and at least ten training patients under each action are suitable provisional plumbing checks. They are not sufficient scientific model/coverage validation. The consumer must freeze exact basis, transformations, regularization, seed and feature/action mapping before its run. Training-only warm-up or explicit abstention prevents filling early folds with future/evaluation patients.

For inference the proposal conditions on sealed target/nuisance/training artifacts, requires at least 30 independent evaluation patients, and uses 2,000 patient bootstrap replicates. Resampling whole patient score sums and counts and recomputing their ratio preserves the declared eligible-decision weighting with unequal lengths. Shared sampled patients preserve paired policy comparisons. Holding nuisance fits fixed is consistent with the explicitly conditional claim; unconditional training-sample uncertainty or nuisance refitting is not silently claimed. The 30/2,000 defaults are engineering guards awaiting G4 coverage validation, not a theorem, and they do not reduce n60/n240 or mandatory simulation repetitions.

The proposal limits patient-level inference to independent evaluation patients under a frozen nonpooled logger or an independently justified equivalent. It explicitly refuses to treat one pooled adaptive cohort as independent patients. Full learning-algorithm comparisons retain independent complete-cohort runs and paired cohort uncertainty under VAL-02. This resolves the prior variance/dependence ambiguity without pretending contextual DR establishes distal ISI, habituation/delayed-harm or adaptive algorithm value.

### Required next qualification, not waived

Root may assign the bounded implementation: strict inputs/results/provenance, pure two-action score/aggregate, conditional patient uncertainty and real maintained-runtime probes. Independent source/runtime/artifact review must follow. Acceptance includes rational per-row/aggregate fixtures; Q=0/zero residual/deterministic/zero factual target cases; real earlier-disjoint Ridge Q; reward mutation without target/Q/training mutation; zero scorer fit/learn/sampled-predict calls; corrupted patient/time/row/action/source hashes and probabilities rejected before work; missing reward/absent training/insufficient independent units; unequal-length patient and paired-bootstrap checks with independent numerical references and fixed seeds.

G4 still owns misspecified-Q/correct-propensity behavior, propensity corruption, support/heavy-weight/ESS and clipping-bias checks, missingness correction/sensitivity, contextual simulator truth, coverage/null/recovery, delayed effects and complete-cohort algorithm evaluation. The implementation must compare contextual scores to a matching behavior-history current-action truth; a target-policy trajectory value would be a different estimand. These obligations remain in the proposal and canonical requirements.

## Observed checks and clean reproduction

Inspected source, Dockerfiles, retained image configs and runner before execution. Reused only the reviewer's pinned Python 3.13.7 contract environment, with requirements-contracts.txt packages already installed; no redundant package install. The first Docker inspect format requested a missing Entrypoint key and returned a formatting error; a corrected full Config inspection succeeded. This was an inspection-command correction, not a failed dependency/runtime probe.

Executed without `--record`:

```text
<own-pinned-contract-python> docs/implementation/evidence/G0-LIB/R1/run_checks.py
<own-pinned-contract-python> contracts/artifacts/__pycache__/r1-review/adversarial.py
```

All ten runner checks pass: contract-environment pip consistency; domain export; DGP export; all 60 accepted contract tests; all 11 artifact/lineage groups; ledger; locked Docker pip/runtime/artifact schemas/manifests; original evidence preservation; accepted source preservation; full-base whitespace against f11e905. Independent adversarial results are detailed above.

Dependency-only Docker images used:

- Python `sha256:be4bbf7978bb318b8c3d2901e8e9510b746aa8554d5c0dbfc8eea5928d9f07f7`.
- Offline R `sha256:2d24b2af23795f11935fd917486dd132c708f2d22e90cf706d540bcd647100d5`.

Python runtime inventory equals the committed qualified distribution map. The actual R bridge reports R 4.5.2, RBesT 1.12.0, SBC 0.5.0.0, MRTAnalysis 0.4.1, posterior 1.7.0 and rstan 2.32.7. Source was mounted read-only at `/workspace`, and only the new review artifact directory was mounted writable at `/review`. R invocation was `Rscript tooling/library/probe-offline.R /workspace/docs/implementation/evidence/G0-LIB/R1/exchange /review/r-return`. The actual deterministic Python fixture probe wrote `/review/reproduced-wcls.csv` and compared it byte-for-byte to committed input.

Performed a genuine HTTPS single-branch clone:

```text
git clone --single-branch --no-local --branch launch/g0-library-20261020 https://github.com/esbraun/REMission.git contracts/artifacts/__pycache__/r1-review/fresh-clone
```

Verified exact d84203709b0164a0824913950c1d7cd7be25a2fb, clean status, HTTPS origin and only the assigned branch fetch mapping. No `.git/objects/info/alternates`; c239dca and8315ee9 commit object lookups both fail. No source overlay, local reference/alternates, object copying or unpublished dependency was used. Ran the complete R1 runner from that clone with the same dependency-only interpreter and clone-only Docker mount: all ten checks pass again. Committed evidence was never overwritten.

Unchanged expensive native-NUTS, gMAP/automixfit and BCF fits were not rerun. Their previous independent API observations remain historical evidence. The original native-NUTS Rhat 1.0277159130972902 and ESS values below 400 still fail final G2 thresholds; RBesT warnings likewise remain. No new convergence, recovery, repeated SBC, security audit, complete image/source rebuild or statistical qualification claim is made. Container apt closure and full R source closure remain the previously documented reproducibility limits.

## Final scope and integration instruction

**DR-EXCEPTION-R1: ready_to_proceed, plan only. Artifact/library repairs: accepted within this reviewed scope, prior blocking defects resolved. Full G0-LIB: incomplete and not ready_to_ship pending actual DR qualification and refreshed independent review.**

Root alone assigns the accepted-plan implementation and manages integration. A changed candidate head or target base requires refreshed review and affected checks. G0 overall, G1-G7 statistical/application gates, actual service consumer/provenance/access enforcement, human-factors/manual accessibility, clinical review and clinical validation retain their unfinished status. Human/clinical review remains explicitly deferred and is not being manufactured by agent approval. No real clinical systems, patients, messages, orders or wearable accounts were involved.
