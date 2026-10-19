# Industry evidence

Use the [register rules](README.md).

## netflix-artwork

- **ID:** `netflix-artwork`.
- **Citation:** Netflix Technology Blog. Artwork Personalization at Netflix. 2017.
- **Canonical URL:** [netflix-artwork](https://netflixtechblog.com/artwork-personalization-c589f074ad76).
- **Type:** Company engineering case study. **Role:** method/rationale or contextual example; no synthetic quantitative input.
- **Supports:** Contextual artwork selection with logged exploration and offline replay.
- **Limits:** Replay assumptions do not transfer unchanged to longitudinal clinical outcomes; no clinical efficacy claim.
- **Requirements:** OPE-01; see [map](../spec/requirement-map.md).
- **Locator/version:** Performance evaluation: Offline and Online.
- **Verification:** full-text-checked, 2026-10-19 design review.
- **Maintenance:** recheck on relevant change and before release reliance.

## netflix-hte

- **ID:** `netflix-hte`.
- **Citation:** Seyfarth S et al., Netflix Technology Blog. Heterogeneous Treatment Effects at Netflix. 2025.
- **Canonical URL:** [netflix-hte](https://netflixtechblog.medium.com/heterogeneous-treatment-effects-at-netflix-da5c3dd58833).
- **Type:** Company experimentation case study. **Role:** method/rationale or contextual example; no synthetic quantitative input.
- **Supports:** Evaluate incremental personalization value over a global winning option.
- **Limits:** Large product experiments differ from sparse clinical trajectories.
- **Requirements:** POLICY-01; see [map](../spec/requirement-map.md).
- **Locator/version:** Policy Learning and Personalization.
- **Verification:** full-text-checked, 2026-10-19 design review.
- **Maintenance:** recheck on relevant change and before release reliance.

## microsoft-srm

- **ID:** `microsoft-srm`.
- **Citation:** Fabijan A et al., Microsoft Experimentation Platform. Diagnosing Sample Ratio Mismatch in A/B Testing. 2020-09-14.
- **Canonical URL:** [microsoft-srm](https://www.microsoft.com/en-us/research/articles/diagnosing-sample-ratio-mismatch-in-a-b-testing/).
- **Type:** Company experimentation guidance. **Role:** method/rationale or contextual example; no synthetic quantitative input.
- **Supports:** Assignment, execution, logging and analysis faults can invalidate experiment interpretation.
- **Limits:** Adaptive checks must use executed conditional probabilities, not an assumed constant 50/50 split.
- **Requirements:** SUPPORT-01, S32; see [map](../spec/requirement-map.md).
- **Locator/version:** How widespread are SRMs; diagnosis and triggering sections.
- **Verification:** full-text-checked, 2026-10-19 design review.
- **Maintenance:** recheck on relevant change and before release reliance.

## recsim

- **ID:** `recsim`.
- **Citation:** Mladenov M, Hsu CW, Google Research. RecSim: A Configurable Simulation Platform for Recommender Systems. 2019-11-19.
- **Canonical URL:** [recsim](https://research.google/blog/recsim-a-configurable-simulation-platform-for-recommender-systems/).
- **Type:** Company research case study. **Role:** method/rationale or contextual example; no synthetic quantitative input.
- **Supports:** Configurable sequential environments permit investigation of cumulative policy effects.
- **Limits:** Stylized simulations are not high-fidelity clinical validation.
- **Requirements:** DGP-01, OPE-01; see [map](../spec/requirement-map.md).
- **Locator/version:** Overview and applications.
- **Verification:** full-text-checked, 2026-10-19 design review.
- **Maintenance:** recheck on relevant change and before release reliance.

## rliable

- **ID:** `rliable`.
- **Citation:** Agarwal R, Schwarzer M, Castro PS, Courville A, Bellemare MG. Deep Reinforcement Learning at the Edge of the Statistical Precipice. NeurIPS. 2021.
- **Canonical URL:** [rliable](https://arxiv.org/abs/2108.13264).
- **Type:** Methodological paper and official research blog. **Role:** method/rationale or contextual example; no synthetic quantitative input.
- **Supports:** Uncertainty-aware repeated-run comparisons and distributional performance reporting.
- **Limits:** Deep-RL benchmark aggregation is not a clinical composite outcome; resample independent cohort runs here.
- **Requirements:** VAL-02, POLICY-01; see [map](../spec/requirement-map.md).
- **Locator/version:** Official explainer https://research.google/blog/rliable-towards-reliable-evaluation-reporting-in-reinforcement-learning/ ; uncertainty and bootstrap discussion.
- **Verification:** full-text-checked, 2026-10-19 design review.
- **Maintenance:** recheck on relevant change and before release reliance.
