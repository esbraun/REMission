# Browser Validation

Read [execution entry point](../../implementation-prompt.md) and your assigned gate bundle first. This document governs future application implementation, not the documentation migration.

## Playwright MCP setup and ownership

Use the official [Microsoft Playwright MCP](https://github.com/microsoft/playwright-mcp) documentation, reviewed at README blob `7cecc4144025919587399336dff41b0d3ba366ad`. It recommends accessibility snapshots for interaction and explains that concurrent persistent profiles can conflict. The upstream README also discusses a CLI alternative; this project explicitly requires **MCP** for agent browser validation. Playwright Test adds repeatable regressions, rather than replacing MCP exploration.

The upstream bootstrap command for Codex is:

```sh
codex mcp add playwright npx "@playwright/mcp@latest"
```

For a reproducible run, choose and record an actual verified package version instead of leaving `latest` unpinned. If the harness uses a JSON MCP configuration, adapt this template to its documented location:

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": [
        "@playwright/mcp@<verified-version>",
        "--headless",
        "--isolated",
        "--output-dir",
        "artifacts/playwright-mcp"
      ]
    }
  }
}
```

The version placeholder must be resolved before running. Install the selected browser/runtime prerequisites according to that version's documentation and verify startup; do not assume package installation proves a browser works. Inspect actual MCP schemas because tool prefixes, capabilities, and parameters vary. Do not use unrestricted file access or weaken browser isolation as a routine workaround.

Delegate setup and the browser smoke check to a tooling/browser worker. If subagents inherit one shared MCP session, serialize browser tasks through a single browser worker. `--isolated` alone does not give two workers independent tabs when they share the same session. True parallel browser tasks need distinct MCP sessions plus isolated contexts or distinct profiles, separate artifact paths, and preferably separate seeded backend instances. Record that ownership in the ledger.

The browser worker also uses its own Git worktree pinned to the candidate/integration commit. Start validation services from that checkout and keep generated evidence in its assigned artifact paths. A separate worktree does not isolate MCP sessions, ports, or backend state; retain the session ownership and fixture coordination rules above. Return defects through the orchestrator for assignment to a Sol worker's separate worktree.

Start the actual app and service from their documented commands. Record URLs, health-check results, integration commit, fixture seed, replay cutoff, and relevant data/model/policy versions. Validate the integrated app against its real local service, not a detached static prototype. Seed/reset data through a documented synthetic-test interface and verify important UI actions in persistent service records.

### Browser worker prompt

```text
Validate UI task <ID> at <URL> using the connected Playwright MCP tools.
Read docs/spec/06-service-and-ui.md, the human-factors portion of
docs/spec/07-validation-protocol.md, and the assigned story in
docs/spec/08-gates-and-release.md plus exact task acceptance criteria.
Use your own Git worktree <absolute path> at integration commit <commit>,
seed <seed>, and cases <IDs>. Verify checkout root and HEAD. Own browser
session <session>; do not race another worker's navigation or mutate shared
fixtures without coordination.

Discover tool schemas. Navigate to the app, obtain an accessibility snapshot,
and interact with visible controls using current snapshot references. Refresh
the snapshot after navigation/state changes; do not guess stale element refs.
Typical tools are browser_navigate, browser_snapshot, browser_click,
browser_press_key, browser_resize, browser_take_screenshot,
browser_console_messages, and browser_network_requests; use the actual names.

Verify both visible behavior and persisted service state. Inspect screenshots
for clipping, density, banners, and charts; a successful click is not a visual
check. Use keyboard interactions for the keyboard task. Do not pass a workflow
by invoking a hidden mutation from browser evaluation instead of its UI control.
Use state-based waits and recorded expectations rather than arbitrary sleeps.

