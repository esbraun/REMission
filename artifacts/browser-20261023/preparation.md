# Deployed physician browser verification preparation

Status: prepared; no deployed browser/network/credential activity yet.

- Owner: `/root/cloud_browser_sol`, root-verified Sol/high.
- Checkout: `C:/Users/erics/Documents/Projects/REMission-worktrees/cloud-browser-sol-261023`.
- Branch: `test/poc-cloud-browser-20261023`.
- Verified HEAD: `286aa87a10a24ad9925c90be033e7d8c0570d99b`.
- Browser: exclusive Playwright MCP ownership; tooling schemas discovered, startup/browser/version unverified until BROWSERGO.
- Proposed origin is not treated as observed or trusted. No TLS override is allowed.
- Root coordinated ordinary-family seed: `20261023`, set through the visible seed control; retain the untouched default patient count12. Select an eligible actual generated patient if the initial patient is held. Operations will not generate/advance this browser flow.
- Capture a representative actual cloud physician-superuser screenshot from the verified flow, with clear patient context and synthetic label plus decision/outcome/history where the existing layout permits. Preserve origin/UTC/viewport provenance; no mockup or redesign.

## Bounded cases

| Case | Expected visible behavior | Evidence |
| --- | --- | --- |
| B03 / CS-T3 | Ordinary trusted HTTPS navigation reaches synthetic sign-in; wrong password and unknown account reject generically; correct account reaches owned panel | Sanitized snapshots and noncredential screenshot; never capture filled password form |
| B05a / CS-T5 | Ordinary behavioral panel defaults to count12; generate exact coordinated seed; visible group/patient selection shows owned synthetic identities | Panel snapshot, seed/count/panel IDs, desktop screenshot |
| B05b / CS-T5 | Opening an eligible patient assigns nothing; no option selected; inspect observations and unavailable comparison; explicit eligible choice, rationale, review, confirmation save immutable history | Before/summary/history snapshots; patient/decision/bundle/version/rationale/clock metadata |
| B05c / CS-T5 | Return current, advance to day14 via visible control, inspect missing-report gaps, chart text/table values, actual delivery versus approval, later outcomes distinct from saved as-known-then | Day14 snapshot/screenshot, observations and unchanged historical display hash |
| B05d / CS-T5 | Sign out removes patient content; second physician sees own panel only and first physician deep links reveal no patient content; second-account panel generation only if root coordinates it | Account-scoped snapshots and negative deep-link result; API isolation is operational lead coverage |
| B06 / CS-T6 | Reload preserves saved panel/decision/rationale/day14/outcomes/history; pause mutation for root-coordinated service recreation/reboot; afterward re-login/reopen/history compare and next visible advancement succeeds | Before/after IDs, displayed integrity hash, observed time/plan/outcome table comparison; lead owns durable store/API comparison |
| B07 / CS-T7 | Keyboard reaches and activates flow controls with visible focus; desktop and narrow layouts preserve context/boundary labels and usable chart/table alternatives; exposed analysis remains unavailable/no-result without submitting jobs | Desktop/narrow screenshots, keyboard observations, console and selected request failure summary |

Use current accessibility references after each state transition. Core mutations use actual visible controls, never API substitutions or page DOM mutation. No analysis request/job submission, fit/training, hold/stale mutation injection, service manipulation or private database access is owned here. Lead owns bounded count/replay/causal-path integration checks, stale/ineligible API rejection, CSRF/cookie/session expiry/reset and runtime/resource proof.

## Credential and evidence handling

Await root BROWSERGO and one exact read-only ACL-private credentials artifact path/schema. Only that artifact may be read, using the Playwright MCP server process and semantic visible form fill. Never print credentials, return field values, include secrets in tool arguments or write credentials to this checkout. Do not inspect root env, global config or credential stores. No evidence screenshot/snapshot while a secret-bearing form is filled. Do not save raw request headers/body or cookies. Sanitize console/selected network results before durable storage.

All generated reports/screenshots/snapshots/manifests are confined to this checkout's `docs/implementation/evidence/cloud-browser-20261023/`. Capture actual observed browser/MCP versions if supported; otherwise record the exact unavailable field. Bind deployment source/image/configuration identity from root's nonsecret handoff. Record UTC, viewport, seed, versions, expected/actual outcome and file hashes. Do not label local source inspection as deployed proof or synthetic engineering checks as human/clinical acceptance.

The installed web-design skill was read. Its required fresh upstream rules fetch is deferred until BROWSERGO because root currently prohibits network requests. Record retrieval date and content hash when fetched; report a fetch failure as a limitation.
