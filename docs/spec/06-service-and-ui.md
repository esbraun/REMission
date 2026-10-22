# Service and clinician interface

Specification revision: 2026-10-19. Status: requirements only; no implementation or validation result is asserted.

**Read first:** [00-scope-and-invariants.md](00-scope-and-invariants.md), [01-estimands-and-contracts.md](01-estimands-and-contracts.md). Read linked scenario and evidence entries only when needed.

**Inputs:** versioned upstream contracts and applicable scenario IDs. **Outputs:** the contracts, artifacts and checks specified below. **Acceptance:** relevant G0–G7 evidence in [gates](08-gates-and-release.md); statistical checks use the [validation protocol](07-validation-protocol.md).

## UX presentation refinement (October 19, 2026)

The [sequenced UX plans](../plans/ux/00-research-and-foundations.md) define the refined presentation: authenticated doctor-owned synthetic panels; My panel; patient Overview, Current decision, Monitoring and History; task-local Assess, Compare options, Decide and follow up views; contextual guides; and a dashboard technical appendix. These names and view boundaries supersede the older tab/combined-panel layout. Domain content, stage actions, uncertainty, history and safety requirements below remain mandatory. Use [validation scenarios](../plans/ux/06-validation-and-integration.md) alongside UI-VALIDATION; no implementation or human acceptance is asserted.

## UI-VALIDATION — Rendering verified research evidence

