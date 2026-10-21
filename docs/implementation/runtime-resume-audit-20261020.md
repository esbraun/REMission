# RUNTIME-RESUME-01 — collaboration lifecycle capability check

**Requested assignment:** GPT-6 Luna / high, unchanged. Effective model/effort cannot be independently introspected by the available agent inventory.

**Checkout:** `C:/Users/erics/Documents/Projects/REMission-worktrees/readiness-audit-v2`

**Branch:** `launch/runtime-resume-audit-20261020`

**Base:** `91a1679fb2a92ca60fed7a2365f760df756f55f9`

## Historical finding (superseded below)

There is no verified, actionable control in the current live runtime to close/release one of the existing collaboration children or change that same child's model and effort to GPT-6.1-Sol/high while retaining its identity and assigned worktree.

Official Codex documentation describes subagent orchestration, including closing completed subagent threads, and the App Server documents resuming an existing thread with a different model. Those are documented capabilities in Codex surfaces generally, not proof that this collaboration-child runtime exposes them. The current collaboration tool surface provides spawn, send, follow-up, interrupt, list, and wait; it has no close/release operation, and follow-up/interrupt have no model or effort override. An interrupted agent remains available; completion does not confirm closure.

The Codex app connector exposes a separate `send_message_to_thread` operation whose schema accepts `threadId`, optional `hostId`, and `model` plus `thinking` overrides. However, the read-only `list_threads({limit:30})` result contained the primary REMission task and peer tasks, not the planner/critic collaboration children. `list_agents` showed `/root/g0_planner_astra` and `/root/g0_critic_astra` by canonical name and status, but returned no Codex thread/session IDs. There is no supported evidence here that those canonical names are valid `threadId` values or that either app-level thread is the same worktree-owning collaboration child. The connector instructions also require explicit user authorization to send a follow-up. Therefore no message was sent and no model change was attempted.

## Bounded runtime checks

- `ALL_TOOLS` inventory: collaboration controls are spawn, send, follow-up, interrupt, list, and wait. No close/release or collaboration model-change control is present. App connector tools include `mcp__codex_app__list_threads` and `mcp__codex_app__send_message_to_thread` with the fields described above.
- `list_agents`: root plus the planner, critic, and this helper. Planner and critic are completed but remain open; this helper remains open between turns. The reported count is two open non-Luna agents, three spawned agents total, plus the primary (four open threads against the runtime cap). This helper remains GPT-6 Luna/high by explicit assignment.
- `mcp__codex_app__list_threads({limit:30})`: returned the root REMission task and other peer tasks; it did not identify the planner or critic children. No unrelated thread was messaged.
- `codex --version`: `codex-cli 0.147.0`. `codex resume --help` documents resuming by an existing `SESSION_ID` and a `--model` option. This is a possible route only for a known Codex session ID; no child session IDs are available here, and the docs do not establish that collaboration child identifiers interoperate with this CLI. `codex agents --help` displayed the general CLI help, not a dedicated agent-management interface.
- `codex app-server --help` lists app-server and daemon/proxy tooling. `codex app-server daemon version` returned `Error: codex app-server daemon lifecycle is only supported on Unix platforms`. `codex app-server proxy --help` requires a Unix socket path. No daemon was started, no socket or private session/auth files were inspected, and no existing session was resumed.

## Operational consequence

The parent reports that the two Astra workers occupy both non-Luna slots even though their turns are complete. The Sol/high repair and contract work remain queued until the orchestrator can use a supported lifecycle path and confirm that a specific existing child identity maps to the same worktree, or otherwise reallocate capacity within policy. Do not count completion as release, change the model through a guessed thread ID, use nested/top-level agents, or replace the required Sol role with solo work. This finding is bounded to the current exposed runtime; it does not claim Codex universally lacks subagent close or thread-resume/model-switch features.

## Project status boundary

The resumed user goal remains active: build, load, and test the synthetic demonstration autonomously, with human review later. The repository still has no application implementation, so no load, build, or application test was performed by this audit. The READY-01 audit candidate `ceed0ff8df66c612641af64a03e46c5666628767` and G0 planning candidate `c239dca3503c32b5e20fbd630d69f1720f9b12ce` remain changes-requested; the checkpoint review of reporting candidate `91a1679fb2a92ca60fed7a2365f760df756f55f9` is not source or gate acceptance. G0–G7 are unaccepted. Human-factors and clinical review are deferred for later as directed and are not the engineering lifecycle blocker. No PR or merge is claimed.

