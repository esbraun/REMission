# Ux And Interfaces evidence

Use the [register rules](README.md). Original citations are retained; verification status is not upgraded by migration.

## UX pattern research 2026-10-19

The following official source passages were checked during the October 19 research turn. Each record has verification status `full-text-checked` for the cited passages, not an exhaustive product evaluation. Mutable pages without a publication year are identified as undated; the accessed revision is 2026-10-19. These are guidance/contextual examples and rationale, never quantitative inputs. Recheck on requirement change and before implementation/release reliance. Existing source records below retain their earlier verification status.

| ID | Citation and official locator | Supported claim | Requirements |
|---|---|---|---|
| ux-carbon | IBM Carbon Design System, *Data table guidelines*, undated; [Anatomy, Expandable, Pagination, Table toolbar](https://www.carbondesignsystem.com/building-blocks/core/components/data-table/guidelines) | Toolbar, sort, supplementary expansion and distinct targets support a worklist | UX-PANEL |
| ux-github | GitHub Docs, *Filtering and searching issues and pull requests*, undated; [Filtering by review status; Sharing filters](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/filtering-and-searching-issues-and-pull-requests) | Review filters and URL-preserved filter/sort state support returning to a queue | UX-PANEL |
| ux-govtasks | Government Digital Service, *Complete multiple tasks*, undated; [When to use; Show related actions; Show status](https://design-system.service.gov.uk/patterns/complete-multiple-tasks/) | Task lists support longer transactions across sessions with action labels and statuses | UX-WORKFLOW |
| ux-nhs | NHS digital service manual, *Design principles*, undated; [Be inclusive; Design for context; Test your assumptions](https://service-manual.nhs.uk/design-system/design-principles) | Inclusive consistent design and observed user testing guide the foundation | UX-FOUNDATION, UX-ACCEPTANCE |
| ux-apple | Apple Support, *View your data in Health on iPhone*, undated; [Highlights, trends and category details](https://support.apple.com/en-euro/guide/iphone/iphe3d379c32/ios) | Graph-to-detail navigation, time ranges and source access inform monitoring | UX-WORKFLOW |
| ux-cloudscape | Cloudscape Design System, *Help system*, undated; [Help and content ramp; Small, Medium, Large](https://cloudscape.design/patterns/general/help-system/) | Inline text progresses to contextual panels and deeper documentation | UX-HELP, UX-APPENDIX |
| ux-wcag-help | W3C WAI, *Understanding WCAG 2.2 SC 1.4.13*, living explanation; [Intent; Dismissible; Hoverable; Persistent](https://www.w3.org/WAI/WCAG22/Understanding/content-on-hover-or-focus.html) | Additional hover/focus content must meet the criterion's perceivability and dismissal conditions | UX-HELP |
| ux-dialog | W3C WAI, *ARIA Authoring Practices Guide: Dialog (Modal) Pattern*, undated; [Keyboard Interaction; Roles, States, Properties](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/) | Modal guides need focus containment, Escape behavior, labels and appropriate focus return | UX-HELP |
| ux-nist | Lowry et al., *NISTIR 7804-1: Technical Evaluation, Testing, and Validation of the Usability of Electronic Health Records*, 2015; [human-factors summary, page 48](https://www.nist.gov/document/nistir7804-1werb100615pdf) | Reserved patient identification and outdated-information cues support context safety | UX-FOUNDATION, UX-ACCOUNT, UX-ACCEPTANCE |
| ux-dashboard | Government Analysis Function, *Data visualisation: building and managing dashboards*, 2026; [Deciding whether to build; User needs](https://analysisfunction.civilservice.gov.uk/policy-store/data-visualisation-building-and-managing-dashboards/) | Dashboard content must meet identified user needs and have accessible alternatives | UX-FOUNDATION |

**Limits and assumptions for every entry:** these patterns require adaptation and intended-user testing; they do not establish clinical effectiveness or regulatory classification. Panel count definitions, ordering, authentication, colors, samples and acceptance thresholds are project decisions. Source principles do not justify adjacent invented clinical thresholds. See the [source-to-design matrix](../plans/ux/00-research-and-foundations.md) and [requirement map](../spec/requirement-map.md) for both directions of traceability.

## oura-api

- **ID:** `oura_api`.
- **Citation:** Oura. API documentation. Official documentation.
- **Type and role:** method, guidance or case study as identified in citation; rationale only.
- **Supports:** the source-specific statements in LEG-05; see the [requirement map](../spec/requirement-map.md).
- **Limits:** retain the population, estimand and setting limits stated in the consuming requirement; no synthetic coefficient is supplied by this entry.
- **Locator:** original citation above; precise section/page and canonical URL require verification unless supplemented below.
- **Verification:** carried forward from 2026-10-04 source list; not independently reverified during this migration.
- **Maintenance:** recheck on claim/method change and before a release relying on this source.

## smart

- **ID:** `smart`.
- **Citation:** HL7. SMART App Launch. Official implementation guide.
- **Type and role:** method, guidance or case study as identified in citation; rationale only.
- **Supports:** the source-specific statements in LEG-05; see the [requirement map](../spec/requirement-map.md).
- **Limits:** retain the population, estimand and setting limits stated in the consuming requirement; no synthetic coefficient is supplied by this entry.
- **Locator:** original citation above; precise section/page and canonical URL require verification unless supplemented below.
- **Verification:** carried forward from 2026-10-04 source list; not independently reverified during this migration.
- **Maintenance:** recheck on claim/method change and before a release relying on this source.

## nist7804

- **ID:** `nist7804`.
- **Citation:** NIST. Technical Evaluation, Testing and Validation of the Usability of Electronic Health Records, NISTIR 7804, 2012.
- **Type and role:** method, guidance or case study as identified in citation; rationale only.
- **Supports:** the source-specific statements in LEG-10, LEG-16; see the [requirement map](../spec/requirement-map.md).
- **Limits:** retain the population, estimand and setting limits stated in the consuming requirement; no synthetic coefficient is supplied by this entry.
- **Locator:** original citation above; precise section/page and canonical URL require verification unless supplemented below.
- **Verification:** carried forward from 2026-10-04 source list; not independently reverified during this migration.
- **Maintenance:** recheck on claim/method change and before a release relying on this source.

## nist7804-1

- **ID:** `nist7804_1`.
- **Citation:** NIST. Empirically Based Use Cases for Validating Safety-Enhanced Usability and Guidelines for Standardization, NISTIR 7804-1, 2015.
- **Type and role:** method, guidance or case study as identified in citation; rationale only.
- **Supports:** the source-specific statements in LEG-10; see the [requirement map](../spec/requirement-map.md).
- **Limits:** retain the population, estimand and setting limits stated in the consuming requirement; no synthetic coefficient is supplied by this entry.
- **Locator:** original citation above; precise section/page and canonical URL require verification unless supplemented below.
- **Verification:** carried forward from 2026-10-04 source list; not independently reverified during this migration.
- **Maintenance:** recheck on claim/method change and before a release relying on this source.

## ahrq-workflow

- **ID:** `ahrq_workflow`.
- **Citation:** AHRQ. Clinical Practice Improvement and Redesign: How Change in Workflow Can Be Supported by Clinical Decision Support.
- **Type and role:** method, guidance or case study as identified in citation; rationale only.
- **Supports:** the source-specific statements in LEG-10; see the [requirement map](../spec/requirement-map.md).
- **Limits:** retain the population, estimand and setting limits stated in the consuming requirement; no synthetic coefficient is supplied by this entry.
- **Locator:** original citation above; precise section/page and canonical URL require verification unless supplemented below.
- **Verification:** carried forward from 2026-10-04 source list; not independently reverified during this migration.
- **Maintenance:** recheck on claim/method change and before a release relying on this source.

## nhs-design

- **ID:** `nhs_design`.
- **Citation:** NHS. Design system and Design principles.
- **Type and role:** method, guidance or case study as identified in citation; rationale only.
- **Supports:** the source-specific statements in LEG-10; see the [requirement map](../spec/requirement-map.md).
- **Limits:** retain the population, estimand and setting limits stated in the consuming requirement; no synthetic coefficient is supplied by this entry.
- **Locator:** original citation above; precise section/page and canonical URL require verification unless supplemented below.
- **Verification:** carried forward from 2026-10-04 source list; not independently reverified during this migration.
- **Maintenance:** recheck on claim/method change and before a release relying on this source.

## nhs-accessibility

- **ID:** `nhs_accessibility`.
- **Citation:** NHS. Accessibility guidance for design.
- **Type and role:** method, guidance or case study as identified in citation; rationale only.
- **Supports:** the source-specific statements in LEG-10; see the [requirement map](../spec/requirement-map.md).
- **Limits:** retain the population, estimand and setting limits stated in the consuming requirement; no synthetic coefficient is supplied by this entry.
- **Locator:** original citation above; precise section/page and canonical URL require verification unless supplemented below.
- **Verification:** carried forward from 2026-10-04 source list; not independently reverified during this migration.
- **Maintenance:** recheck on claim/method change and before a release relying on this source.

## wcag

- **ID:** `wcag`.
- **Citation:** W3C. Web Content Accessibility Guidelines (WCAG) 2.2. Recommendation.
- **Type and role:** method, guidance or case study as identified in citation; rationale only.
- **Supports:** the source-specific statements in LEG-10, LEG-16; see the [requirement map](../spec/requirement-map.md).
- **Limits:** retain the population, estimand and setting limits stated in the consuming requirement; no synthetic coefficient is supplied by this entry.
- **Locator:** original citation above; precise section/page and canonical URL require verification unless supplemented below.
- **Verification:** carried forward from 2026-10-04 source list; not independently reverified during this migration.
- **Maintenance:** recheck on claim/method change and before a release relying on this source.

## tabs

- **ID:** `tabs`.
- **Citation:** W3C WAI. ARIA Authoring Practices: Tabs Pattern.
- **Type and role:** method, guidance or case study as identified in citation; rationale only.
- **Supports:** the source-specific statements in LEG-16; see the [requirement map](../spec/requirement-map.md).
- **Limits:** retain the population, estimand and setting limits stated in the consuming requirement; no synthetic coefficient is supplied by this entry.
- **Locator:** original citation above; precise section/page and canonical URL require verification unless supplemented below.
- **Verification:** carried forward from 2026-10-04 source list; not independently reverified during this migration.
- **Maintenance:** recheck on claim/method change and before a release relying on this source.

## gaf-dashboard

- **ID:** `gaf_dashboard`.
- **Citation:** Government Analysis Function. Data visualisation: building and managing dashboards, February 2026.
- **Type and role:** method, guidance or case study as identified in citation; rationale only.
- **Supports:** the source-specific statements in LEG-10; see the [requirement map](../spec/requirement-map.md).
- **Limits:** retain the population, estimand and setting limits stated in the consuming requirement; no synthetic coefficient is supplied by this entry.
- **Locator:** original citation above; precise section/page and canonical URL require verification unless supplemented below.
- **Verification:** carried forward from 2026-10-04 source list; not independently reverified during this migration.
- **Maintenance:** recheck on claim/method change and before a release relying on this source.

## gaf-testing

- **ID:** `gaf_testing`.
- **Citation:** Government Analysis Function. Data visualisation: testing dashboards for design and accessibility, 6 February 2026.
- **Type and role:** method, guidance or case study as identified in citation; rationale only.
- **Supports:** the source-specific statements in LEG-10; see the [requirement map](../spec/requirement-map.md).
- **Limits:** retain the population, estimand and setting limits stated in the consuming requirement; no synthetic coefficient is supplied by this entry.
- **Locator:** original citation above; precise section/page and canonical URL require verification unless supplemented below.
- **Verification:** carried forward from 2026-10-04 source list; not independently reverified during this migration.
- **Maintenance:** recheck on claim/method change and before a release relying on this source.

## gaf-uncertainty

- **ID:** `gaf_uncertainty`.
- **Citation:** Government Analysis Function. Communicating quality, uncertainty and change (supersedes the earlier "Communicating uncertainty and change"). The page indicated it was under review when accessed; pair it with the current dashboard guidance.
- **Type and role:** method, guidance or case study as identified in citation; rationale only.
- **Supports:** the source-specific statements in LEG-10; see the [requirement map](../spec/requirement-map.md).
- **Limits:** retain the population, estimand and setting limits stated in the consuming requirement; no synthetic coefficient is supplied by this entry.
- **Locator:** original citation above; precise section/page and canonical URL require verification unless supplemented below.
- **Verification:** carried forward from 2026-10-04 source list; not independently reverified during this migration.
- **Maintenance:** recheck on claim/method change and before a release relying on this source.

## harvest

- **ID:** `harvest`.
- **Citation:** Hirsch JS, et al. HARVEST, a longitudinal patient record summarizer. *Journal of the American Medical Informatics Association*, 2015.
- **Type and role:** method, guidance or case study as identified in citation; rationale only.
- **Supports:** the source-specific statements in LEG-10; see the [requirement map](../spec/requirement-map.md).
- **Limits:** retain the population, estimand and setting limits stated in the consuming requirement; no synthetic coefficient is supplied by this entry.
- **Locator:** original citation above; precise section/page and canonical URL require verification unless supplemented below.
- **Verification:** carried forward from 2026-10-04 source list; not independently reverified during this migration.
- **Maintenance:** recheck on claim/method change and before a release relying on this source.

## codesign

- **ID:** `codesign`.
- **Citation:** Co-design of an Electronic Dashboard to Support the Coproduction of Care in Pediatric Rheumatic Disease: Human-Centered Design and Usability Testing. *Journal of Participatory Medicine*, 2022.
- **Type and role:** method, guidance or case study as identified in citation; rationale only.
- **Supports:** the source-specific statements in LEG-10; see the [requirement map](../spec/requirement-map.md).
- **Limits:** retain the population, estimand and setting limits stated in the consuming requirement; no synthetic coefficient is supplied by this entry.
- **Locator:** original citation above; precise section/page and canonical URL require verification unless supplemented below.
- **Verification:** carried forward from 2026-10-04 source list; not independently reverified during this migration.
- **Maintenance:** recheck on claim/method change and before a release relying on this source.

## fda-cds

- **ID:** `fda_cds`.
- **Citation:** FDA. Clinical Decision Support Software: Guidance for Industry and Food and Drug Administration Staff. Issued January 29, 2026; supersedes the version issued January 6, 2026, which superseded the 2022 guidance.
- **Type and role:** method, guidance or case study as identified in citation; rationale only.
- **Supports:** the source-specific statements in LEG-10; see the [requirement map](../spec/requirement-map.md).
- **Limits:** retain the population, estimand and setting limits stated in the consuming requirement; no synthetic coefficient is supplied by this entry.
- **Locator:** original citation above; precise section/page and canonical URL require verification unless supplemented below.
- **Verification:** carried forward from 2026-10-04 source list; not independently reverified during this migration.
- **Maintenance:** recheck on claim/method change and before a release relying on this source.

## UI engineering skills 2026-10-19

These are engineering guidance sources, not clinical evidence. Reviewed 2026-10-19 and installed from agent-skills commit `063bee94c3f4df8453406c830b0a7df0f2860278`; [local provenance and applicability](../execution/engineering-guidelines.md#installation-and-provenance).

| Source ID | Source and inspected material | Application and limits |
|---|---|---|
| ux-agent-react | [React best practices](https://github.com/vercel-labs/agent-skills/blob/063bee94c3f4df8453406c830b0a7df0f2860278/skills/react-best-practices/SKILL.md); async-parallel, derived-state-no-effect and dynamic-import rules | Portable fetching/state/loading guidance; Next.js-specific APIs do not require adopting Next.js; no premature cache or optimization mandate |
| ux-agent-composition | [Composition patterns](https://github.com/vercel-labs/agent-skills/blob/063bee94c3f4df8453406c830b0a7df0f2860278/skills/composition-patterns/SKILL.md); avoid-boolean-props and explicit-variants rules | Simple composition and explicit variants; no mandatory provider framework or incompatible React API changes |
| ux-agent-web | [Web design skill](https://github.com/vercel-labs/agent-skills/blob/063bee94c3f4df8453406c830b0a7df0f2860278/skills/web-design-guidelines/SKILL.md) and [fetched web rules](https://github.com/vercel-labs/web-interface-guidelines/blob/434b7f91364665f2f733b310ec54809bf8f37937/command.md) | Accessibility and interface review; domain holds, readable identity/blockers and appropriate URL state override generic recommendations |

The web rules were fetched on 2026-10-19 at revision `434b7f91364665f2f733b310ec54809bf8f37937`. Fetch fresh rules before each later web review and record revision or content hash/date; the installed skill's pin does not freeze this separate source. Engineering standards on reuse/testing are project decisions, not claims of proven clinical effectiveness or blanket compliance with every upstream rule.
