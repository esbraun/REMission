# Library validation and selective DGP benchmarks

**Immediate PoC precedence (2026-10-22):** the [PoC amendment](../../spec/poc-amendment-20261021.md) controls active scope, sequencing and acceptance over conflicting full-program requirements below. The immediate Google Cloud physician simulation milestone requires POC-CLOUD-01 through POC-CLOUD-05, POC-1 through POC-3 and the workflow/persistence/failure portions of POC-6. Training/fitting, POC-4/5, fitted protocol representatives, APPT-01–05 and POC-VAL remain later analytics acceptance; retain relevant invariants and independent review. Exhaustive G0-G7 counts, deferred engines and human/clinical gates are later work, not prerequisites for synthetic PoC operation. Existing historical evidence retains its original scope.

Revision: 2026-10-19. Future work only; no benchmark, fit or statistical validation has been executed by this revision. Read the [validation protocol](../../spec/07-validation-protocol.md) and [library decisions](00-library-decisions.md).

## LIB-BENCH — Evidence triage

For every material library/algorithm choice, record: decision to resolve, candidate/default, relevant published or official evidence, applicability to the project's estimand/data/runtime, unresolved uncertainty and disposition. Use `evidence-sufficient`, `targeted-benchmark-planned`, `deferred-optional` or `unsupported` as selection statuses; these are not G0-G7 acceptance statuses.

Do not benchmark when direct evidence already resolves the choice. Examples: PyMC supports required probability models; RBesT already supplies robust mixture construction; DynamicDML's documented data restrictions exclude some proposed comparisons. Do not repeat generic library feature or throughput contests on synthetic data without a project decision they could change.

Use synthetic DGP benchmarks where existing evidence leaves a consequential gap. Distinguish conditional performance claims from library maturity: upstream nutpie performance is reason to try it, not evidence of REMission speed; an established WCLS formula does not establish finite-sample coverage with these missingness patterns.

| Decision or uncertainty | Planned evidence | Disposition |
|---|---|---|
| Primary Bayesian modeling framework | Official PyMC model/sampling capability; Python architecture and one-backend requirement | Evidence sufficient for selection; no PyMC-vs-Stan tournament |
| Robust prior software | RBesT normal-endpoint/robust mixture documentation | Evidence sufficient for selection; imported artifacts and project bridge still require validation |
| Diagnostic/regression/numerical primitives | Official ArviZ, statsmodels, NumPy/SciPy/scikit-learn APIs | Evidence sufficient; analytic seam checks, not broad competing-library benchmarks |
| nutpie acceleration | Same PyMC likelihood/prior, explicit settings and matched input sizes | Targeted future pilot; compare time to acceptable precision, not draws/second alone |
| Ordinal/borrowing bridge approximation | Independent source/target standardization truth, weak/robust/complete borrowing and existing conflict cells | Required project validation; no assumption that established MAP tools validate the bridge |
| WCLS covariance and observation weights | Existing analytic fixtures and coverage cells at 60/240 participants; MRTAnalysis reference | Required project validation; no blanket ranking of statsmodels vs R |
| Flexible BCF or predictive comparator | Matching estimand/information set, held-out performance and relevant scenario cells | Existing specified comparator work; exclude mismatched longitudinal claims |
| Faster generic bandit | Only if the hierarchical learner's pilot reveals a consequential bottleneck | Deferred optional; compare matched constraints and report changed statistical model |
| pygformula, DynamicDML, OBP or offline RL additions | A named unsupported capability or unresolved method question, plus compatibility/estimand review | Deferred optional; do not add a benchmark matrix merely to include every package |

The user explicitly requested future synthetic-DGP benchmarking where useful, no benchmarking now, and no redundant benchmarking where existing evidence is clear. Required implementation validation remains mandatory. No studies are downsized or gates waived through the selection-status table.

## Implementation validation sequence