## Official references

- [Subagents — OpenAI Learn](https://learn.chatgpt.com/docs/agent-configuration/subagents?surface=app) describes subagent orchestration and the general ability to close completed subagent threads; the web sidebar itself is described as read-only.
- [Codex App Server — OpenAI Learn](https://learn.chatgpt.com/docs/app-server) documents `thread/resume` for an existing `threadId` and states that resuming with a different model produces a warning and a one-time model-switch instruction.
- [Developer commands — OpenAI Learn](https://learn.chatgpt.com/docs/developer-commands) documents `/subagents` for switching to inspect or continue an agent thread; it does not provide a command to release a completed collaboration child.

No existing thread was closed, interrupted, resumed, messaged, or model-switched during the original Luna audit. No existing project files or runtime configuration were edited by that audit.

## Superseding root-verified resolution

2026-10-20, after the original audit: root resolved the lifecycle blocker using supported archival of an existing, verified child. This update is Sol's durable record of root-supplied observed tool evidence; Sol did not repeat lifecycle mutations. The immutable original review reports preserve their earlier blocked observations.

1. Root read only named process environment keys in the planner/Luna workers. Planner `CODEX_THREAD_ID` was `01a15ccb-51c2-7422-9cf1-29137399d061`; Luna was `01a15cc9-7f45-79e1-90a9-40f4ef0bc5b9`. Root app `read_thread` matched each ID to that child's recent turns and assigned checkout before any mutation. Parent/root ID is `01a15cc8-bab2-73f3-bc3b-c2861965b8eb`. Canonical collaboration names alone were not used as app IDs.
2. Root attempted app `send_message_to_thread` with Sol/high on the verified planner identity. The runtime rejected it: `direct app-server input is not allowed for multi-agent v2 sub-agents`. No model changed; this direct-app-input path is unsupported for these children and must not be retried as a lifecycle solution.
3. Root called supported `mcp__codex_app__set_thread_archived` with `threadId=01a15ccb-51c2-7422-9cf1-29137399d061`, `hostId=local`, `archived=true`. The return confirmed `archived=true` for that exact existing planner.
4. Root then called native `collaboration.list_agents`. It contained only root, independent critic Astra and Luna; planner was absent. That actual removal established slot release. An archive return by itself, a completed turn or interruption is insufficient evidence of capacity.
5. Only after verifying removal, root spawned `/root/integration_sol` with explicit `gpt-6.1-sol` / `high` and a fresh exclusive worktree at the accepted base. Root subsequently verified Sol app ID `01a15cf4-3065-7063-b11e-3967008fe9a1` with `read_thread`, matching active worktree commands and named ID lookup. Root similarly verified critic ID `01a15ccb-d23c-7e10-a1c8-6a55a6719daf` against its own critique-checkout commands.

Current counts are two non-Luna workers (Sol/high, independent Astra/medium), one Luna/high helper, three spawned workers plus root = four total. Native collaboration still has no close/model-change parameter. Explicit spawn/assignment settings are observed; no independent effective-model introspection is exposed. There was no silent substitution, extra orchestrator, new top-level task, nested worker, shared checkout or limits bypass. Source planner/readiness branches and old worktrees remain preserved.

Operative procedure for future root-only replacement: preserve commits/checkpoint and assigned worktree, obtain the actual existing child's app identity from a named environment key, verify that identity via `read_thread`, archive only that child using the supported app operation, confirm its removal from native live inventory, then provision/spawn the correctly configured replacement within both limits. If identity verification, archive or removal fails, keep dependent work queued. Do not infer that a generic archive always closes every runtime child.

Sources for this operative result are root's observed named-key lookups, app `read_thread`, rejected `send_message_to_thread`, successful `set_thread_archived`, subsequent native `list_agents`, and explicit Sol spawn configuration, communicated directly to this repair worker. The general official references above describe broader capabilities; they do not establish this specific v2 child lifecycle behavior. Tool documentation for `set_thread_archived` and `read_thread` supplies the supported app operations. No runtime settings or private session/auth files were modified.

READY-FIX-01 and G0-PLAN-FIX-01 are now authored by the assigned Sol/high in its own worktree and await exact-head/base independent Astra review. G0 actual contracts, library probes and G1-G7 implementation remain unexecuted. The active goal remains the full real-algorithm synthetic hybrid demo; human-factors and clinical review are deferred, without invented acceptance or an engineering blocker.
