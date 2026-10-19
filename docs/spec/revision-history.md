# Revision history

## October 19 2026 data science library planning

Added the [methods implementation sequence](../plans/methods/00-library-decisions.md) and [software evidence register](../evidence/software-libraries.md), comparing speed mechanisms, statistical accuracy limits, built-in evaluation and alternatives. Selected PyMC/native NUTS with compatible ArviZ, NumPy/SciPy, statsmodels, scikit-learn, StochTree and offline COBA; RBesT, SBC and MRTAnalysis run offline. nutpie is a gated accelerator. Narrowed the formerly open PyMC-or-Stan application choice to PyMC; no public API migration or dependency installation occurred.

Recorded RBesT informative/weak-weight translation, marginal bridge checks, actual-Python-backend SBC, WCLS correction differences, N-of-1/SMART steps, leakage-safe nuisance training and hierarchical policy/OPE reuse boundaries. Canonical component requirements, worker reading bundles and gate mapping now link these steps.

Per user direction, synthetic-DGP benchmarks are future work only for material choices unresolved by applicable existing evidence. Clear evidence can settle library selection without a new bake-off. Existing mandatory analytic, SBC, recovery, null, policy, runtime-pilot and reproduction requirements remain intact. No application implementation, package qualification/install, benchmark, fit, simulation or clinical/human-factors validation occurred in this documentation revision.

## October 19 2026 engineering and skills refinement

Installed three pinned vercel-labs/agent-skills packages and added [canonical engineering standards](../execution/engineering-guidelines.md) for DRY, maintained open-source reuse, simplicity and meaningful tests. Portable React/composition/design guidance preserves the React/TypeScript + FastAPI stack and deployment outside Vercel. No application API migration or clinical validation is implied.

Integrated the standards into worker launch instructions, UX foundations, service requirements and gates. Added verification-layer coverage for all UX-T01-14 scenarios while preserving the entire browser matrix. Strengthened account lifecycle requirements for same-doctor reauthentication and real authentication middleware checks. Corrected obsolete browser panel-layout and canonical task/story references.

