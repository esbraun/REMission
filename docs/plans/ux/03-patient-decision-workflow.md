# Patient decision workflow

Status: implementation plan. Depends on [01](01-doctor-accounts-and-shell.md), [02](02-panel-dashboard.md), and accepted domain contracts.

## Views

Overview shows the approved plan, next task, all open tasks and a small relevant recent-observation summary. Current decision uses one task-local step per view:

| View | Necessary content |
|---|---|
| Assess | History, goals, contributors, input completeness, readiness and blockers relevant to this task |
| Compare options | Eligible choices, effects, uncertainty, burden/harms and applicability |
| Decide and follow up | Explicit selection or protocol action, preference, rationale, follow-up and concise confirmation |

Completed steps can be revisited. One primary action does not remove necessary hold/defer controls. Task selection and tab position do not determine clinical, learning, consent or readiness state.

## Stage-to-view mapping

| Service task/stage | View behavior |
|---|---|
| Assessment incomplete | Assess inputs/contributors; allow data request/referral/hold; no fabricated comparison |
| Initial assignment/cold start | Assess -> Compare -> Decide; label prior-only/limited evidence |
| Treatment active, no decision due | Monitoring; amendment/hold only when clinically justified, no forced reassignment |
| N-of-1 eligibility/design | Assess acceptability/consent; inspect protocol and expected precision; approve/revise/decline protocol |
| N-of-1 block active/next block | Monitor delivered versus assigned and readiness; confirm protocol-prescribed block, pause or stop |
| N-of-1 interim/final review | Compare posterior contrast and protocol diagnostics; continue, select eligible plan, inconclusive or redesign |
| Behavioral reassessment/escalation | Assess response/adherence; compare eligible escalation; separate clinician choice from sequential randomization |
| MRT/bandit support review | Assess burden/preferences; compare support evidence; approve envelope, pause or fixed support |
| Hold/major phase change | Assess changed state and specific blocked actions; return through required review before assignment |
| Maintenance/closeout | Review sustained outcomes/preferences; maintain, close episode or reopen assessment |

All actions remain governed by the original stage matrix and clinical/consent/coordination rules in the [canonical service specification](../../spec/06-service-and-ui.md). A protocol schedule cannot be overridden by choosing a numerically favored block.

## Evidence presentation

Beside comparisons retain outcome/comparator, units, benefit direction, horizon, interval type, cutoff, evidence status, uncertainty and applicability/support limitations. Expose exact estimand, event strategy and model/policy/evidence versions through labeled basis details; event-strategy and population labels are inline whenever needed to interpret an outcome.

Separate missing, pending, undefined and failed estimates from inconclusive valid estimates. Separate death, hospitalization and conditional symptom outcomes; do not synthesize an overall winner. Preserve conditional-population labels. Distinguish credible intervals of average effects from individual prediction intervals.

Do not preselect the highest-ranked treatment. Keep ordinary clinician care, experimental eligibility and permission to claim superiority distinct. Show exclusions and their reasons. Inspect basis opens the exact input/evidence snapshot and relevant diagnostics.

## Monitoring and history

Monitoring contains aligned ISI assessment points/recall windows, daily reports and Oura estimates using separate scales; gaps, coverage and device-version changes; treatment, chemotherapy, steroid, washout and hold lanes; source-event access; and chart tables. Explain wearable/report disagreement without automatic reconciliation. Show the task-relevant excerpt during decisions.

History is read-only as-known-then, with immutable decision inputs, permissions, estimates and versions. Later outcomes are separately requested and labeled retrospective. Historical deep links remain historical on reload. Return to current is explicit; historical selection never changes actual treatment.

## Context, drafts and submission

Decision context includes patient ID, task ID, decision ID, mode, clinical/learning states, readiness, consent/hold status, allowed actions, cutoff and state/model/evidence versions. The service is authoritative.

Keep a task-scoped draft with its base state version; preserve it across subviews. Leaving the context offers Save draft, Discard or Cancel. Saving is not approval or a committed assessment action. Clear client drafts on patient/task switch; resume a saved server draft explicitly after state revalidation. Refresh loses unsaved local input with the supported browser warning; session expiry clears local input and explains that only saved drafts can be recovered.

Approval uses optimistic concurrency, an idempotency key and an atomic persisted outcome. Material changes require review of the changed facts. On timeout show Checking approval status and retrieve the result using the original key; never retry with a new key while outcome is unknown. Clear the draft after confirmed persistence. Log clinician actions separately from assignments and delivery.

## Acceptance

Exercise every stage above and concurrent tasks. Test stale holds during review, invalidated estimates, no superiority claim, historical refresh, task-switch draft isolation, explicit save/resume, double-clicks, lost responses and amendments. Assert rendered values against saved backend fixtures.

Sources: [GOV task lists](https://design-system.service.gov.uk/patterns/complete-multiple-tasks/), [Apple Health](https://support.apple.com/en-euro/guide/iphone/iphe3d379c32/ios), and the existing clinical/statistical contracts.
