# Independent G1-FOUNDATION review — changes_requested

Reviewed frozen/published head `54adde3d7588c3aee3baa29b5370a2317bfd34a9` against accepted base `8ca67682505d78accc855e92cbfbb6692edf8316`. Own detached root: `C:/Users/erics/Documents/Projects/REMission-worktrees/g1-foundation-review-20261021`. Requested model/effort: gpt-6-astra / medium; no independent effective-model introspection endpoint is available. No helper, candidate source change, commit, merge or author checkout access occurred.

**Disposition: changes_requested for this exact FOUNDATION package.** The two independently reproduced safety compositions below block acceptance. Root requested a bounded report after confirmation, deferring remaining broad browser repetition to the repaired exact-head review. This is not a completed passing foundation qualification and does not accept G1 overall, generator/scientific engines, clinical or human gates.

## Findings, severity ordered

### P1 — Equal-time known death can be cleared and an ordinary approval persisted

Source: `services/foundation/app.py:320` (state-change death guard), composed with `services/foundation/replay.py:82` and the ordinary approval route. Requirement: approved `docs/implementation/g1-technical-plan-20261021.md:39` requires current safety checked in the transactional admission boundary; line 33 preserves strict learner cutoff and line 65 distinguishes safety phase precedence.

Independent actual-route/SQLite reproduction uses the supported injected clock fixed at 2026-10-21T12:00:00Z, real seeded accounts, session cookie and CSRF, and the reviewer-built curated tests image. Ingest a valid death with event/declared availability 11:00. Live admission clamps actual availability to 12:00 and returns 200; current workspace correctly excludes all actions and disables ordinary approval. Without advancing clock, POST state ASSIGN-02 using current patient version returns 200. POST ordinary MED_A approval with the resulting current versions returns 200 and creates an immutable approval bundle and follow-up task.

The state-clear guard calls strict `as_known_at(now)`, which excludes the just-arrived death. Initial hold logic intentionally includes availability equal to now. The approval boundary trusts the cleared workflow and fails to restore the terminal exclusion. This is a valid equal-time deterministic service-clock composition, not a claim that separate wall-clock HTTP calls always share a microsecond. Equal-time safety/assignment semantics are explicitly required.

Reproduction: `artifacts/review-foundation/death_probe.py`; raw result `death-output.json`. Run using reviewer tests image with /probe.py read-only, network none, read-only root and /tmp tmpfs, as recorded in the review history. This uses candidate test helpers only to construct valid envelopes/authentication; the adverse sequence and assertions are independent of existing passing tests.

Repair acceptance: current safety visibility and terminal exclusion must consistently include the admitted equal-time death while learner projection remains strictly before cutoff. Reproduce before/equal/after boundary, attempted state clear and subsequent fresh approval, including persistence counts. Reject the clear/approval without a new bundle/task. Preserve historical and learner cutoffs; do not solve by admitting equal-time symptoms into learner data.

### P2 — Retracted safety events re-trigger a hold on unrelated new data

Source: `services/foundation/replay.py:82–83`. Requirement: approved plan line 33 requires cutoff-first visible lineage resolution; line 139 explicitly requires corrected/retracted/duplicate lineage compositions. Accepted `contracts/domain/boundaries.py:90` resolves visible heads and omits retracted heads.

Independent actual-route reproduction: ingest a fall; advance clock one second; ingest its valid revision-2 retraction; advance one second; explicitly clear to ASSIGN-02 with rationale that the source correction was reviewed. Clear returns 200 and ordinary approval becomes permitted; projection has no active fall. Advance another second and ingest an unrelated valid daily report. Ingestion returns 200, but current state returns to clinical hold and ordinary approval becomes forbidden. The removed fall is still absent from projected active records.

`known_safety` scans every historical record and `held` excludes only each row's own retracted status. The original active fall survives this check even though its visible lineage head is retracted. This report does not demand automatic clearing immediately on retraction: the reproduction explicitly performs clinician clearance first, then demonstrates resurrection on unrelated input.

Reproduction: `artifacts/review-foundation/retraction_probe.py`; complete raw responses/workspaces in `retraction-output.json`.