A fresh GPT-6.1 Sol/high adversarial review identified six corrections incorporated in this revision; see [dispositions](../plans/ux/07-adversarial-review.md#october-19-2026-engineering-and-skills-review). Earlier xhigh reviews remain separate. Application tests and human gates remain pending.

## October 19 2026 UX planning refinement

Added eight sequenced UX documents: research, authenticated synthetic doctor panels, worklist, focused decisions, guides, appendix, validation, and a completed fresh GPT-6.1 Sol/xhigh plan review. Added concrete Carbon, GitHub, GOV.UK, NHS, Apple Health and Cloudscape precedents with source-to-feature mappings. Application work and human-factors validation remain pending.

Changed presentation requirements: LEG-10-015 uses the new stable navigation; LEG-11-017 distributes the patient dashboard hierarchy across focused views; LEG-12-002 distributes the five decision content groups across task-local views; LEG-13-009 uses historical read-only task views. All required content remains represented, including monitoring, uncertainty, concurrent tasks and source provenance. The section 12 heading is now Current decision workspace. The baseline migration counts below describe the earlier migration, not this subsequent revision.

The accepted review corrections specify exact evidence semantics, concurrent task discoverability, retained longitudinal content, draft/idempotency recovery and the original broader human-review gates. See [review dispositions](../plans/ux/07-adversarial-review.md).

LEG-11-005 is now an information inventory rather than a mandatory default-column layout; supplementary content remains in expansion. LEG-11-014 retains appointment and state filters, while authenticated ownership fixes clinician scope instead of a cross-doctor filter.

## October 19 2026 synthetic validation revision

Modularized the specification and execution context; added layered known-truth validation and a maintained evidence register. Added explicit reference equations, 32 scenario families, three distinct validation tracks, replication budgets, null-decision calibration and gate reading bundles. No model runs or human reviews were conducted by this documentation revision.

### Changed legacy requirements

| Unit | Disposition and reason |
|---|---|
| LEG-04-007 | Restricted the scalar ISI contrast to uninterrupted reference cases; interruption scenarios use EST-INT |
| LEG-04-013 | Replaced underspecified while-alive ISI with survival and explicitly conditional symptom outputs; undefined outcomes are not imputed |
| LEG-04-014 | Replaced vague while-in-scope contrast with hospitalization and alive-outpatient probabilities plus conditional symptoms |
| LEG-06-007 | Qualified an overly absolute statement about heterogeneity estimation with 2–4 studies; sensitivity to the prior remains mandatory |
| LEG-06-028 | Clarified null on the declared outcome while allowing treatment-affected intermediate variables; direct coefficient zero alone is insufficient |
| LEG-09-016 | Replaced no-update as an apparent missingness solution with explicit MAR analysis and MNAR sensitivity; retain no-update as comparator |

The atomic map covers 483 original content units, including explanatory and mathematical material, with 477 preserved and these six revised. Original source entries remain available; verification status is explicit. All original UI stories, invariants, and human-review gates are retained.

## Revision log (October 4, 2026 review)

Each change below was made because a source checked during review contradicted, sharpened, or exposed a gap in the earlier draft. Changes that are design consequences rather than literature findings are marked as such.

| Area | Change | Basis |
|---|---|---|
| Estimands (§4, §5, §6, §7, §16) | Replaced generic "censoring" with a per-event intercurrent-event strategy; death and admission are no longer treated as ignorable censoring | ICH E9(R1): treatment-policy strategy cannot be used for terminal events |
| Longitudinal model (§6, §7.4, §15–17) | Added the g-null paradox, a sharp-null scenario, and a false-ranking metric | McGrath, Young, Hernán 2022 |
| Borrowing (§6, §7.3, §12, §16) | Required an explicit, documented heterogeneity prior with sensitivity analysis; flagged that 2–4 studies cannot estimate heterogeneity | Röver et al. 2021 |
| MRT (§4, §9, §16, §17) | Named the causal excursion effect; required WCLS rather than standard mixed-model regression; required availability logging | Boruvka et al. 2018; Qian et al. 2022 |
| Bandit inference (§9, §16) | Stated why probability floors/ceilings are needed; added missing-reward handling | Hadad et al. 2021; missing-reward rule is a design decision |
| Concurrent learners (§3.1, §6, §9, §16) | Support policy is frozen during an N-of-1 block; added a scenario and comparator to test it | Design consequence of two learners sharing one outcome stream; to be verified in simulation |
| N-of-1 (§4, §6, §8, §12) | Added withdrawal/rebound handling and blinding status with its estimand label | Kales et al. 1983 and later reviews for rebound; blinding label is a design decision |
| Oversight (§1, §2.1, §5, §9, §12–16, §18) | Added a consent/oversight record as an eligibility gate for every randomized component | Stunnenberg et al. 2020: no consensus that N-of-1 trials are exempt from review |
| ISI (§2, §4, §5, §7.1, §7.5) | Recorded validation scope, the different origins of change thresholds, recall-interval versioning, and item dependence in the likelihood | Savard et al. 2005; Yang et al. 2009; Morin et al. 2011 |
| Wearables (§2, §11.2) | Stated the validation population and funding, added the general low wake-detection specificity, and excluded illness monitoring | Oura validation study details; *Sleep Advances* 2025 |
| Medication rule (§2) | Illustrative rule now shows both an exclusion and a dose-review flag | Suvorexant label sections 2.4 and 7.2 |
| Fall risk (§2, §8, §11.2, §12) | Added a clinician-acknowledged fall-risk review for sedating options, with the inpatient-evidence caveat | *Frontiers in Public Health* 2023 cohort |
| Trial context (§2) | Stated the sample size and feasibility design of the cited behavioral trial | Palesh et al. 2018 |
| Regulatory (§10) | Corrected the FDA guidance date and added the signal/pattern point | FDA document dated January 29, 2026 |
| Citations | Corrected or completed authors, volumes, and pages; the SMART paper's authors are Kidwell, Postow, and Panageas | Publisher and repository records |
| Notation and formatting | Restored the missing equals signs in the estimand and mixture formulas; renamed the study bias term to $\epsilon_s$ and the source comparator to $c_s$ to remove the collision with comparator $b$; fenced the flowchart | Internal consistency |

Not independently re-verified in this review, and carried forward unchanged: the Ontario Health algorithm, NCI PDQ, Keil et al., Hahn et al., Hobbs et al., Oganisian and Roy, Greenewald et al., Kallus and Uehara, the EconML and Stan documentation, the NIST, AHRQ workflow, NHS, and W3C sources, HARVEST, and the rheumatology co-design study.