1. **G0 qualification:** map method requirements to selected APIs and sources. Record accepted package licenses/maintenance/runtime compatibility and the source-to-requirement links. Freeze endpoint coding, analysis bases, artifact schemas and correction choices before dependent work.
2. **G1 foundations:** analytic/enumerable checks for posterior fixtures, ordinal expectations, longitudinal interventions, strategy trees and binary policies. Use independent truth, separate keyed streams and denied oracle access. Verify deterministic replay across worker scheduling on the pinned runtime; do not promise bitwise identity across different numerical platforms.
3. **G2 Bayesian:** validate mixture imports/weight conventions, induced marginal priors, shared-severity measurement, no duplicate likelihoods, derived-quantity diagnostics and actual-backend SBC with seeded faults. Perform recovery and full-scale checks separately from tractable SBC.
4. **G3 experiments:** validate block schedules, AR residual spacing, carryover/rebound, frozen support, SMART path products and strategy covariance. Compare exact enumeration before complex scenarios.
5. **G4 support:** verify WCLS coefficients/variance choices, MAR/MNAR handling, final propensities, bounded sampling frequencies and immutable frozen policies. Validate contextual IPS/DR against known values and report support failures. Distinguish pooled adaptation from independent-participant inference.
6. **G5 integration:** consume accepted saved results, retain interval type/units/cutoff/version and expose failed, pending, undefined, inconclusive and prior-only states. No fabricated success when optional dependencies or offline artifacts are absent.
7. **G6/G7:** preserve locked confirmatory protocols, independent seeds, raw failure counts and paired cohort comparisons; reproduce from a clean checkout with actual commands, lockfiles, artifact checksums and supported-region limitations.

## Runtime pilot and benchmark design

Retain VAL-01's 20-fit runtime/storage pilot before expensive suites. It is resource planning, not mandatory comparison of every library. Select the representative supported full-scale workload before running; cover relevant variation in fit size/geometry through a documented allocation. Measure total projected cost for the locked repetition budget and preserve checkpoint/resume instructions.

For an additional library comparison, freeze the question, candidates, estimand, workload/cells, precision target, configuration, seeds, hardware/runtime and resource cap before timing. Start from the selected stack and add only the alternative needed to resolve that question. Choose replicate allocation from the paired pilot's variability and the decision precision required; record it before any confirmatory performance claim. Never treat a 20-fit timing pilot as proof of statistical equivalence.

Measure cold startup/compilation, warm fitting, posterior rollouts, diagnostics, artifact writing, peak resident memory, storage and accepted-fit yield. Report end-to-end time and estimand-specific ESS/second or time to required MCSE. Include failures and tuning costs; distinguish serial latency from total parallel throughput. Fix thread/process limits to avoid oversubscription and record cache/device/BLAS conditions.

Use identical datasets and matched targets for paired method comparisons. Keep fit randomness independent where appropriate and retain paired DGP/truth keys. Report bias, RMSE, empirical variation, interval width/coverage, false direction/meaningful superiority, abstention, support/missingness, reward/burden and constraint violations separately. A faster run that fails the existing numerical or statistical gates is not an eligible replacement.

Promote nutpie only for compatible models after analytic agreement, acceptable diagnostics and posterior contrasts/probabilities consistent within combined numerical error; verify any decision discrepancy with additional precision before disposition. Require improved measured time to accepted precision on the relevant workload, including cold cost when compilation is not amortized. Otherwise retain native NUTS. Backend changes create a versioned configuration and invalidate affected downstream evidence.

## Uncertainty and artifacts

Use SciPy/statsmodels routines for Wilson and exact binomial bounds; explicitly request the appropriate one-sided exact bound for zero failures and null-superiority acceptance. Use existing independent-replicate MCSE formulas. Bootstrap paired method differences over independent replicate/cohort units, preserving scenario strata; never bootstrap patient-night rows as independent complete algorithm runs.

scikit-learn grouped and time-based splitters are building blocks, not a combined leakage guarantee. Construct and audit patient-held-out, chronological and site-shift splits explicitly. Fit transformations and nuisance models only on allowed training data; disable or replace automatic random early-stopping splits where they violate chronology/grouping.

rliable is optional reporting for comparable repeated-run metrics, not a new acceptance system. Preserve raw per-scenario outcomes and failure statuses. Do not normalize incompatible clinical endpoints into one benchmark score or lose paired dependence through a default reporting routine.

Each manifest records selection disposition and sources; protocol/scenario/DGP/estimand/prior/model versions; actual packages/sampler and hardware; independent seeds and splits; attempted/completed/failed counts; draws/diagnostics/numerical uncertainty; truth precision; per-replicate results; timing/memory/storage; commands; checksums; and the exact decision supported. Evidence-only decisions name their applicable source instead of inventing a benchmark result.

Preserve the current 5/200/1,000/2,000 tier rules, all mandatory catalog cells, acceptance thresholds and separate human/clinical gates. Changed post-confirmation choices require a new protocol and fresh confirmation seeds. Lack of resources leaves the relevant gate incomplete.