Exercise normal, empty, loading, missing-data, error, clinical-hold, historical,
and stale-version paths. Record unexpected console/network failures, screenshots,
accessible-tree evidence, expected/observed results, and reproduction steps.
Send defects through the orchestrator to the implementation worker and verify repairs. Return
pass/fail/blocked for each case, artifact paths, versions, and untested scope.
```

Apply [TEST-QUALITY](engineering-guidelines.md#test-quality--tests-that-detect-meaningful-failures) and the [UX verification layers](../plans/ux/06-validation-and-integration.md#verification-layers). Every matrix row below remains required; combine coherent workflows without omitting behavior. Use the installed web-design skill during UI review, recording the fetched rule revision/date and project-specific exceptions.

### Required integrated browser matrix

| Cases | Required checks |
| --- | --- |
| Clinic and selected-patient dashboards | Patient identity, synthetic label, current/historical context, phase, task owner/due date, count denominators and timestamps, filters, missing reports, separate clinical/learning states |
| Assessment and cold start | Required inputs block premature ranking; inspect compatible evidence, broad modifier uncertainty, prior-only labels, heterogeneity/no-borrowing sensitivity, and endpoint/horizon/direction/interval labels |
| Treatment and all section 12 stages | Enumerate every stage row, including active treatment without a decision, eligibility/design, active block, interim/final review, escalation, support review, hold, and maintenance; stable navigation and required content groups distributed across task-local views; appropriate controls and failure states |
| Treatment choice and consent | No recommendation preselected; approval summary and follow-up persist; treatment choice distinct from randomization; missing, expired, and withdrawn consent block relevant assignments and expose the next review step |
| Reversible and durable care | Carryover/rebound/washout/rescue/incomplete outcomes visible; frozen support-policy version; no manual winning-block choice presented as unchanged randomization; durable escalation not on/off CBT-I |
| Support envelope | Permitted actions, probabilities/bounds, availability, burden, reward missingness, and proximal/distal distinction visible; no medication or oncology optimization control |
| Holds, abstention, and failures | Interaction exclusion versus prescriber-review flags; acute concern hold with owner; sparse overlap suppresses superiority claims; no successful-looking substitute when fitting/ingestion fails |
| Wearable/report discordance | Distinct sources and units, missing nights as gaps, version changes, accessible table alternatives, and explanation of quiet-wake bias; no readiness score used as diagnosis or acute-illness detector |
| History and correction lineage | Navigate previous/next decision; old stage renders; banner and cutoff persist through deep-link refresh; as-known-then excludes late uploads/later outcomes; retrospective outcomes separate; no old approval controls; new fits/corrections leave original snapshot unchanged |
| Context/concurrency | Reject delayed responses after logout/expiry and same-doctor reauthentication; switch patients with an open draft: clear it before re-enabling controls; inject a material clinical update during approval through the seeded test interface: server rejects stale version and UI requires specific refresh/review without silent approval |
| Accessibility and responsive layout | Keyboard completion, focus order/visibility, accessible tab semantics, labels, contrast, zoom/reflow, narrow/desktop viewports, non-color statuses, and chart tables; manual screen-reader/accessibility checks recorded separately |

Map these checks to all thirteen human-factors tasks in the [validation protocol](../spec/07-validation-protocol.md) and the eight [demonstration stories](../spec/08-gates-and-release.md). Also test the deliberately unsupported recommendation case in the synthetic test environment: the interface must permit the user to decline it and inspect its limitations. It must not be a production source of fabricated evidence.

Browser evidence should identify task/case, commit, browser and MCP versions, viewport, seed, data/model versions, replay time, steps, expected/observed behavior, outcome, screenshots/snapshots, console/network findings, and persisted-record references. Capture evidence after the last relevant repair. If backend, model, seed, or UI changes invalidate a result, rerun the affected checks on the final integrated commit.

MCP provides exploratory workflow evidence. Add reproducible Playwright Test checks for patient switching, stale approval, historical deep links, consent blocking, and keyboard assignment. Keep invariant tests at the service boundary too: disabling a button does not enforce a clinical constraint. A clean accessibility tree or an automated scanner does not establish WCAG conformance or clinician comprehension.
