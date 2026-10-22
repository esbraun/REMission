# POC-1–3 merged verification

Postmerge verification passed on accepted merge `a7ab7e60a8146ace6342efd8d51a0bd1013566ad`, parents `439ebaa298882777a1f11b2573b689c42cd7e6fe` and reviewed candidate `17c6e8b9e4a221ea7017daaeb21dd4c3dfcc5f52`. Both merged and candidate trees are `990948a36fd0910128226f00911b1942d3286989`. PR [21](https://github.com/esbraun/REMission/pull/21) received independent READY for POC-1–3 from /root/poc_scope_critic_astra, GPT-6-Astra/medium, app thread `01a161aa-3824-79e1-bb52-5edd6dd8dec4`, full report blob `d788d452da2d46f90822c18aa709548e091b4f91`. Author verification: GPT-6.1-Sol/high.

This checkpoint changes evidence and the existing ledger only. Exclusive checkout `C:/Users/erics/Documents/Projects/REMission-worktrees/poc-merged-verify-sol-261021`, branch `launch/poc-panel-merged-verify-20261021`, started clean at the merge. The previous frozen author checkout, source and runtime stacks on ports 8765–8775 were preserved.

## Source and runtime correspondence

[source-runtime.json](source-runtime.json) and [actual commands](source-runtime-commands.json) bind the new merged checkout to the previously reviewed immutable images. All 48 service, 27 learner and 3 generator copied source files match physical SHA256 bytes in the actual images; all 3 built assets match the reviewed manifest. Of 209 recorded source files, 207 match. Two source-only generator test files differ physically; neither is copied by any production or test Dockerfile. These exceptions are recorded explicitly. Image provenance remains original source `ef71ae01953462e65be5d1bd7d6c6359c84a3139`; no images were rebuilt or relabelled. Merged deployment uses the verified corresponding source at a7ab7e6.

- Service: `sha256:a92d7bda327ce7eb06a1d8ee03193d4090f148f48034bee63655d3cd8402dbcb`
- Learner: `sha256:24f061faf5d692cc0a47128cf4c82b9437e5ca9cb5d6edac3479805f80e28d6c`
- Generator: `sha256:2f70d99ca90d8ecb159aba3ed338a2d8266830b49bdb80bbf539908d9f2ef7de`
- Foundation: `sha256:ce346feace2ae607ebd574e1bb681d594c9b676c06b56f8ba8d50b858a577faa`

The supported launcher created new prefix `remission-poc13-4f1e77e0`, network and four private volumes, on previously free port 8776. [Deployment](deployment/deployment.json), [launcher output](deployment.log), and [compact commands plus nonempty raw streams](deployment-commands-compact.json) preserve identities and health. Large duplicate source snapshots and original streams remain locally under ignored deployment captures. The intended stale provisioner restart failed because the new current service owns port 8776; its exact stderr is preserved. Health reports LIVE-HOLD-01/1.0.0 and new database instance `96e6c214-ec1c-4586-8bd5-05cb50a3339b`.

Each ordinary container was limited to 2 CPUs / 2 GiB. Correspondence commands took 2.123 seconds total; deployment commands 12.535 seconds total (not an end-to-end latency benchmark). [Runtime sample](runtime-stats.jsonl) records actual idle CPU/memory. No simulation-scale computation or monetary-cost estimate was performed.

## Official MCP merged smoke

[Raw bounded browser record](browser-mcp.json), [visually inspected screenshot](poc8776-day14.png). Alice signed in, generated default count12 / seed20261021, and saw 12 generated patients among 22 owned. Selected Synthetic Morgan 01 (`POC-5fd7a273e1114fcca47c2bed38452e9d`), inspected baseline ISI and eligible options with none preselected, explicitly chose behavioral escalate, entered rationale, reviewed and confirmed.

Day advance 0→1 followed by next-visit advance 1→14 passed. Current projection contains one persistent action, 14 distinct delivery/adherence records (13 taken, one not taken), 14 daily reports (10 observed, four missing), baseline ISI19 and scheduled ISI14. ISI recall is exactly Dec18→Jan1 and Jan1→Jan15, 11:00 UTC. Decision is Jan1 noon, effective/delivery begins Jan1 20:00 UTC; real receipt time is separate. These are synthetic observed outcomes, not fitted effects or evidence of efficacy.

Current API content was identical before and after browser reload. Saved decision remains cutoff `2026-01-01T12:00:00Z`, display SHA256 `520e170da3afb797e2b998c425af172fa0bf9be4da3a21a9c0927c028d9e1a1c`, zero prospective daily reports, and no advancement controls. Separately requested later outcomes returned 15 records (14 reports + one ISI). Returned to current day14.

Normal browser UI requests were 200; console had zero warnings/errors. Two author read-only instrumentation mistakes are preserved: relative APIRequestContext URL rejected locally, then nonexistent /workspace route returned404; corrected absolute existing patient route returned200. Neither affected app mutations. Screenshot staged by this own MCP call at exact `C:/Users/erics/Documents/Projects/REMission/artifacts/playwright-mcp/poc8776-day14.png`, copied only that file to this checkout, original preserved; SHA256 `3ecd459bb89236f5a0914fe0de48cb1d5fe88718217b52e874f5e7971edc8960`. Automatic snapshot paths returned by MCP remain preserved in staging. No primary source was read or changed.

No application defect found. No broad suites repeated: exact source tree and byte correspondence plus this postmerge browser smoke complement the final independent copied78-test and browser READY report. Official MCP exclusivity for8776 was explicitly released to root after completion. Stack remains loaded at [8776](http://127.0.0.1:8776), current patient day14.

## Remaining work

POC-4–6 and POC-VAL still require actual analytics and small accuracy/timeliness ablations. Human factors, clinical review and clinical validation remain unexecuted; no real patient connections or efficacy claims. The restricted law and limits remain as accepted in [the interface](../../poc-generator-interface-20261021.md) and prior [implementation handoff](../POC-1-3-20261021/handoff.md). No methods implementation occurred here.
