# Deployed physician UI verification

Status at 2026-10-23 05:17 UTC: assigned browser cases complete. Both frozen day14 baselines matched after root-reported service recreation and actual guest reboot; one subsequent physician1 advancement reached day15 and left original history unchanged. No more patient mutations are planned.

## Identity and scope

Exclusive Playwright MCP owner `/root/cloud_browser_sol`, root-verified `gpt-6.1-sol`/high. Current worktree `C:/Users/erics/Documents/Projects/REMission/artifacts/bw`, branch `test/poc-browser-mcp-short-20261023`, verified HEAD `286aa87a10a24ad9925c90be033e7d8c0570d99b`. Browser version `156.0.8078.48`; MCP package version is not exposed by the available tool metadata and was not inferred from another installation. Actual origin `https://34.59.176.42`. Ordinary navigation rendered the app without an interstitial or a requested TLS override; root supplied independent default-CA/IP verification and TLS1.3 proof.

Root supplied exact deployed identities: app digest `sha256:a950cdb0dd9b3bbdeb176c6da71903180406a9bf2160ea3d23faf4be3c0f5e72`; generator digest `sha256:d64907d76a2810d2e6cad8acaa012f3df132ced69bfe2636c7eb07f7090b4eee`; Caddy digest `sha256:04913b1da43339a40ad1ea87827d70a576ac5aa6cf674c6e24fdca675887533a`; configuration manifest SHA256 `caef64ea9b0c03525f25aea35dfc3589d0b19ce6c449afc753d7554846201f45`. Root owns VM/API/persistence/session-expiry/reset/resource verification.

Core generation, selection, choice/rationale/review/confirmation and advancement used actual visible controls through Playwright MCP. Read-only response observation on UI reload supplied whitelisted saved-state identifiers and observations; it did not substitute API calls for physician actions. No analytics submission, fitting/training, hidden mutation, source repair or clinical acceptance occurred.

## Observed results

| Case | Result | Evidence |
| --- | --- | --- |
| CS-T3 browser trust/sign-in | Pass for ordinary HTTPS render, unknown-account rejection, real-account wrong-password rejection and successful real UI login for both physicians | Initial observation; cleared sign-in snapshot; expected 401 request/console records; protected tool transcript returns booleans only |
| CS-T5 default seeded panel | Pass. Each physician initially owned0. Ordinary family and default count12 unchanged; visible seeds20261023/20261024 generated12 and loaded distinct owned panels | `04`, `19`, `20`; API status list shows exactly two generation POSTs |
| CS-T5 explicit decisions | Pass. Both tested patients initially had zero checked radios. Explicit eligible escalation for physician1 and continuation for physician2; rationale, follow-up, review and separate confirmation persisted | `05`, `06`, `07`, `21`; both baseline JSON files |
| CS-T5 simulation/outcomes/history | Pass for day0-to14 via visible control. Reports/gaps, actual delivery versus approval, ISI assessment points and tables shown; history remains read-only/as-known-then with unchanged integrity hashes | `08`, `10`, `11`, `12`, `21`; both baseline files |
| CS-T5 ownership | Pass for visible list/detail isolation in both directions. Other-owner patient/draft reads returned404; UI showed generic Resource not found, no other patient heading, clock or advancement controls | `17`, `18`, `19`, `20`, `22`; expected 404 statuses |
| CS-T5 absent analytics | Pass for honest no-result view and no submission. Analysis view says no compatible accepted stored summary and no saved attempts; comparison supplies no ranking and decision remains available | `05`, `09`; API list has only GET analyses/analysis-sources, no analysis POST |
| CS-T6 reload | Pass for history reload/hash equality and current day14/decision/rationale restoration; both whitelisted baseline captures follow UI reload | Baseline JSON files; history hash observations |
| CS-T6 recreation/reboot | Pass for combined post-recreation/reboot UI readback. Fresh UI logins for both owners restored exact saved state before mutation; root separately owns the actual recreation/reboot and individual API/disk comparisons | `23`, `24`, `25`, `26` |
| CS-T7 keyboard | Pass for first-Tab skip link, Enter-to-main, next Tab username; radio ArrowDown, Tab-to-rationale, keyboard text entry, Enter review, Tab traversal through datetime segments to confirmation, Space confirmation and Space advancement. Dirty draft disabled advancement | `02`, `06`, `16`; observed tool results |
| CS-T7 desktop/narrow | Pass for bounded visual inspection at1440x1000 and390x844. Patient identity/synthetic labels wrap legibly; page width390 at narrow viewport; charts describe gaps and have observation tables. Table containers intentionally scroll680px within324px; focused wrapper ArrowRight moved scrollLeft0-to200 with visible focus | `02`, `03`, `10`, `12`, `13`, `15`, `16` |
| CS-T7 console/network | Expected negative-case errors only in reviewed output: two login401 and six cross-owner patient/draft404; no JavaScript exception or warning observed. One logout request lacks terminal status after subsequent navigation; no revocation claim is based on it | Sanitized console/API status files; root independently owns old-session rejection |

