# Adversarial UX plan review

Date: October 19, 2026. Reviewer: fresh subagent using gpt-6.1-sol, xhigh reasoning, without inherited conversation history. The reviewer received the draft and inspected repository scope, service/UI and gate specifications. No UI implementation or user study was reviewed.

## Findings and dispositions

| Priority | Finding | Resolution in revised plans |
|---|---|---|
| P1 | Generic comparison cards could drop required estimand, uncertainty and interruption semantics | Plan 03 explicitly preserves comparison labels, availability states, separate outcomes and conditional-population/event-strategy labels; UX-T06/07 |
| P1 | A single linear workflow would misrepresent independent care and learning states | Four-section shell with task-local subviews and stage mapping; service-derived independent states; UX-T05 |
| P1 | Simplified Monitoring could silently remove longitudinal requirements | Plan 03 retains aligned ISI/report/Oura displays, recall windows, gaps, phase/treatment lanes, provenance and tables; UX-T07/14 |
| P1 | One main task per patient could hide concurrent work | Plan 02 adds visible open-task count/list, owners, blockers and deterministic ordering; UX-T03 |
| P1 | Draft and uncertain-submission lifecycle was incomplete | Plan 03 specifies save/discard/cancel, version-bound drafts, expiry/refresh behavior and original-key approval recovery; UX-T08/09 |
| P2 | Two small doctor studies could replace broader required human review | Plan 06 retains nurse/behavioral, clinical and manual-accessibility review and separate evidence statuses |

The reviewer judged the revised shell appropriate and reported no fundamental blocker if the corrections were included. Findings are addressed in the written plans; runtime verification remains pending.

## Pattern-fit review

Carbon fits supplementary table expansion, with essential blockers visible. GitHub fits review filtering and return context, without dense metadata or activity ordering. NHS provides the coherent component foundation. GOV task lists fit resumption without a forced wizard. Apple Health fits trend-to-detail with separate scales and wearable caveats. Cloudscape is the closest fit for inline help, contextual guides and deeper documentation.

## Follow-through

A second fresh gpt-6.1-sol/xhigh subagent inspected the saved Markdown package, canonical service requirements and traceability on October 19, 2026. It reported no remaining actionable findings after the panel information-inventory clarification, authenticated clinician scope, appointment filters and draft/session rules were reconciled. This was a documentation consistency review only.

Re-review the implemented flows before G5 acceptance. Record evidence, severity, fix and retest for new findings. Do not use this completed plan review to claim application safety, clinical validity or human-factors acceptance.
