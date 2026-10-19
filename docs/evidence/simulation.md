# Simulation evidence

Use the [register rules](README.md). Original citations are retained; verification status is not upgraded by migration.

## stan-checks

- **ID:** `stan_checks`.
- **Citation:** Stan. Posterior predictive checks (including prior predictive checking). Official guide.
- **Type and role:** method, guidance or case study as identified in citation; rationale only.
- **Supports:** the source-specific statements in LEG-16; see the [requirement map](../spec/requirement-map.md).
- **Limits:** retain the population, estimand and setting limits stated in the consuming requirement; no synthetic coefficient is supplied by this entry.
- **Locator:** original citation above; precise section/page and canonical URL require verification unless supplemented below.
- **Verification:** carried forward from 2026-10-04 source list; not independently reverified during this migration.
- **Maintenance:** recheck on claim/method change and before a release relying on this source.

## sbc

- **ID:** `sbc`.
- **Citation:** Stan. Simulation-based calibration. Official guide.
- **Type and role:** method, guidance or case study as identified in citation; rationale only.
- **Supports:** the source-specific statements in LEG-16; see the [requirement map](../spec/requirement-map.md).
- **Limits:** retain the population, estimand and setting limits stated in the consuming requirement; no synthetic coefficient is supplied by this entry.
- **Locator:** original citation above; precise section/page and canonical URL require verification unless supplemented below.
- **Verification:** carried forward from 2026-10-04 source list; not independently reverified during this migration.
- **Maintenance:** recheck on claim/method change and before a release relying on this source.

## sim-ademp

- **ID:** `sim-ademp`.
- **Citation:** Morris TP, White IR, Crowther MJ. Using simulation studies to evaluate statistical methods. Statistics in Medicine. 2019;38:2074–2102.
- **Canonical URL:** [sim-ademp](https://doi.org/10.1002/sim.8086).
- **Type:** Methodological tutorial. **Role:** method/rationale or contextual example; no synthetic quantitative input.
- **Supports:** ADEMP design, Monte Carlo uncertainty, explicit failures and reproducible simulation reporting.
- **Limits:** Simulation conclusions are conditional on the chosen DGPs; this source does not prescribe project thresholds.
- **Requirements:** VAL-01, VAL-02; see [map](../spec/requirement-map.md).
- **Locator/version:** Sections 3–6; performance measures and Monte Carlo SEs.
- **Verification:** full-text-checked, 2026-10-19 design review.
- **Maintenance:** recheck on relevant change and before release reliance.

## sim-check

- **ID:** `sim-check`.
- **Citation:** White IR, Pham TM, Quartagno M, Morris TP. How to check a simulation study. International Journal of Epidemiology. 2024;53(1):dyad134; online 2023.
- **Canonical URL:** [sim-check](https://doi.org/10.1093/ije/dyad134).
- **Type:** Methodological guidance. **Role:** method/rationale or contextual example; no synthetic quantitative input.
- **Supports:** Use well-understood cases, inspect generated data and diagnose anomalous/failed estimates.
- **Limits:** Agreement in simple cases does not certify a rich clinical simulator.
- **Requirements:** DGP-01, TRUTH-02; see [map](../spec/requirement-map.md).
- **Locator/version:** Key messages and simulation design/conduct/checking sections.
- **Verification:** full-text-checked, 2026-10-19 design review.
- **Maintenance:** recheck on relevant change and before release reliance.

## sbc-talts

- **ID:** `sbc-talts`.
- **Citation:** Talts S, Betancourt M, Simpson D, Vehtari A, Gelman A. Validating Bayesian Inference Algorithms with Simulation-Based Calibration. 2018. arXiv:1804.06788.
- **Canonical URL:** [sbc-talts](https://arxiv.org/abs/1804.06788).
- **Type:** Methodological preprint. **Role:** method/rationale or contextual example; no synthetic quantitative input.
- **Supports:** Prior-predictive simulation and posterior ranks can diagnose Bayesian computation.
- **Limits:** Requires model-matched generation; does not establish misspecification robustness or clinical validity.
- **Requirements:** BAYES-01, BAYES-02, VAL-03; see [map](../spec/requirement-map.md).
- **Locator/version:** Abstract and SBC algorithm.
- **Verification:** abstract-checked, 2026-10-19 design review.
- **Maintenance:** recheck on relevant change and before release reliance.

## sbc-quantities

- **ID:** `sbc-quantities`.
- **Citation:** Modrák M, Moon AH, Kim S, Bürkner PC, Huurre N, Faltejsková K, Gelman A, Vehtari A. Simulation-Based Calibration Checking for Bayesian Computation: The Choice of Test Quantities Shapes Sensitivity. Bayesian Analysis. DOI published online 2023; volume 20(2):461–488, June 2025.
- **Canonical URL:** [sbc-quantities](https://doi.org/10.1214/23-BA1404).
- **Type:** Methodological paper. **Role:** method/rationale or contextual example; no synthetic quantitative input.
- **Supports:** Data-dependent quantities such as joint likelihood improve sensitivity to ignored observations.
- **Limits:** Parameter-only ranks can miss failures; no finite diagnostic proves absence of all bugs.
- **Requirements:** BAYES-02, VAL-03; see [map](../spec/requirement-map.md).
- **Locator/version:** Test-quantity discussion; accessible author text https://arxiv.org/html/2211.02383v3.
- **Verification:** full-text-checked, 2026-10-19 design review.
- **Maintenance:** recheck on relevant change and before release reliance.

## stan-diagnostics

- **ID:** `stan-diagnostics`.
- **Citation:** Stan Development Team. How to Diagnose and Resolve Convergence Problems. Official documentation, mutable.
- **Canonical URL:** [stan-diagnostics](https://mc-stan.org/learn-stan/diagnostics-warnings.html).
- **Type:** Official documentation. **Role:** method/rationale or contextual example; no synthetic quantitative input.
- **Supports:** Four chains, R-hat below 1.01, adequate ESS and estimand-specific Monte Carlo precision for final inference.
- **Limits:** Diagnostics do not establish causal identification; recheck current documentation at implementation.
- **Requirements:** BAYES-02; see [map](../spec/requirement-map.md).
- **Locator/version:** R-hat, ESS, divergences and numerical precision sections; accessed 2026-10-19.
- **Verification:** full-text-checked, 2026-10-19 design review.
- **Maintenance:** recheck on relevant change and before release reliance.