Two-owner mutation rejection, stale/ineligible API rejection, cookie/CSRF/origin, expiry/reset, count/replay/causal-path coverage and runtime fit are operational-lead tests. This browser report does not pass those rows by inference. Automated accessibility exploration does not establish WCAG conformance or human/clinical acceptance.

## Saved-state baseline

| Field | Physician1 | Physician2 |
| --- | --- | --- |
| Patient | `POC-0bb7b661339c45b0b23ec0c6b029a71d` Synthetic Jordan09 | `POC-05a4fb3106e74baeb9f411ec1fa28969` Synthetic Casey11 |
| Panel | `panel-35a135b698364b71b387ec4f22f9e6b2` | `panel-dd80bf64a6204b6f992bc11e4c5292e5` |
| Seed/index/day | 20261023 /8 /14 | 20261024 /10 /14 |
| Choice | behavioral_escalate | behavioral_continue |
| Current decision | `decision-97476314927fd83b62341b1d63064461` | `decision-9437a36e6aba4ab33776ebe86c64cc4a` |
| Versions patient/state/eligibility/consent | 3/3/3/1 | 3/3/3/1 |
| Cutoff | 2026-01-15T12:00:00Z | 2026-01-15T12:00:00Z |
| Approval | `approval-a9431f4f56c24424be8912ea2cc8b2ff` | `approval-b8cd434cb703446983384c0f756dde6d` |
| Display SHA256 | `bbaecb64042c5823466ed670bda351082e8eca7dc49fdc3b7840033bc39ebb56` | `7eeb7407aeb819f1b8484177cae7b3c0435f5c6153545625ab8ccb3b99c0ecf2` |
| Reports observed/missing | 11/3 | 13/1 |
| ISI day0/day14 | 16/14 | 16/15 |

Both use `poc-longitudinal-v1`, origin2026-01-01T12:00Z and horizon84. These are functional physician demonstrations using different seeds, not a matched causal response comparison. Physician1 later outcomes show14 daily reports and1 ISI separately from the original single observation; original display/hash are unchanged.

## Representative screenshot provenance

`10-representative-physician-history.png`: actual browser screenshot, 2026-10-23T04:55:23Z, CSS viewport1440x1000/full-page1440x1750, origin above, physician1 history path ending `approval-a9431f4f56c24424be8912ea2cc8b2ff`. Visually inspected: patient/current-versus-historical context, explicit choice/rationale/follow-up, immutable hash, synthetic boundary and later-outcome separation are visible. No credential form is present. `12-day14-overview-desktop.png` separately shows actual day14 trajectories/delivery/plan/tables. No redesign or image generation was used. Minor nonblocking density: the historical table's Type header wraps within its narrow column at desktop; values remain readable.

## Tooling restrictions and corrected probes

Initial assigned sibling worktree was rejected by MCP output allowed-roots policy. Root provisioned the current exclusive worktree inside the existing allowed workspace, without widening provider config/ACLs. Only this worker's generated nonsecret default artifacts were copied as inputs. Standard server `require`/`process` were unavailable and dynamic import lacked a callback. A documented filename-loader probe echoed its complete nonsecret source; no private code was created.

