# UX validation and integration

Status: planned tests, not executed application acceptance. Define fixtures/tests early; final integrated acceptance follows plans 01-05.

## Interfaces and integration

Implement typed session/principal, panel-summary, task, decision-context, draft, result-availability and documentation-version contracts. Preserve independently represented clinical/learning/readiness states and server-derived permissions. Use authenticated ownership for every resource, including aggregate and job-result access.

Map UX-FOUNDATION, UX-ACCOUNT, UX-PANEL, UX-WORKFLOW, UX-HELP, UX-APPENDIX and UX-ACCEPTANCE to the canonical service specification and this package. Update root navigation, evidence register, revision history and G5 traceability. Existing domain requirements remain mandatory.

G0 acceptance precedes detailed design and the thin service shell. Fixtures may support prototypes but cannot count as accepted model outputs. G5 requires actual G2-G4 engines and saved-output rendering checks. G6/G7 and separate human/clinical gates remain unchanged.

## Automated and manual scenarios

| Test ID | Scenario and expected result |
|---|---|
| UX-T01 | Two doctor panels: reject cross-owner URL/API, history, draft, aggregate and job-result access |
| UX-T02 | Logout/expiry, password reset and delayed responses: session revocation works; no stale content becomes active, including after same-doctor reauthentication |
| UX-T03 | Multiple tasks, holds, overdue and unscheduled tasks: stable priority, accurate distinct-patient counts and complete task discoverability |
| UX-T04 | Panel navigation: filters/page/scroll restored; safety changes visible without automatic row movement |
| UX-T05 | Every workflow stage: only authorized actions, no navigation-driven state transition |
| UX-T06 | Missing/pending/undefined/failed/inconclusive evidence: distinct rendering, exact units/horizon/interval and no fabricated winner |
| UX-T07 | Death/admission interruptions and sparse reports: separate outcomes, recall windows, conditional populations and visible gaps |
| UX-T08 | Draft save/discard/cancel, refresh and expiry: context isolation and version-aware explicit resume |
| UX-T09 | Double submission, lost response and changed state: idempotent recovery and review of material changes |
| UX-T10 | Historical links/reload: immutable as-known-then data; later outcomes separate and no write controls |
| UX-T11 | Keyboard, screen reader, touch, 200%-400% zoom/reflow: operable task/help flows, visible focus and chart tables |
| UX-T12 | Guide/appendix topics, anchors and versions: correct context, preserved draft and accessible focus return |
| UX-T13 | Empty, no-results, stale, partial and failed service states: unavailable values never rendered as reassuring zero |
| UX-T14 | Monitoring: aligned dated sources, treatment/phase lanes, coverage/device changes and source-event access |

Automated browser checks complement manual accessibility testing and visual inspection. Inspect desktop and narrow-screen renders with realistic long names, multiline blockers and open help.

## Verification layers

Apply [TEST-QUALITY](../../execution/engineering-guidelines.md#test-quality--tests-that-detect-meaningful-failures). This assignment preserves every UX scenario and the complete integrated browser matrix; it is not permission to replace browser behavior with mocked service checks. Tests assert observable results and persisted effects, not implementation details.

| Scenarios | Primary checks and complementary verification |
|---|---|
| UX-T01/02 | Real-route integration: cookies, CSRF, ownership across all resources, expiry/reset revocation; UI integration/browser: switch, logout, Back, same-doctor reauthentication and delayed responses; unit seam: context/auth-generation rejection |
| UX-T03/04 | Unit seams: priority and distinct-patient counts; integration: panel aggregates; browser: discover all tasks, restore filters/page/scroll, show changed safety state without row movement |
| UX-T05 | Unit seams: domain eligibility/readiness; service integration: unauthorized actions denied; browser: each workflow stage, consent blocking and navigation without transitions |
| UX-T06/07 | Unit seams: availability/estimand/cutoff mapping; integration: saved-output contract; browser: distinct evidence states, exact labels, interruptions, gaps and no fabricated winner |
| UX-T08/09 | Unit seam: draft base-version checks; service integration: atomic approval/follow-up, original-key idempotent recovery, stale hold/version rejection; browser: save/resume/discard/cancel and uncertain submission |
| UX-T10 | Integration: immutable snapshots, late data excluded, writes denied; browser: historical deep links/reload remain read-only and later outcomes stay separate |
| UX-T11/12 | Component integration: focus, guide context, draft retention; browser: keyboard/help flows and topic links; manual: screen reader, zoom/reflow, touch and visual inspection |
| UX-T13/14 | Service/component integration: unavailable versus zero, source alignment/provenance; browser: empty/error/partial states, monitoring lanes, selected dates and chart-table agreement |

Use isolated fixtures, controlled clocks and explicit deferred responses to reproduce races. Real API/storage workflows remain unmocked except for explicit fault injection. Each test identifies the regression it would catch. Keep manual and statistical gates separate; do not use snapshot counts, coverage percentages or retries as evidence of correctness.

## Human-factors work

Plan two formative rounds targeting five doctors each; this is an engineering study choice, not a statistically sufficient validation claim. Include the existing nurse and behavioral-care workflow reviews and clinical review of wording/actions. Record participant roles, scenarios, observed errors, completion time, help use and post-task ease.

Tasks include finding the correct patient needing review, identifying the next task and owner, interpreting an inconclusive comparison, recognizing a hold, completing a decision, reviewing concurrent learning, restoring historical context and using help without losing work.

Any wrong-patient action, historical write, hidden blocker or misleading evidence is a release-blocking finding. Fix and repeat affected tasks. Remaining findings require recorded severity/disposition before acceptance.

## Evidence and rollout

Keep synthetic-engineering, human-factors, clinical-review and clinical-validation statuses separate. Attach actual test runs and observations to requirements. Initial rollout is synthetic-only, with provisioned demo accounts and explicit demonstration labeling. No production clinical release is authorized by this package.

Before integration acceptance, rerun adversarial review against implemented behavior and record unresolved findings. The [existing plan review](07-adversarial-review.md) is not implementation validation.
