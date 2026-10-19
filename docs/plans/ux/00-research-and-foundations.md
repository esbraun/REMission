# UX research and foundations

Status: planned application work; documentation researched October 19, 2026. No implemented UI or human-factors acceptance is claimed.

## Sequence and authority

Read [scope](../../spec/00-scope-and-invariants.md), [service requirements](../../spec/06-service-and-ui.md), and [gates](../../spec/08-gates-and-release.md) first. This package refines presentation and interaction; it does not change eligibility, estimands, consent, or validation requirements. Detailed design starts after accepted G0 contracts.

| Order | Plan | Dependency |
|---|---|---|
| 00 | This research and foundation | Existing domain specifications |
| 01 | [Doctor accounts and shell](01-doctor-accounts-and-shell.md) | 00 and G0 |
| 02 | [Panel dashboard](02-panel-dashboard.md) | 01 |
| 03 | [Patient decision workflow](03-patient-decision-workflow.md) | 01-02 and domain contracts |
| 04 | [Tooltips and view guides](04-tooltips-and-view-guides.md) | View definitions; ship alongside each view |
| 05 | [Technical appendix](05-technical-appendix.md) | 00 and shared help/content structure |
| 06 | [Validation and integration](06-validation-and-integration.md) | Defines tests early; integrated acceptance after preceding work |
| 07 | [Adversarial review](07-adversarial-review.md) | Records completed plan review and dispositions |

The root plan remains the navigation index. Canonical service requirements own domain behavior; this package owns the refined UX layout. Superseded legacy navigation is identified in the canonical specification and traceability.

## Confirmed user decisions

- Real username/password authentication, one doctor per account, synthetic patients only.
- One decision step per view, rather than one analytics pipeline stage per screen.
- A calm clinical visual style and a panel overview for review and drill-down.
- Accessible terminology help, a pop-out guide for every view, and a dashboard-accessible technical appendix.
- Real examples to adapt, with a fresh GPT-6.1 Sol extra-high adversarial review.

## Existing examples to adapt

The linked official pages contain examples or screenshots. Features are adapted into one design system; these products are not evidence of clinical effectiveness.

| Reference | Observed example | REMission adaptation | Boundary |
|---|---|---|---|
| [Carbon data table](https://www.carbondesignsystem.com/building-blocks/core/components/data-table/guidelines) | Toolbar, sortable headers, pagination, expandable rows | Searchable patient panel; expansion for supplementary details | Never hide blockers or identity in expansion; no bulk clinical approval |
| [GitHub review queues](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/filtering-and-searching-issues-and-pull-requests) | Review filters and URL-preserved filter/sort state | Review queue and return to previous list context | Plain-language controls, no query-language requirement or activity-driven urgency |
| [GOV.UK task list](https://design-system.service.gov.uk/patterns/complete-multiple-tasks/) | Verb-led tasks, statuses, return across sessions | Resumable decision tasks | Task navigation does not imply a single linear patient state |
| [NHS design principles](https://service-manual.nhs.uk/design-system/design-principles) | Consistent accessible health-service design | Forms, typography, status presentation and interaction foundation | No NHS branding or implied endorsement |
| [Apple Health data views](https://support.apple.com/en-euro/guide/iphone/iphe3d379c32/ios) | Graph-to-detail, time ranges, source access | Patient trends and provenance | No consumer score, automatic clinical inference, or combined outcome scale |
| [Cloudscape help system](https://cloudscape.design/patterns/general/help-system/) | Inline text, contextual panel, deeper documentation | Three levels of help | Required decision information stays inline |

Supporting research: [NISTIR 7804-1](https://www.nist.gov/document/nistir7804-1werb100615pdf) for reserved patient identity and outdated-information cues; [dashboard guidance](https://analysisfunction.civilservice.gov.uk/policy-store/data-visualisation-building-and-managing-dashboards/) for task relevance and alternative formats; [WCAG hover/focus](https://www.w3.org/WAI/WCAG22/Understanding/content-on-hover-or-focus.html) and [dialog behavior](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/) for help accessibility. See the [evidence register](../../evidence/ux-and-interfaces.md#ux-pattern-research-2026-10-19).

## Information and visual hierarchy

Primary journey: sign in -> My panel -> patient/task -> assess -> compare -> decide/follow up. Monitoring and historical review remain available without initiating a new decision.

Use three information levels: essential facts/actions inline; explanations in contextual help; methods in the appendix. Never disclose patient identity, holds, important uncertainty, or action consequences only through help.

Use warm off-white backgrounds, white surfaces, dark slate text and restrained deep teal/navy accents. Start with 16px body text and an 8px spacing scale; use readable line lengths, clear headings and text-labeled statuses. Reserve strong colors for meaningful state, validate contrast, and respect reduced motion. Implement one component foundation rather than combining entire design systems.

## UI engineering skills

Apply [UI-SKILLS and engineering standards](../../execution/engineering-guidelines.md#ui-skills--portable-ui-guidance) throughout plans 01-06. Use the installed React best-practices, composition-patterns and web-design-guidelines skills selectively for the current runtime. Retain the existing NHS-informed design foundation, React/TypeScript and FastAPI; deployment is outside Vercel. Skill usage does not introduce Next.js or require a React upgrade. Source provenance and applicability limits are recorded in the [evidence register](../../evidence/ux-and-interfaces.md#ui-engineering-skills-2026-10-19).

## Acceptance

- Every existing UI requirement has a destination in the new views.
- Research claims and project design decisions are labeled separately.
- Prototype review includes panel, current decision, monitoring, history, and open-help layouts at desktop and narrow widths.
- No decorative score or chart is present without a decision-making purpose.
