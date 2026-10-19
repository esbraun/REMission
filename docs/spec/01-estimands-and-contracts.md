# Estimands and data contracts

Specification revision: 2026-10-19. Status: requirements only; no implementation or validation result is asserted.

**Read first:** [00-scope-and-invariants.md](00-scope-and-invariants.md). Read linked scenario and evidence entries only when needed.

**Inputs:** versioned upstream contracts and applicable scenario IDs. **Outputs:** the contracts, artifacts and checks specified below. **Acceptance:** relevant G0–G7 evidence in [gates](08-gates-and-release.md); statistical checks use the [validation protocol](07-validation-protocol.md).

## CONTRACT-01 — Temporal and evaluation contracts

These are versioned internal interfaces, not public API wire formats. Semantic changes invalidate dependent evidence; historical outputs retain their original versions.

| Contract | Required content |
|---|---|
| DGPConfig | Version, layer, scenario, population sizes, time grid, equations/parameter table, observation rules, export schema and seed namespaces |
| EstimandContract | ID/version, population, observed history/cutoff, intervention/comparator, assignment versus delivery, outcome/unit/direction, horizon, continuation/support policies, event strategies and assumptions |
| TruthResult | Estimand, analytic/enumerated/numerical method, estimate/SE, information set, privileged-information flag, DGP version, seed stream and draw count |
| EvaluationProtocol | Locked cells, sample sizes, repetitions, metrics, thresholds, development/confirmation split, failure handling, model/prior/decision versions and protocol hash |
| ReplicateResult | Run/replicate IDs, seeds, attempted fit/status, estimates/intervals, diagnostics, truth reference, assignments/propensities, outcomes, violations, runtime/memory and failure reason |
| GateEvidence | Requirement IDs, input versions, executed checks/commands, manifests/checksums, attempted/completed counts, failures, reviewer disposition and claim limits |
| EvidenceRecord | Source ID, bibliography/year/URL/DOI, type/version, supported claim, limitations, locator, verification date/status, consuming requirements and role |

### TIME-01 — Daily ordering and history

Implement: prior available history → pre-decision state/eligibility → scheduled visit assignment → support assignment → delivery/adherence/rescue → skills/carryover/rebound and overnight outcome → next-morning measurements → availability timestamps → next history. Event time alone never establishes availability.

List parents of each structural equation and label covariates, treatments, mediators, outcomes, observation indicators and intercurrent events for each estimand. A variable can change roles at later decisions. Define initial distributions and irregular-visit observation processes. Patient random effects do not replace measured confounders.

### EST-INT — Interruptions and denominators

The uninterrupted reference target is the 42-day ISI contrast. With death/hospitalization, return separately: survival through day 42; hospitalization by day 42; alive-and-outpatient probability on day 42; and ISI conditional on being alive and outpatient on day 42 under each intervention. Include denominators and event times.