For the immediate PoC, [APPT-01–05](poc-amendment-20261021.md#appt-0105--background-refresh-and-appointment-prediction) govern background refresh, versioned artifact identity and appointment advice. The existing [analytics integration seams](../implementation/poc-analytics-contract-20261021.md#appointment-integration-seams) map that behavior to current jobs/results and UI. Display data-through and generation times plus hash-aware current/stale/historical/unavailable state; appointment navigation, selection and approval never start or await fitting. Preserve explicit physician choice, advancement, immutable history and current clinical approval guards. APPT implementation remains not started; [POC-VAL](07-validation-protocol.md#appt-04--appointment-timeliness-and-freshness) owns its unmeasured latency/freshness hypotheses.

Expose the exact estimand, units, horizon, event strategy, cutoff, evidence status, model/policy version and interval type from accepted backend outputs. Distinguish numeric sorting from a permitted superiority claim. Present missing, pending, undefined and failed estimates differently. Death/hospitalization scenarios show separate outcomes and conditional-population labels under [EST-INT](01-estimands-and-contracts.md#est-int--interruptions-and-denominators); do not synthesize an overall winner.

Verify saved output rendering against fixture manifests, including fit failures, inconclusive truth and failed statistical gates. A clinical hold invalidates readiness immediately even before model refitting. Preserve all existing human-factors and accessibility tasks; browser automation does not substitute for those reviews.

## 10. Research-backed UI design requirements

The following sources guide the design process and specific presentation choices. They do not establish that a particular dashboard is clinically effective. The proposed layout and historical-state behavior remain hypotheses to test with clinicians.

| Research or guide | Relevant finding or requirement | Application in this app |
|---|---|---|
| NIST EHR usability protocol | Combine clinical/human-factors review with representative users performing realistic tasks | Observe outpatient work; test assessment, assignment, interruption, and historical review tasks[nist7804](../evidence/ux-and-interfaces.md#nist7804) |
| NIST safety-enhanced usability research | Keep patient identification consistent and make outdated/inappropriate information identifiable | Reserved patient banner; explicit time context; medication and data freshness indicators[nist7804_1](../evidence/ux-and-interfaces.md#nist7804-1) |
| AHRQ workflow/CDS guidance | Match support to the actual decision and team workflow | Place actionable comparisons at assignment/review; give follow-up tasks an owner[ahrq_workflow](../evidence/ux-and-interfaces.md#ahrq-workflow) |
| NHS design system and principles | Start from user needs and use consistent, accessible patterns | Stable navigation, plain labels, recognizable forms/statuses, clinician and nurse research[nhs_design](../evidence/ux-and-interfaces.md#nhs-design) |
| NHS accessibility guidance; WCAG 2.2 | Design and test accessible interaction | Keyboard operation, visible focus, sufficient contrast, readable zoom/reflow, labels, and text beyond color[nhs_accessibility](../evidence/ux-and-interfaces.md#nhs-accessibility)[wcag](../evidence/ux-and-interfaces.md#wcag) |
| Government Analysis Function dashboard guidance | Choose metrics for user needs; limit clutter; make metadata and quality visible; test interactions | Task-based overview, a few meaningful trend panels, visible filters/cutoffs, accessible tables[gaf_dashboard](../evidence/ux-and-interfaces.md#gaf-dashboard)[gaf_testing](../evidence/ux-and-interfaces.md#gaf-testing) |
| Guidance on statistical uncertainty | Explain uncertainty and limitations prominently and at useful levels of detail | Effect intervals, endpoint/horizon labels, prior dependence, and support limitations beside recommendations[gaf_uncertainty](../evidence/ux-and-interfaces.md#gaf-uncertainty) |
| HARVEST formative research | Longitudinal record visualization can support point-of-care chart review | A linked patient timeline with direct access to source events; test time and accuracy rather than assume benefit[harvest](../evidence/ux-and-interfaces.md#harvest) |
| Rheumatology dashboard co-design study | Develop longitudinal clinical/patient-report displays with users and iterate in visits | Co-design combined report/medication timelines and shared-decision views; do not transfer efficacy claims to leukemia[codesign](../evidence/ux-and-interfaces.md#codesign) |
| FDA CDS guidance, issued January 6, 2026 and superseded by the January 29, 2026 version | Enable independent examination of inputs, recommendation basis, knowns/unknowns, and limitations | Inspectable evidence and input snapshot; clear model limitations and clinician decision controls[fda_cds](../evidence/ux-and-interfaces.md#fda-cds) |

FDA transparency guidance informs this design; the prototype does not claim a non-device classification. Use the January 29, 2026 document, which supersedes the January 6 issue. Commentary on the 2026 guidance notes that it distinguishes single discrete measurements from signals or patterns of repeated measurements, and a product that processes nightly wearable streams and ranks treatments falls on the side that needs a careful classification analysis. Classification for a future clinical product depends on its actual functions, including wearable processing and treatment optimization.

### Interaction principles to implement and test

- **Keep the shell stable.** My panel leads to patient Overview, Current decision, Monitoring and History. Current decision has task-local Assess, Compare options, and Decide and follow up views. Stage changes replace relevant content, not the entire navigation; detailed diagnostics are available through Inspect basis.
- **Show the decision first.** A short clinical context, readiness status, and eligible choices precede technical model diagnostics.
- **Reveal detail progressively.** Provide an immediately visible uncertainty/support summary, with deeper prior, overlap, fit, and protocol detail available on demand.
- **Keep urgent clinical information visible.** Holds and action-blocking reasons are inline, specific, and actionable; routine model updates do not create repeated interruptive alerts.
- **Use direct comparisons.** Compare a small eligible choice set against the same reference and horizon. Avoid a decorative "best treatment" score.
- **Distinguish observations from estimates.** Patient report, wearable estimate, causal estimate, and clinician judgment have separate labels.
- **Prevent context errors.** Patient, decision date, current versus historical mode, and data cutoff stay visible on every clinical view.
- **Make action consequences clear.** Approval, experimental enrollment, pause, and completion use different verbs and summaries.
- **Avoid relying on hover.** Critical values/reasons are readable and keyboard-accessible; every chart has a tabular alternative.
- **Preserve useful customization.** Clinicians can change date range and expand panels, but cannot hide patient identity, historical-mode status, or action-blocking constraints.

These are design requirements derived from the sources and this workflow. Validate the exact labels, density, and placement with the intended users.

## 11. Overall dashboard

Provide two levels, with an explicit patient selector.

The demonstration has a persistent "Synthetic demonstration — simulated patients and estimates" label. Reference-study citations and synthetic quantitative study records must be visibly distinguishable.

### 11.1 Clinic dashboard

An actionable worklist is the main view. Small summary counts link to the same filtered list; avoid a wall of unrelated KPIs.

The table below is the required information inventory, not the refined default column layout. The [panel plan](../plans/ux/02-panel-dashboard.md) places supplementary appointment, report and assignment detail in expansion while retaining identity, next task, holds and readiness inline. The authenticated doctor scope replaces a cross-clinician filter in this single-doctor version; appointment-date filtering remains available.

| Column | Purpose |
|---|---|
| Patient identifiers and appointment | Keep identity and outpatient timing clear |
| Clinical/learning stage | Show active care and experiment status separately |
| Next task and owner | Identify what the team should do next |
| Latest ISI/report trend | Show date, recall window, and missingness |
| Relevant safety or review trigger | Distinguish a clinical hold from a data issue |
| Data readiness | Latest diary/Oura sync and missing required inputs |
| Assignment status | Pending review, approved, active block, outcome due, or maintenance |
| Follow-up due | Make overdue and upcoming work actionable |

Default ordering prioritizes configured clinical review tasks and decisions due; document sorting and allow filters by clinician, appointment date, clinical stage, and learning stage. Do not silently rank urgency from an unvalidated model.

Counts use denominators and timestamps: for example, "3 of 12 scheduled patients need data review." A patient with no recent report must not appear as improved.

### 11.2 Selected-patient dashboard

Preserve the following content hierarchy across the patient workspace. Overview shows identity, current plan and next task with a relevant recent summary; Assess owns readiness/contributors; Compare options owns evidence; Monitoring owns the full aligned trends, treatment/phase lanes and data-follow-up detail. Context and relevant excerpts remain visible during decisions. Do not render all seven groups as a single default dashboard:

1. **Patient/context banner:** identity, care team, chemotherapy phase, current/historical mode, selected decision, and last update.
2. **Current plan and next task:** approved intervention, clinical/learning stage, next appointment, and the single main next action.
3. **Clinical readiness and contributors:** relevant reviewed problems, interaction/stability status, fall-risk review status, and patient goals.
4. **Aligned trend panels:** ISI at its assessment dates; daily reported sleep/function; Oura-estimated sleep. Shared time axis, separate units/scales, no unexplained dual axis.
5. **Treatment/phase lanes:** behavioral program, medication order and actual use, N-of-1 blocks and washouts, chemotherapy/steroid periods, and holds.
6. **Evidence summary:** last decision's main comparison, uncertainty, evidence support, and prior dependence.
7. **Data and follow-up:** coverage, latest available data, discordance, and owned tasks.

Graphs show gaps as gaps. Display wearable coverage and device-version changes; distinguish raw observations, any smoothing, and predicted trajectories. Include a "Why these differ?" explanation when the ring and patient report disagree, with clinical review rather than automatic reconciliation. The explanation should state the general direction of wearable error (sleep overestimated when wake time is high) rather than present the two sources as equally likely to be right.

Use signed treatment-effect dot-and-interval plots with a clearly labeled comparator, scale, direction of benefit, horizon, and interval type. A credible interval for an average effect is not an individual's outcome prediction interval.

For sparse ISI visits, show assessment points and recall windows; a connected line must not imply continuous daily measurement. Table and text summaries must reflect the currently selected date range and historical cutoff.

## 12. Current decision workspace

This is a decision workspace, not a generic analytics page. Its title remains stable; its task header changes, for example: "Initial plan," "Review block 2," or "Reassessment after brief behavioral treatment."

Preserve five content groups distributed across the task-local views: decision context throughout; clinical assessment in Assess; evidence/diagnostics and eligible options in Compare options; clinician decision in Decide and follow up. These are not five simultaneously expanded panels:

1. **Decision context:** selected step, clinical question, approved background care, outcome/horizon, and current versus historical date.
2. **Clinical assessment and readiness:** relevant symptoms/contributors, medication reconciliation, patient goals, stability, and exclusions.
3. **Evidence and diagnostics for this step:** brief clinical summary plus appropriate causal/experimental diagnostics.
4. **Eligible options:** comparative effects and uncertainty, practical burden, harms, and reasons an option is unavailable.
5. **Clinician decision:** choice, rationale, patient preference, follow-up, and approval/hold controls.

### Content by patient step

| Selected step | Clinical information | Decision/model diagnostics | Available decision controls |
|---|---|---|---|
| Assessment incomplete | Sleep history, ISI/diary, daytime impairment, contributor and alternative-disorder review | Required-input checklist, data dates, wearable/report discordance; no fabricated treatment ranking | Complete review, request data, refer, or enter clinical hold |
| Initial assignment / cold start | Goals, stability, reviewed contributors, current medicines, feasible behavioral care | Compatible studies; transport differences; prior-only or limited local evidence; interval width; support, heterogeneity-prior, and no-borrowing sensitivity | Choose eligible plan, record preference/rationale, approve follow-up, or defer |
| Treatment active, no decision due | Current approved plan, adherence, burden, adverse symptoms, next visit | Data coverage and review triggers; outcome maturity; no new medication assignment just because another night arrived | Continue monitoring, record a clinically justified amendment, or hold |
| N-of-1 eligibility/design | Both options acceptable; stable period; rescue plan; fall-risk review; patient agreement and consent record | Reversibility, onset/offset, carryover and rebound plan, blinding, endpoint, block schedule, expected precision/burden | Approve protocol; decline or revise comparison |
| N-of-1 block active / next block | Current block, actual use, adverse symptoms, phase changes, rescue | Assigned-versus-delivered status; washout/carryover readiness; incomplete outcomes; prespecified interim boundaries; support policy frozen | Confirm protocol-prescribed next block when ready, pause, or stop; do not manually pick a "winning" block and retain the old randomized analysis claim |
| N-of-1 interim/final review | Patient function, burden, tolerability, goals | Posterior contrast; serial correlation/trend/carryover checks; informative block count; uncertainty and protocol deviations | Continue, select an eligible long-term plan, end as inconclusive, or redesign |
| Behavioral reassessment/escalation | Program completion/skills, symptom response, function, and adherence barriers | Prespecified response criterion; outcome timing; escalation evidence; SMART eligibility, consent record, and assignment history | Continue, clinician-guided escalation, or approve eligible sequential randomization |
| MRT/bandit support review | Approved behavioral content, availability, patient preferences, burden | Prompt-effect evidence; uncertainty; assignment probabilities and their bounds; proximal versus distal outcomes; reward missingness; drift/support | Approve/change the support envelope, pause learning, or return to fixed support |
| Clinical hold or major phase change | Reason for hold, responsible team member, changed regimen/state, required clinical review | Explicit blocked actions and prerequisites; prior predictions marked potentially inapplicable | Resolve clinical review and re-enter assessment; no experimental assignment while held |
| Maintenance/closeout | Sustained reports/function, patient preferences, ongoing therapy review | Evidence maturity, uncertainty about recurrence, next review plan | Continue maintenance, close episode, or reopen assessment |

The step-specific panel chooses diagnostics relevant to the decision. A prompt review does not default to an N-of-1 carryover plot, and an initial assignment does not show fictitious individual-trial evidence.

### Option card contract

Every card shows:

- Intervention and comparator in clinical language.
- Target outcome and time horizon.
- Expected effect plus interval, with units and benefit direction.
- Clinically relevant harms/burden and constraints.
- Evidence status: prior-only, observationally updated, randomized individual evidence (blinded or open-label), or mixed.
- Applicability/data-support limitations.
- Patient preference/feasibility.
- "Inspect basis" link to the exact data and evidence snapshot.

Display "Insufficient evidence to rank these options" when appropriate. This still permits ordinary clinician care but suppresses model-backed superiority claims and experimental assignment until its eligibility criteria are satisfied.

Keep "choose treatment" distinct from "approve randomization." Never preselect a recommended option solely because it is at the top of a model list. An approved randomized protocol determines the next assignment according to its rules.

Before approval, show a concise summary of the patient, chosen plan or protocol action, changed elements, follow-up, and stop/review conditions. Verify the latest patient/state version server-side. If a material safety or regimen update arrived during review, require refresh/review of that specific change instead of silently using a stale decision.

## 13. Historical review and time travel

The clinician must be able to change the selected view back to any previous decision. This changes the view context, not the patient's actual current treatment.

### Controls

- A decision/visit selector and a linked timeline allow selection of a historical step.
- "Previous decision" and "Next decision" controls preserve the patient and panel layout.
- A persistent banner says "Historical review — decision on [date/time]", shows the historical stage, and provides "Return to current decision."
- Default historical view is **as known then**: only information available at that decision, its eligible action set, estimates, evidence/model/policy versions, and actual clinician decision.
- An explicitly separate **retrospective outcomes** section reveals what happened later. Later outcomes do not appear inside the original recommendation card.
- A comparison view can show "then" versus "now" using matched outcomes/comparators and clear labels when estimates are not directly comparable.

In historical mode, the decision workspace renders read-only task views for the historical stage. For example, selecting an initial visit shows the initial cold-start view; selecting a completed trial block shows block-specific review. Historical mode persists through deep links and refresh.

### Immutable snapshots

Store:

- Clinical and learning state at decision time.
- Available-at data cutoff and complete input record references.
- Eligible/ineligible actions with contemporaneous reasons, including consent status.
- Original estimates or a versioned stored posterior summary/draw reference.
- Evidence, prior, feature, model, and policy versions.
- Recommendation, randomized assignment if any, clinician approval/override, and rationale.
- Follow-up/stopping plan and subsequent amendments.

Use event-time and transaction-time records for late or corrected data. An observation collected yesterday but uploaded tomorrow must not appear in yesterday's as-known-then snapshot.

Historical decisions are read-only. Addenda become new audit events; they do not rewrite the original recommendation. A "Re-evaluate with current evidence" function, if included, opens a separately labeled retrospective analysis with new versions and no ability to issue a current treatment order from the old snapshot.

A replay test must recover the exact displayed historical recommendation and diagnostic summary. New model fits must not silently replace it.

## 14. Application architecture and implementation contracts

Apply [ENG-01, UI-SKILLS and TEST-QUALITY](../execution/engineering-guidelines.md) to implementation and review. Keep the service authoritative for domain rules and reuse contracts rather than duplicate eligibility logic in UI components. These standards add no public API redesign or hosting migration; deployment is outside Vercel.

### Suggested demonstration stack

These are engineering choices, not findings from clinical studies.

- **Frontend:** React/TypeScript with an accessible component foundation; design tokens and component behavior informed by the NHS guidance, adapted to the local clinical environment rather than presented as an NHS product.
- **Service:** Python/FastAPI with typed validation contracts.
- **Storage:** immutable events and snapshots in a local database; DuckDB/Parquet for reproducible analytics. Keep identifiers separate from model features even though all records are synthetic.
- **Bayesian engine:** PyMC with explicit native NUTS initially and compatible ArviZ diagnostics; pin tested dependencies during implementation. Follow the [methods library decisions](../plans/methods/00-library-decisions.md). RBesT/SBC/MRTAnalysis operate offline through versioned artifacts; nutpie requires a recorded acceleration check.
- **Workers:** batch historical fitting, posterior rollout, incremental new-data jobs, and policy evaluation. Do not run a full MCMC chain during a clinician's approval click.
- **Adapters:** synthetic FHIR/EMR replay, Oura-like replay, patient-report replay, and literature/evidence registry.
- **Simulator/evaluator:** separate process and storage permissions for hidden truth.
- **Policy controller:** independent eligibility masks (clinical, consent, and coordination rules), assignment protocol, clinician approval, and audit logging.

Use one modeling backend initially. Cache versioned posterior summaries for a smooth demo, but expose fit age and freshness. A newly arrived clinical event can invalidate decision readiness immediately even while a new statistical fit is pending.

### Core service capabilities

| Capability | Required behavior |
|---|---|
| Patient overview | Return current plan, states, task ownership, dates, and data quality |
| Decision workspace | Return stage-specific clinical, diagnostic, and option-panel data |
| History | Return immutable selected-decision snapshot and separately requested later outcomes |
| Eligibility | Compute allowed actions and explain exclusions before estimation/assignment, including consent status and the N-of-1 freeze rule |
| Comparison | Evaluate a declared estimand using a specified model/policy version |
| Approval | Check patient/state version; create approved plan and follow-up atomically |
| Randomization | Draw from the approved protocol; record probabilities before delivery |
| Outcome ingestion | Deduplicate, preserve timing/corrections, update readiness and model jobs |
| Model registry | Track prior/evidence/data versions, diagnostics, deployment status, and sensitivity results |
| Evaluation | Access simulator truth only in the research/evaluation surface |

Use role permissions, idempotent ingestion/approval, optimistic concurrency checks, and rollback-safe transactions. All recommendation, approval, assignment, delivery, and outcome events require stable IDs.

No real EMR orders, patient messages, live device accounts, or clinical prescribing are part of the synthetic demonstration. Preserve interface boundaries for later integration; do not needlessly build production connections to show the methodology.

### Frontend state contract

Maintain separate values for:

- Selected patient.
- Current clinical and learning states.
- Selected decision ID.
- View mode: current, historical as-known-then, or retrospective analysis.
- Display date range.
- Active data/model/evidence versions.
- Readiness/eligibility and action permissions.

Obtain stage and permissions from the service; do not infer them from UI tab position. A deep link to a historical decision must remain historical after refresh. Switching patients must clear drafts and update the identity banner before decision controls become active.
