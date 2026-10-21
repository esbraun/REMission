# Data science software evidence

Revision and access date: 2026-10-19. Role: software capability/method implementation rationale, never quantitative clinical input. Official documentation and maintainer repositories below were inspected for the stated claims. This is not an exhaustive release, security, maintenance or compatibility audit; exact installed versions and license dispositions remain implementation qualification work under LIB-01. Mutable documentation versions are inspected references, not tested dependency pins.

Canonical consumers: [library decisions](../plans/methods/00-library-decisions.md), [Bayesian steps](../plans/methods/01-bayesian-and-borrowing.md), [experiment/support steps](../plans/methods/02-experiments-and-support.md), [validation steps](../plans/methods/03-validation-and-benchmarks.md). Source-to-requirement links below supplement the existing methodological evidence, not replace it.

## sw-pymc

- Citation: PyMC Developers, PyMC sampling API and repository modeling examples, mutable documentation, accessed 2026. [sample API](https://www.pymc.io/projects/docs/en/latest/api/generated/pymc.sample.html); [official model overview](https://github.com/pymc-devs/pymc/blob/main/docs/source/learn/core_notebooks/pymc_overview.ipynb).
- Type/status/locator: official API and source examples; full-text-checked relevant sample parameters, prior/posterior predictive sections; latest/main are mutable. Current stable module documentation also surfaced version 6.3.2; this is not a selected installed version.
- Supports: native and external NUTS selection, chain/seed configuration and predictive sampling. External samplers require continuous sampled models; likelihood/model support must be checked for the chosen backend.
- Limits: supplies probability modeling/inference, not the longitudinal intervention semantics, transport bridge, clinical eligibility or causal identification. Sampling defaults can change; configure explicitly.
- Requirements: LIB-01/03, BAYES-LIB, BAYES-01/02, MEASURE-01, EXP-LIB, BANDIT-LIB.

## sw-stan

- Citation: Stan Development Team, CmdStanPy API reference, inspected version 1.3.0. [API](https://mc-stan.org/cmdstanpy/api.html).
- Type/status/locator: official documentation; full-text-checked sampling/generate_quantities and install_cmdstan parameters.
- Supports: compiled Stan inference, generated quantities from existing fits and documented Windows compiler installation support.
- Limits: another model language/toolchain; no evidence inspected establishes superior speed or accuracy for REMission. Alternative, not an additional required application backend.
- Requirements: LIB-01, BAYES-LIB, LIB-BENCH.

## sw-nutpie

- Citation: PyMC Developers, nutpie documentation, mutable documentation accessed 2026. [Overview](https://pymc-devs.github.io/nutpie/); [PyMC usage](https://pymc-devs.github.io/nutpie/pymc-usage.html); [sampling options](https://pymc-devs.github.io/nutpie/sampling-options.html).
- Type/status/locator: maintainer documentation; full-text-checked overview features, compilation and sample configuration.
- Supports: compiled Bayesian sampling for supported PyMC/Stan models, diagnostics and alternate compilation backends. Overview reports average approximately 2x speed over Stan on posteriordb.
- Limits: upstream benchmark is not a matched comparison on this model/hardware, nor a native-PyMC speed guarantee. Experimental adaptation features are not selected. Model compatibility and posterior accuracy still need project checks.
- Requirements: LIB-01/02, BAYES-LIB, LIB-BENCH.

## sw-numpyro

- Citation: NumPyro Developers, NumPyro documentation and runtime utilities, mutable stable documentation accessed 2026. [Utilities](https://num.pyro.ai/en/stable/utilities.html); [documentation](https://num.pyro.ai/en/stable/).
- Type/status/locator: official API; full-text-checked enable_x64, set_platform, host-device configuration and Predictive. A different numpyro.pyro.ai utilities URL failed; the linked num.pyro.ai page was accessible.
- Supports: explicit 64-bit selection and CPU/device configuration; JAX compilation/vectorization and predictive generation.
- Limits: precision/device/compilation settings matter, some predictive interfaces are experimental, and JIT disables some validation checks. No local acceleration or accuracy comparison was run. Deferred runtime, not an installed dependency.
- Requirements: LIB-01/02, LIB-BENCH.

## sw-arviz

- Citation: ArviZ Developers, ArviZ documentation, inspected stable landing page version 1.3.0. [Documentation](https://python.arviz.org/en/stable/).
- Type/status/locator: official documentation; full-text-checked overview/navigation. Legacy rhat API link redirects to submodule documentation; the older diagnostics index returned 404 during research.
- Supports: maintained ecosystem for Bayesian exploratory analysis and diagnostics; motivates using established diagnostic implementations with the selected backend.
- Limits: this access does not verify a particular PyMC/ArviZ version pair or all diagnostic function signatures. Qualify R-hat/ESS/MCSE, container and plotting APIs against the actual pinned combination. Earlier LOO references are not proof that ordinary row-wise LOO is appropriate for longitudinal outcomes.
- Requirements: BAYES-02, BAYES-LIB, BCF-LIB, LIB-03.

## sw-rbest

- Citation: Weber and RBesT contributors, R Bayesian Evidence Synthesis Tools, inspected documentation version 1.12-0. [Overview](https://opensource.nibr.com/RBesT/); [normal endpoint](https://opensource.nibr.com/RBesT/articles/introduction_normal.html); [robustify](https://opensource.nibr.com/RBesT/reference/robustify.html); [gMAP](https://search.r-project.org/CRAN/refmans/RBesT/help/gMAP.html).
- Type/status/locator: maintainer/CRAN reference documentation; full-text-checked normal-endpoint workflow, parametric mixture/robustification functions and gMAP priors. Overview reports GPL >=3; record redistribution/license implications during qualification.
- Supports: MAP construction for supported endpoints, mixture approximation, weak-component robustification, effective-information and operating-characteristic tools. robustify's weight is the added weak component fraction, unlike the project's informative MAP weight.
- Limits: generic normal/binary/Poisson tools do not validate ordinal-scale conversion or transported conditional effects. Explicit priors/weak scales and original-study lineage remain required. Normal-endpoint operating characteristics are not the complete app's repeated-decision calibration.
- Requirements: BORROW-01, BORROW-LIB, LIB-01/03, LIB-BENCH.

## sw-sbc

- Citation: Modrak, Moon, Kim, Burkner and collaborators, SBC package; associated 2023 Bayesian Analysis method, DOI 10.1214/23-BA1404. [Package documentation](https://hyunjimoon.github.io/SBC/); [reference manual](https://community.r-multiverse.org/SBC/doc/manual.html).
- Type/status/locator: maintainer documentation/reference; full-text-checked quick tour, backends, test quantities, parallelization and thin_ranks guidance. Installation includes development-repository instructions; pin a verified revision.
- Supports: generator/backend separation, rank/ECDF diagnostics, custom backends and derived quantities; dependence-aware rank processing requires explicit settings.
- Limits: no built-in PyMC adapter was verified. Implement a narrow adapter to actual Python fits; absence of detected discrepancy is not proof of correctness. Preserve failed fits and distinguish SBC from fixed-parameter recovery.
- Requirements: BAYES-02, SBC-LIB, VAL-01/03.

## sw-statsmodels

- Citation: statsmodels Developers, WLS and robust covariance API, inspected stable pages labeled 0.15.0. [WLS.fit](https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.WLS.fit.html); [robust covariance](https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.RegressionResults.get_robustcov_results.html).
- Type/status/locator: official documentation; full-text-checked fit arguments, cluster groups, small-sample/df correction and inference options.
- Supports: weighted linear regression and configurable clustered sandwich inference, building blocks for the declared WCLS design and weighted strategy analyses.
- Limits: WLS does not construct causal centering or assignment weights. Generic cluster corrections are not the MRTAnalysis hat-matrix correction. Defaults and asymptotics do not establish coverage under missingness or pooled adaptation. Inspect weighted-score behavior on independent fixtures.
- Requirements: MRT-01, MRT-LIB, SMART-01, EXP-LIB, VAL-02.

## sw-mrtanalysis

- Citation: MRTAnalysis authors, CRAN package reference manual, accessed 2026. [Official manual](https://cran.r-project.org/web/packages/MRTAnalysis/MRTAnalysis.pdf).
- Type/status/locator: official CRAN reference; full-text-checked wcls, printed pages 57-58 (PDF indices 56-57), summary methods and returned analysis quantities. Pin/record the actual package version at installation.
- Supports: continuous-outcome causal excursion-effect WCLS, moderator/control formulas, executed randomization probabilities, availability, numerator probability and hat-matrix small-sample variance correction.
- Limits: package applicability is narrower than all of the app's adaptive/missing-data analyses. Reference coefficient checks do not imply identical SEs across different corrections; no claim of independent validation or production acceptance for this package is made.
- Requirements: MRT-01, MRT-LIB, LIB-BENCH.

## sw-stochtree

- Citation: StochTree contributors, Causal Inference in StochTree, Python API and multiple-chain workflow, mutable documentation accessed 2026. [BCF](https://stochtree.ai/about/bcf.html); [API](https://stochtree.ai/python-api/reference/); [multiple chains](https://stochtree.ai/vignettes/multi-chain.html).
- Type/status/locator: maintainer documentation; full-text-checked BCF model description, Python API index and multichain instructions. Generic python-api root returned an error; linked reference page was accessible.
- Supports: Python BCFModel sampling with compiled tree machinery, forest samples and multiple chains.
- Limits: tree-sampler diagnostics differ from HMC; built-in prediction does not establish longitudinal causal identification. Maintenance/wheel/version compatibility and matching BCF assumptions require implementation qualification.
- Requirements: BAYES-01, BCF-LIB, POLICY-01.

## sw-sklearn

- Citation: scikit-learn Developers, cross-validation and histogram gradient boosting, inspected stable documentation labeled 1.9.1. [Cross-validation](https://scikit-learn.org/stable/modules/cross_validation.html); [HistGradientBoostingRegressor](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingRegressor.html).
- Type/status/locator: official API/user guide; full-text-checked grouped/time-series split sections and regressor early-stopping/validation parameters.
- Supports: grouped and temporal validation components, regularized/flexible predictive models and controlled randomization/early stopping.
- Limits: grouped splitting and chronological splitting separately do not guarantee both protections together. Automatic random validation can leak within-patient/future information. Prediction scores and calibrated probabilities are not causal-effect calibration or a missingness identification assumption.
- Requirements: MISS-01, MRT-LIB, OPE-LIB, LIB-BENCH.

## sw-bandits

- Citation: Vowpal Wabbit contributors; Fidelity MABWiser contributors; David Cortes, contextualbandits. [VW contextual bandits](https://vowpalwabbit.org/docs/vowpal_wabbit/python/latest/tutorials/python_Contextual_bandits_and_Vowpal_Wabbit.html); [MABWiser repository](https://github.com/fidelity/mabwiser); [contextualbandits repository](https://github.com/david-cortes/contextualbandits).
- Type/status/locator: maintainer tutorial/repository readmes; full-text-checked algorithm/usage descriptions, accessed 2026, mutable latest/default branches.
- Supports: existing contextual/online learning implementations; MABWiser documents parallel training/testing and linear Thompson sampling; contextualbandits documents incremental regression/Thompson approaches. VW is a compiled online learning alternative.
- Limits: inspected capabilities do not establish an exact implementation of this project's patient-level Bayesian pooling, action centering, missingness correction and frozen-policy constraints. No speed ranking among these packages was established; VW is an optional comparator, not the hierarchical replacement.
- Requirements: SUPPORT-01, BANDIT-LIB, LIB-01/02.

## sw-ope

- 2026-10-21 qualified-source revision, preserving the original documentation history below: actual COBA8.1.0 fixed stochastic IPS probe succeeds; stock DR lacks external held-out-Q injection. Immutable raw-source anchors are [OpeRewards1501](https://github.com/VowpalWabbit/coba/blob/0abed4d9779d254b0501f8be10632765c1ce718a/coba/environments/filters.py#L1501) and [same-stream nuisance fit1601](https://github.com/VowpalWabbit/coba/blob/0abed4d9779d254b0501f8be10632765c1ce718a/coba/environments/filters.py#L1601); prior1361 anchor is superseded.
- Independent plan review inspected the official [OBP0.5.7 release](https://pypi.org/project/obp/0.5.7/) and [sdist](https://files.pythonhosted.org/packages/5c/c8/3b511884a171091638d00a4255f11a635f33e0600094c255ec820f7a052f/obp-0.5.7.tar.gz), SHA2563060d67fedfcfadf1e7a6f2608987f74412b5eb74d2c567edeb147595c68f2a0. Its declared Python>=3.8,<3.11 stack excludes the qualified3.13 runtime; [Python3.10 EOL](https://devguide.python.org/versions/) occurred2026-10-01. Stock OBP is rejected as the default maintained runtime, not mislabeled archived. Its public external-Q DR mathematical API remains historical source evidence, not a tested modern install or mandatory legacy execution. Full unchanged inspection/limitations are in the [plan report](../implementation/evidence/G0-LIB/R1/plan-review-01.md).
- [DR-EXCEPTION-R1](../implementation/library-qualification.md#dr-exception-r1--proposed-bounded-ope-decision-revision-unaccepted) proposes a narrow project-owned functional with maintained numerical/regression libraries. It remains unaccepted/unimplemented pending independent re-critique; neither this evidence revision nor a source-level formula closes OPE-LIB, MISS-01 or G4 validation.

- Citation: Vowpal Wabbit/COBA contributors, Logged Bandit Data (inspected documentation 8.0.3); Saito and OBP contributors, Open Bandit Pipeline; VW OPE tutorial. [COBA](https://coba-docs.readthedocs.io/en/latest/notebooks/Logged_Bandit_Data.html); [OBP repository](https://github.com/st-tech/zr-obp); [VW OPE](https://vowpalwabbit.org/docs/vowpal_wabbit/python/latest/tutorials/off_policy_evaluation.html).
- Type/status/locator: maintainer documentation/repository; full-text-checked COBA logged evaluation with learn disabled/IPS/DR, OBP estimator list/examples and VW OPE workflow. Mutable documentation accessed 2026.
- Supports: existing logged contextual-policy estimators and experiment reports. OBP includes broader specialist variants; VW also supplies IPS/DR workflows.
- Limits: docs do not establish appropriate clustered/adaptive uncertainty or project-compliant nuisance splits. Check stochastic-target scoring and nuisance customization in the selected COBA release before accepting the adapter. OBP's broad Python statement is not a tested modern dependency-resolution result. No archive/unmaintained status is asserted. VW labels its legacy --eval workflow as nonpreferred when alternatives are available.
- Requirements: OPE-01, OPE-LIB, POLICY-01, LIB-BENCH.

## sw-numerics

- Citation: NumPy Developers, parallel random generation; SciPy Developers, binomtest; statsmodels Developers, statistical inference APIs. [NumPy streams](https://numpy.org/doc/stable/reference/random/parallel.html); [SciPy binomtest](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.binomtest.html).
- Type/status/locator: official documentation; full-text-checked SeedSequence/parallel streams and binomial-test interval interface; mutable stable pages accessed 2026.
- Supports: established independent random-stream and binomial-interval primitives rather than custom PRNG or interval algorithms. SciPy/statsmodels supply numerical/statistical building blocks.
- Limits: build stable keyed stream creation, not shared mutable global generators or scheduling-dependent child assignment. Exact one-sided bounds, paired/cohort bootstrap and correct independent sampling units must be configured explicitly. Pin PRNG/runtime; do not promise cross-platform bitwise MCMC identity.
- Requirements: DGP-01/03, TRUTH-02, VAL-02/03, LIB-BENCH.

## sw-rliable

- Citation: Agarwal and Google Research collaborators, rliable; associated 2021 benchmark-evaluation work. [Official repository](https://github.com/google-research/rliable).
- Type/status/locator: maintainer README; full-text-checked supported stratified-bootstrap intervals, performance profiles, aggregate metrics and examples, accessed 2026, mutable default branch.
- Supports: existing repeated-run reporting and uncertainty tools for comparable benchmark metrics.
- Limits: example game normalization/IQM summaries do not authorize mixing clinical endpoints. Preserve cohort/replicate sampling units, scenario strata and paired dependence. Optional reporting dependency, not a substitute for VAL-02.
- Requirements: VAL-02, POLICY-01, LIB-BENCH.

## sw-longitudinal

- Citation: CausalInference pygformula contributors; EconML contributors, DynamicDML API (inspected documentation 0.16.0). [pygformula](https://github.com/CausalInference/pygformula); [DynamicDML](https://econml.azurewebsites.net/_autosummary/econml.panel.dml.DynamicDML.html).
- Type/status/locator: maintainer repository/official API; full-text-checked parametric g-formula scope and DynamicDML panel/heterogeneity notes, accessed 2026.
- Supports: existing parametric longitudinal g-formula implementation; DynamicDML specifies grouped panel data and uses first-period X for effect heterogeneity.
- Limits: neither is a drop-in for the specified Bayesian longitudinal borrowing model or arbitrary irregular histories. Optional matched comparators only; capability/estimand mismatches can be settled from documentation without synthetic benchmarking.
- Requirements: BAYES-01, VAL-01, LIB-02, LIB-BENCH.