These conditional symptom contrasts compare intervention-specific populations, not a common survivor principal stratum. A zero conditioning probability produces undefined, not an invented mean. Do not scalarize the vector or automatically rank overall treatment. No ISI exists after death. This replaces underspecified while-alive/while-in-scope defaults. [iche9](../evidence/causal.md#iche9)

## 4. Estimands before algorithms

Write an estimand contract for every decision type. Specify the eligible population, intervention version, comparator, assignment versus delivery, time zero, outcome, horizon, continuation policy, concurrent support policy, intercurrent-event strategy, missing-data assumptions, and analysis assumptions. Align the historical analysis with a target-trial specification.[targettrial](../evidence/causal.md#targettrial)

| Decision | Primary causal question | Endpoint and horizon | Data suitable for identification |
|---|---|---|---|
| Initial or revised visit plan | What is the expected effect of assigning eligible plan A versus B now, under a common subsequent decision policy? | ISI at a prespecified distal horizon, with function and harms alongside it | Compatible trials; historical data with adequate exposure/outcome/confounder information; prospective decision data |
| N-of-1 medication comparison | For this patient, what is the effect of assigning A versus B during an eligible block? | Daily reported sleep quality or another prespecified proximal outcome; adverse effects and function | Randomized block assignment, delivery/adherence records, and longitudinal outcomes |
| Behavioral escalation | For eligible nonresponders, what is the effect of continuing versus escalating an ongoing program? | Later ISI/function, at a defined horizon | Sequential randomized assignments or carefully specified longitudinal observational analysis |
| Support prompt | Among available decision points, what is the causal excursion effect of offering a permitted support action versus no prompt, averaged over the support policy that generated the preceding history? | Next-morning report and prompt burden | MRT/bandit assignment logs, availability records, and outcomes |

For an uninterrupted reference visit at time $t$, define the contrast below. EST-INT replaces this scalar with separate outcomes in interruption scenarios; undefined potential ISI values are never subtracted.

$$
\Delta_t(h; a, b, \pi, K) = E\left[\,Y_{t+K}^{a,\pi} - Y_{t+K}^{b,\pi} \;\middle|\; H_t = h,\ a, b \text{ eligible}\right].
$$

Here $H_t$ contains only information available before assignment. The same continuation policy mapping $\pi$ applies after either initial assignment; resulting histories can differ. Freeze and record its version for each prediction. Lower ISI is better, so a negative contrast favors $a$.

For the demo, a six-week distal outcome and appointment-aligned reassessments are engineering choices. A trial reporting a six-week ISI effect can inform a compatible six-week comparison; its estimate cannot simply become a next-night sleep-duration or prompt-effect prior. Because the ISI asks about a recall window, an administration shortly after a treatment change mixes pre- and post-change nights; the contract must state the earliest post-assignment ISI that counts as an outcome for that assignment.

**Intercurrent events.** "Censoring" is not an adequate description of what happens to these patients within a six-week horizon. The ICH E9(R1) framework separates intercurrent events from missing data and offers five handling strategies: treatment policy, hypothetical, composite, while-on-treatment/while-alive, and principal stratum. The treatment-policy strategy cannot be applied to a terminal event such as death, after which the outcome does not exist.[iche9](../evidence/causal.md#iche9) Each contract therefore lists, per event, the chosen strategy. The demonstration defaults, which are engineering choices to be reviewed in Phase 0, are:

| Intercurrent event | Default strategy in the demo | Consequence |
|---|---|---|
| Death | Survival through day 42 and conditional symptom distribution under EST-INT | No post-death ISI; no common-survivor or overall superiority claim |
| Hospital admission / leaving outpatient scope | Admission and alive-outpatient probabilities plus explicitly conditional ISI under EST-INT | Admission triggers a hold; conditional populations can differ by intervention |
| Chemotherapy regimen or steroid schedule change | Treatment policy (part of real-world care) | Outcome still collected; phase recorded as a covariate after assignment, not conditioned on as baseline |
| Rescue hypnotic use | Treatment policy for the primary contrast; reported alongside | Do not exclude rescue nights |
| Discontinuation or clinician override of the assigned plan | Treatment policy (effect of assignment) | Per-protocol effects need separate assumptions |

Primary randomized analyses estimate effects of assignment. If a clinician overrides a randomized proposal or a patient does not take it, retain both assignment and actual treatment. Per-protocol effects need additional assumptions; do not obtain them by restricting the analysis to adherent patients.

**Blinding.** Record for every randomized comparison whether the patient and clinician are blinded. The N-of-1 outcome is patient-reported, so an open-label comparison estimates the effect of *knowingly* receiving A versus B, expectancy included. That may be the clinically relevant quantity, but it must be labeled as such and must not be pooled with blinded evidence without a term for the difference.

CATE is a conditional average effect. A patient-specific posterior incorporating their repeated observations is still a model-based expectation; it does not reveal both realized potential outcomes for that person.

## 5. Data contracts, timing, and provenance

Use versioned contracts and a replay clock. Every clinical or wearable record needs an event time and an availability time. Prediction snapshots must use the latter to prevent future information from leaking backward.

| Entity | Minimum fields |
|---|---|
| Patient | Synthetic ID; demographic/clinical covariates; preferences; baseline eligibility; care team |
| Consent/oversight record | Component (N-of-1, escalation randomization, MRT/bandit), status, version, date, withdrawal time |
| Encounter | Encounter ID, scheduled/actual time, care setting, chemotherapy phase/cycle, review status |
| Medication order | Drug identifier, intended schedule, order/change/stop times, ordering clinician, source |
| Medication exposure | Actual taken/reported administration, timing, adherence, rescue use, uncertainty |
| Clinical observation | Concept, value, unit, event time, available-at time, source, corrected/superseded status |
| Intercurrent event | Type (death, admission, regimen change, discontinuation, rescue), event and available-at times, source |
| Oura-like observation | Record type, sleep episode/date, estimated sleep/wake measures, source/device version, event and sync times, quality/missingness flags |
| Patient report | Daily diary/function/adverse symptoms; ISI items, instrument version, and recall interval; patient goals and burden |
| External study | Population, intervention/comparator, outcome/scale, follow-up, effect/SE or IPD, covariate distribution, blinding, bias/transport notes, source/version |
| Decision snapshot | History cutoff, workflow state, eligible actions and reasons, outcome/horizon, posterior/model/evidence/policy versions, support policy version in force |
| Assignment event | Recommended option, approved option, experimental assignment, assignment probability, blinding status, clinician override and reason |
| Delivery event | Offered/delivered/taken action, time, adherence, rescue, protocol deviation |
| Follow-up task | Owner, due date, trigger, status, escalation destination |
| Audit/model run | Actor, change, versions, fit diagnostics, execution time, reproducible seed, data lineage |
| Simulator truth | Latent states, structural parameters, counterfactual outcomes; accessible only to evaluation services |

Use a FHIR-shaped EMR adapter and a versioned Oura replay adapter. Consult SMART App Launch and Oura's official API documentation when implementing actual interfaces.[smart](../evidence/ux-and-interfaces.md#smart)[oura_api](../evidence/ux-and-interfaces.md#oura-api) Do not represent a mock payload as a guaranteed current vendor schema.

Keep units, timezone, overnight episodes crossing midnight, local calendar dates, lab reference context, duplicates, late uploads, and corrections explicit. A prescribed drug is not evidence that it was taken. Absence of a wearable record is not evidence of poor sleep or clinical stability.

Historical EMR lacking insomnia measures, treatment details, or essential confounders cannot supply a trustworthy efficacy estimate merely because it has many patients. Historical records lacking Oura cannot identify Oura-treatment interactions.
