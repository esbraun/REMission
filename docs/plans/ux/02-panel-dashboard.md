# Doctor panel dashboard

Status: implementation plan. Depends on [01](01-doctor-accounts-and-shell.md).

## Dashboard composition

My panel is an actionable patient worklist. Show total panel size, a refresh timestamp and compact linked counts: Needs review, Due, Data gaps. Count distinct owned patients, not tasks. Categories overlap and are labeled as overlapping; counts are not additive.

Needs review means an open service-created review task. Due means an open task due at or before the displayed cutoff. Data gaps means required-input readiness is incomplete. Counts use the same authorized snapshot as the list and state their denominator. Filtering updates the displayed-result count separately from whole-panel category counts.

| Default column | Content |
|---|---|
| Patient | Name and stable synthetic ID |
| Next task | Action, reason, owner and open-task count |
| Clinical state | Current care state |
| Learning state | Independent experiment/support state |
| Due | Due date/time or explicitly unscheduled |
| Data freshness | Latest required input/readiness; missing or stale explicitly |

Patient name opens Overview. Task link opens the exact task. A labeled open-task count opens all that patient's tasks with owner, status, due date and blockers. Expansion contains supplementary appointment and latest reported outcome details with dates/recall windows. Holds and blocking reasons stay inline. No bulk clinical actions.

## Ordering and interaction

Order by configured clinical-review priority, overdue tasks, upcoming tasks, then patients without pending work. Within a priority use due timestamp (missing last), task ID and patient ID for stable ordering. Configuration is versioned; no unvalidated model urgency score. The next task is the highest-priority open task, including blocked tasks that require review.

Use search by patient name/ID, category filters, appointment-date and clinical/learning-state filters and explicit sort controls. Authentication fixes clinician scope; there is no cross-doctor selector. Default to 25 patients per page. Persist non-sensitive filter/sort/page parameters in the URL and search text/scroll position in session state; do not put patient-name search strings into URLs. Restore context on return.

Expanded detail retains the original assignment status (pending review, approved, active block, outcome due or maintenance), latest ISI/report trend with date/recall window/missingness, and diary/Oura synchronization details. Essential missing-input reasons remain inline. No missing report is rendered as improvement.

Update safety/hold status immediately without moving rows under the reader. Offer an explicit refresh for newly ordered results. A refresh recalculates counts and ordering together. Show all task blockers even when no assignment is allowed.

## Narrow screens and failures

Use stacked rows on narrow screens, preserving identity, next task/owner, due date, hold and freshness. Secondary state details remain accessible without horizontal scrolling through core actions.

Provide loading, empty panel, no search results, stale data, partial failure and full failure states. Failed counts are unavailable, not zero. Display the last successful timestamp for retained stale data.

## Acceptance

Test multiple tasks on one patient, overlap among count categories, missing due dates, equal-priority ordering, overdue and held patients, no recent reports, large paginated panels, refresh while reading and restored list position. Patient selection must never mutate task state.

Sources: [Carbon](https://www.carbondesignsystem.com/building-blocks/core/components/data-table/guidelines), [GitHub filters](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/filtering-and-searching-issues-and-pull-requests). Count definitions and ordering are project choices.