Root then explicitly authorized a bounded standard temporary local-file-page method after a nonsecret probe confirmed in-memory parsing, closed temporary page and unchanged main page with no body echo. One exact credential input copy was placed in a gitignored, owner/SYSTEM-only, read-only private directory. Every secret read closes the temporary page before the main visible login fill/submit; no private body, screenshot, snapshot, request details, credential literal or secret hash is part of evidence. Private files are excluded from the manifest and Git.

Two locator expectations were corrected without repeating mutations: the first panel wait used a shorter exact string than the actual explanatory paragraph, while generation had succeeded; the second login expected My panel although the app preserves the prior patient route, while login200 and the generic ownership-denied screen showed actual success. Both failures remain disclosed; successful later observations supply the result. No repeated panel generation or credential reset occurred.

Installed web-design skill read; fresh official upstream rules fetched2026-10-23, raw copy SHA256 `d246b026f4f29b5823a9cc857f9edf3d2507002e055e32040cadeaf3b38e0234`. Review remains bounded to enabled workflow and project-specific synthetic boundaries; unrelated stylistic suggestions were not applied.

## Post-restart readback and continued operation

After root AFTERRESTARTGO, the browser reloaded the existing physician1 view. Its newer browser session remained authenticated; that is separate from the original session whose genuine1800-second expiry the operational lead verified. Explicit logout completed200, followed by fresh UI login. Physician1 comparison at05:14:44Z and physician2 comparison at05:15:11Z each matched all eight captured groups: patient ID/name, full simulation, current decision/versions/cutoff, plan/rationale, history, all32 whitelisted projected records, and tasks. Each historical display retained its original hash, exactly one original observation and no approval control. Both comparisons completed before the next patient mutation. These UI checks occurred after both operational steps; they do not independently establish equality at the intermediate recreation-only point. Root owns that API/runtime evidence.

The sole subsequent mutation was physician1's visible Advance1day button at05:15:44Z, returning200 and day15. Current decision became `decision-7d1537b16406fb79b40b8010f254d552`; patient/state/eligibility versions4, consent1, cutoff2026-01-16T12:00:00Z. The plan/rationale/assignment were unchanged;15 reports include12 observed and3 missing, with15 delivery records. Physician2 remains at its saved day14 baseline. Reopening physician1's original history after this advancement still showed hash `bbaecb64042c5823466ed670bda351082e8eca7dc49fdc3b7840033bc39ebb56`, read-only context and one original observation. See `27` through `30`.

Final representative real cloud screenshots, both captured and visually inspected at05:16 UTC with1440x1800 CSS viewport: `29-actual-cloud-physician-day15.png` shows patient context, synthetic boundary, day15 reports/gaps and outcome trajectories; `31-actual-cloud-physician-saved-history.png` shows the explicit choice/rationale/follow-up, original cutoff and unchanged saved-history integrity. The former uses the same `/overview` path as the selected patient; the latter uses the original approval history path. Neither contains a credential form. Source origin is `https://34.59.176.42`; these are direct browser pixels, without image generation or layout editing.

Final console review still contains only the eight expected earlier negative-case HTTP errors and no new JavaScript error or warning. Final API request status inventory establishes no analysis POST. Pre-restart baseline physical SHA256 values remain unchanged: physician1 `8ad3d0b937ea1a35839b8dbd1492f82d553b68ed05902afa2b43d82ba55f0ef0`, physician2 `ffc4eed8670c1ee86f9588b9dc28f150636600c414571b643986947bc93205d2`; raw Git blobs `0e6b34708388d286d121679ff228e50da4d3a13c` and `6e332df439885f099561eddd44c1202f345bf23a`.

Public UI rule source: <https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md>. No human-factors, WCAG, scientific, clinical or complete release acceptance is inferred from these synthetic browser checks.

Packaging checks: the first PowerShell integrity-check invocation had a parser error before execution and was corrected; the executed scoped validation passed. A whole-package whitespace check flagged verbatim MCP request-list trailing spaces and raw Windows CRLF bytes. Those raw artifacts were preserved, and the authored report/README/probe whitespace check was scoped separately. SHA256/size bindings and private-input exclusion are the evidence acceptance checks; no browser case was repeated for these harmless packaging failures.