Repair acceptance: derive current safety from the appropriate cutoff-visible, lineage-resolved current safety set, with its explicit equal-time admission rule; retain original envelopes and provenance. After valid retraction/correction plus explicit clearance, unrelated data must not resurrect superseded safety facts. Test corrections changing event type, retracted head, duplicates, and a genuinely still-active safety event so the repair cannot silently remove a valid hold.

## Observed verification and preservation

- Verified own root, exact detached head/base, initial clean state. Candidate source remained unmodified.
- Read bounded accepted plan/requirements, service authentication/transaction/replay/workflow/persistence, client context/report/history flows, tests, build/runtime/boundary tooling and author evidence. Applied installed React best-practices, composition-patterns and web-interface-guidelines skills; fetched current interface rules. No broad future generator requirements were added.
- Reviewer-owned source-derived build passed 14/14 recorded commands. It includes pinned SQLite/runtime qualification, strict client typecheck, two async client groups, production build and 18 real-route/SQLite backend tests. Raw TestClient httpx deprecation warning is preserved.
- Reviewer-owned integration passed 12/12: accepted contract/DGP/TIME tests (60), artifact groups, DR groups, schemas/dictionary/ledger/runtime, accepted-source preservation and full-base whitespace. The checker retained the 635-row coverage mapping guard. This does not imply all possible ledger invariants were newly exhaustively hand-audited.
- Own separate resource prefix `remission-g1-foundation-review54`, source-derived review54 images, database volume and loopback 8766. Actual stack passed API/learner private file/list/import, evaluator DNS and direct-IP denial, observed-volume write denial, plus positive private evaluator read/network controls. Source checkout/socket were not mounted into running application identities. Own inventory and all command outputs retained.
- Build recipe copies only redirect evidence outputs, image tags and Dockerfile FROM tag references. Stack recipe copies only redirect own outputs, tags/resource labels/prefix and host port/origin/health URL (container service port unchanged). Candidate app source is untouched. Runtime image `sha256:b2fb3b8d4ef505d544465c49876fc55278b507ff493d88430462493b0204e0bd`; service `sha256:ca780cc5d6926e0eecf463f32747a8a28fb656c40f0eb2a4256094c7a043378a`; tests `sha256:95b52a13cca84f4c42db47692d668b0d5b55ae68fd07268d064da0649b913478`.
- All 26 entries in author's build-source manifest have identical reviewer raw source SHA256 values. Reviewer capture has 28 entries because the frozen tree additionally includes README.md and verify_integration.py. The aggregate mapping-equality diagnostic is therefore false without any changed runtime-source hash; do not interpret it as source/image drift. Own complete manifest and image identities retained.
- Genuine HTTPS `--single-branch --branch launch/g1-foundation-20261021 --no-local` clone with `core.autocrlf=false` in own ignored directory reproduced exact head and initially clean tree, no alternates. Clone integration passed 12/12. Clone source mounted read-only into the dependency-only reviewer runtime, PYTHONPATH=/workspace, passed all 18 backend tests. No local Git overlay or unpublished object input was used. A second full clone image/client build was not executed after the blocker.
- Official Playwright MCP navigated only our service at 8766 and captured the actual login accessibility tree. The exact newly generated tool-owned snapshot was copied into own evidence with source path/time/SHA256; original preserved. No authenticated browser flow or screenshot visual qualification is claimed. The sole review tab was closed; no tabs remain. Author service 8765/resources were untouched.
- No repeated costly NUTS/R/BCF fits. Accepted G0 records/raw evidence remain historical accepted inputs, not new executions. Pending browser identity/race/approval/history/mobile/keyboard checks and final complete exact-head acceptance must be completed on the repaired head. No waiver is implied.

## Raw evidence

Own ignored directory: `artifacts/review-foundation/`. Evidence manifest raw Git blob: `164fc736dc17a6c03b25d4fac822026fe96f347a`. It records source/output sizes, SHA256 and raw Git blobs for independent probes, source-derived build/check logs, runtime inventory, clone identity/backend/integration, tooling-only reproduction copies and exact browser transfer. It also preserves the initial aggregate source-mapping comparison described above. Evidence was hashed with `git hash-object -w --no-filters`, not staged or committed. The new standalone report is the only untracked review deliverable outside ignored artifacts.

Root must obtain a refreshed independent exact-head/base review after repair; this frozen head is not ready_to_ship.
