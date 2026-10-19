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
| UX-T02 | Logout/expiry and delayed responses: no previous doctor's or patient's content becomes active |
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

## Human-factors work

Plan two formative rounds targeting five doctors each; this is an engineering study choice, not a statistically sufficient validation claim. Include the existing nurse and behavioral-care workflow reviews and clinical review of wording/actions. Record participant roles, scenarios, observed errors, completion time, help use and post-task ease.

Tasks include finding the correct patient needing review, identifying the next task and owner, interpreting an inconclusive comparison, recognizing a hold, completing a decision, reviewing concurrent learning, restoring historical context and using help without losing work.

Any wrong-patient action, historical write, hidden blocker or misleading evidence is a release-blocking finding. Fix and repeat affected tasks. Remaining findings require recorded severity/disposition before acceptance.

## Evidence and rollout

Keep synthetic-engineering, human-factors, clinical-review and clinical-validation statuses separate. Attach actual test runs and observations to requirements. Initial rollout is synthetic-only, with provisioned demo accounts and explicit demonstration labeling. No production clinical release is authorized by this package.

Before integration acceptance, rerun adversarial review against implemented behavior and record unresolved findings. The [existing plan review](07-adversarial-review.md) is not implementation validation.
