# Launch status — 2026-10-20

**Status:** G0-LAUNCH-FIX-01 repair candidate needs independent exact-head/base Astra review. It comprises READY-FIX-01 and G0-PLAN-FIX-01. No application build, load, simulation or gate acceptance is claimed.

## Current orchestration and verified lifecycle

Root verified and archived the existing planner child, then native `collaboration.list_agents` confirmed its removal before Sol/high spawn. The prior lifecycle blockage is resolved. Direct app input to change the v2 child's model was rejected; no model changed. See the exact procedure, identities and sources in [runtime audit](runtime-resume-audit-20261020.md#superseding-root-verified-resolution). Earlier reports remain historical evidence; raw reviews are unchanged.

| Worker | Explicit model / effort | Current identity and ownership |
|---|---|---|
| Root | Primary settings | `01a15cc8-bab2-73f3-bc3b-c2861965b8eb`; owns orchestration, assignments, reviewed PRs/merges |
| `/root/integration_sol` | `gpt-6.1-sol` / `high`; no escalation | Verified app ID `01a15cf4-3065-7063-b11e-3967008fe9a1`; exclusive `C:/Users/erics/Documents/Projects/REMission-worktrees/g0-sol-integration-20261020`; branch `launch/g0-repair-integration-20261020`; accepted base `50403963d11cc51e6109a635f9a2b6b1031b8cf4`; writes only `docs/implementation/**` for this package |
| `/root/g0_critic_astra` | `gpt-6-astra` / `medium` | Verified app ID `01a15ccb-d23c-7e10-a1c8-6a55a6719daf`; separate `C:/Users/erics/Documents/Projects/REMission-worktrees/g0-critique-20261020`; root will provision `C:/Users/erics/Documents/Projects/REMission-worktrees/g0-launch-fix-review-20261020` detached at exact repaired candidate, preserving the old checkout; same independent thread reused |
| `/root/readiness_luna` | `gpt-6-luna` / `high` | Verified app ID `01a15cc9-7f45-79e1-90a9-40f4ef0bc5b9`; exclusive `C:/Users/erics/Documents/Projects/REMission-worktrees/readiness-audit-v2`; retained `launch/runtime-resume-audit-20261020` at `8315ee9d2062f04a53cd777a4891080d7c604b7d` |
| Archived `/root/g0_planner_astra` | Original `gpt-6-astra` / `medium` | Verified app ID `01a15ccb-51c2-7422-9cf1-29137399d061`; removed from native live inventory; source `launch/g0-plan-20261020` at `c239dca3503c32b5e20fbd630d69f1720f9b12ce`, exclusive planner checkout and checkpoint preserved |

Current counts: two open non-Luna workers, three spawned total, plus root = four total slots. Idle workers still count. Explicit spawn/assignment configuration is observed; the runtime has no independent effective-model/effort introspection. Native collaboration has no close/model-change control. Only root manages archive/replacement; a successful archive must be followed by verified actual removal before capacity is reused. No nested/new-top-level workers or model substitution occurred.

## Candidates and review state

The original READY-01 head `ceed0ff8df66c612641af64a03e46c5666628767` and G0-PLAN head `c239dca3503c32b5e20fbd630d69f1720f9b12ce`, both based on `50403963d11cc51e6109a635f9a2b6b1031b8cf4`, remain **changes_requested**. Full immutable reports are [READY-REVIEW-01](reviews/ready-review-01.md) and [G0-CRITIQUE](reviews/g0-critique-20261020.md), originally supplied as blobs `aa8df5b95e3a5c44fc10dc4b2d1a1365775e3a0d` and `f727e620ad38c9c66d7b51d344745c4185323ca0`.

Sol integrated the candidate histories into its new repair branch and corrected readiness browser/ref/whitespace statements, explicit runnable-versus-final G2 milestone dependencies and downstream LIB-03 owners/checks. The repaired candidate's exact SHA is returned after commit in the handoff; no self-referential SHA or ready_to_ship self-review is asserted. Candidate writes stop for review. The current PR target is `main`, exact review target base `c7cdf4a8415073d0b275064a0b0aca188fc022fe`; worker creation base remains 5040396. Root owns PR/merge after exact-head/base ready_to_ship, required checks, accepted dependencies and repository protections; no PR or merge has occurred for this candidate.

## Browser, refs and preserved state

Root/critic discovered `mcp__playwright__browser_*`; read-only `browser_tabs({action:"list"})` succeeded with one about:blank tab. This confirms exposed responding tooling only. No REMission app, workflow, UI or persistent-service test passed. Later G5-BROWSER requires the canonical complete matrix, real services/fixtures, screenshots/snapshots, console/network and persisted-record evidence.

Root/critic observed live remote `refs/heads/main` via `git ls-remote` at `c7cdf4a8415073d0b275064a0b0aca188fc022fe`; historically stale local `origin/main` was `462f66eac2ce146c4166219b5cdf6a53f54c8b5e`; root has since fetched it to c7. Neither changes the accepted launch base. Sol did not fetch or reconcile these refs. Primary untracked `.codex/`, `.dockerignore`, `.env.example`, `.gitignore`, `infra/`, existing `.env` and older readiness/planner worktrees are preserved and outside this repair's write scope.

## Next queue and claim boundaries

1. Independent Astra review of the exact G0-LAUNCH-FIX-01 head/base; Sol repairs any returned findings and re-review follows.
2. Root's authorized reviewed PR/merge, followed by Sol integrated verification.
3. G0-CONTRACT from accepted planning; G0-DGP, G0-LIB and G0-WORKFLOW consume accepted G0-CONTRACT. These remain queued/unexecuted. Shared schemas/manifests/locks/root config belong to the designated Sol integration owner under a later assignment.
4. Independent acceptance of actual G0 outputs, then G1-G7 real algorithms, integration, loading/testing and reproduction. Planning acceptance alone cannot complete G0 or the user's demo goal.

The JSON ledger preserves 635 rows and their stable test IDs, all required canonical requirements and scenarios, and all original final statistical acceptance. Structural checks and full-base whitespace results are repair evidence only. Synthetic engineering and statistical implementation remain unaccepted. Human-factors, clinical review and clinical validation remain separate outstanding statuses; the user explicitly defers human review and it does not block synthetic engineering with reviewed, labeled provisional assumptions. No fabricated clinical/human acceptance is supplied.

## Integration target update before repaired-candidate review

Root reassigned the actual PR/integration target to `main`, review target base `c7cdf4a8415073d0b275064a0b0aca188fc022fe`. The exclusive writing branch/base remain `launch/g0-repair-integration-20261020` / `50403963d11cc51e6109a635f9a2b6b1031b8cf4`. Root fetched `origin/main` to c7; the earlier stale 462 tracking-ref observation is historical. Root verified 504 is an ancestor of c7 (merge PR #9) and both commits have identical tree `78645d9384a3954d6bf293c361510d4394e70e1b`. The unused local `launch/implementation-20261020` target was never published or merged and is superseded for current dispatch. No worker rebase is needed for identical specification trees. Independent review and full-base checks identify c7 as the exact target base; record worker creation base 504 separately. Root observed empty main rulesets and Branch not protected; that does not establish absence of all future required checks. No protections bypass, PR or merge is claimed here.
