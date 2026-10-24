# Engineering guidelines

Revision: 2026-10-19. These requirements govern future implementation across G0-G7. Installed skills and documentation review do not establish application correctness, clinical safety or efficacy.

For the immediate [cloud physician simulation milestone](../spec/poc-amendment-20261021.md#immediate-physician-simulation-milestone-2026-10-22), apply these guidelines to enabled simulation/auth/persistence behavior and [CS-T1–T8](../implementation/poc-cloud-simulation-ledger-20261022.md). Full analytics/model browser scenarios and method qualification remain later obligations; training/fitting is not required for this milestone.

## ENG-01 — Simple design and reuse

- Keep domain rules and contracts in one authoritative home. The service owns eligibility, readiness and permissions; the frontend renders its decisions rather than reimplementing them. Reuse typed contracts across boundaries where practical.
- Apply DRY to repeated responsibilities and knowledge. Extract shared components or functions when real repetition makes them useful; similar-looking code alone does not justify a generic framework.
- Prefer maintained, production-used open-source implementations for authentication primitives, accessible controls and infrastructure. Check license, maintenance, security history and runtime compatibility, pin selected versions, and record the choice and purpose. Library adoption is not validation of its use here.
- Do not hand-roll cryptography or established UI primitives. Avoid dependencies for trivial helpers and avoid combining entire component systems.
- Choose the simplest implementation that meets documented workflows and credible failure cases. Do not add speculative compatibility layers, plugin systems, cache hierarchies or exhaustive edge-case machinery. Record unsupported optional behavior explicitly rather than silently fabricating a fallback.
- Preserve required ownership, consent, holds, temporal cutoffs, immutable history, optimistic concurrency, idempotency and rollback-safe transactions. These are established requirements, not optional edge cases.
- Explain meaningful abstractions, dependencies and tests through the requirement or failure they address. Optimize measured bottlenecks; avoid speculative memoization or virtualization.

## Methods library reuse

Methods work follows the [library decisions](../plans/methods/00-library-decisions.md), assigned implementation steps and [software evidence register](../evidence/software-libraries.md). Reuse established inference/regression/diagnostic/numerical implementations; retain project-specific estimands, interventions, transport, protocols and constraints. Qualify actual release/license/maintenance/runtime compatibility before pinning. Use applicable existing evidence where clear; add selective future DGP benchmarks only for material unresolved choices, preserving all required project validation.

## UI-SKILLS — Portable UI guidance

Retain React/TypeScript, FastAPI and deployment outside Vercel. Skill adoption does not require Next.js, a React upgrade, a hosting change or new public APIs. Keep the existing NHS-informed visual foundation and G0-before-detailed-design dependency.

Read the applicable installed skill and relevant rule files when designing, implementing or reviewing UI. Treat their advice as subordinate to project domain requirements, accessibility and the selected runtime. React-19-only advice applies only when that runtime is selected; Next.js-specific APIs do not apply to a plain React application.

| Source path in vercel-labs/agent-skills | Skill name | Application |
|---|---|---|
| skills/react-best-practices | vercel-react-best-practices | Independent authorized reads in parallel; avoid request waterfalls; derive redundant state; lazy-load heavy optional views using the chosen runtime |
| skills/composition-patterns | vercel-composition-patterns | Simple components with explicit variants and composition; providers and compound components only when shared behavior warrants them |
| skills/web-design-guidelines | web-design-guidelines | Review semantic controls, labels, keyboard/focus behavior, responsive layouts, reduced motion, loading/errors and accessible help |

Do not apply generic advice mechanically: holds and permissions still block submission; identity, uncertainty and blockers remain readable without truncation; only appropriate navigational state belongs in URLs, never credentials or drafts. Do not introduce cross-user caches, automatic treatment selection or shared mutable request state for performance. Clear/invalidate caches and requests according to the [account contract](../plans/ux/01-doctor-accounts-and-shell.md).

### Installation and provenance

Installed on 2026-10-19 using the system skill-installer helper, from immutable commit `063bee94c3f4df8453406c830b0a7df0f2860278`. Local destinations verified under `C:/Users/erics/.codex/skills/`: `react-best-practices`, `composition-patterns`, `web-design-guidelines`. These are agent instructions, not application dependencies. New sessions/workers must verify skill availability rather than assume this machine's installation is shared.

To reproduce, invoke the skill-installer's `scripts/install-skill-from-github.py` with `--repo vercel-labs/agent-skills --ref 063bee94c3f4df8453406c830b0a7df0f2860278 --path skills/react-best-practices skills/composition-patterns skills/web-design-guidelines`. Resolve the helper from the current skill catalog; its default destination is the current Codex skills directory. Inspect existing destinations before installing; do not overwrite unrelated skills. Verify all three SKILL.md files and their referenced rules after installation. Exclude Vercel deployment/optimization and unrelated skills.

The web-design skill fetches a separate upstream document before each review. Record that fetched content's revision or hash and retrieval date; the skill pin does not pin those rules. This planning review fetched rules on 2026-10-19 at `434b7f91364665f2f733b310ec54809bf8f37937`. See [source records](../evidence/ux-and-interfaces.md#ui-engineering-skills-2026-10-19). An unavailable source is a reported review limitation, not a silent pass.

## TEST-QUALITY — Tests that detect meaningful failures

Assign planning and independent review under the [launch model policy](../../implementation-prompt.md#launch-contract): Sol/high by default; Astra/medium only for critical gate plans/reviews after ROOT records the material gate reason. Routine documentation, bug fixes and clarifications do not automatically require Astra. A different worker still reproduces relevant checks; neither self-review nor model selection substitutes for evidence. Difficult implementation alone may use Sol/xhigh with a recorded reason.

Choose checks by risk and observable behavior. Keep all required scenarios while avoiding redundant assertions at every layer. Coverage percentages and test counts are diagnostics, not acceptance criteria.

- Unit tests exercise meaningful seams: eligibility/readiness decisions, temporal cutoffs, evidence-state mapping, context isolation and draft-version validation. Use independent expectations and boundary cases; do not mirror implementation logic or assert trivial getters/internal call sequences.
- Integration tests use actual FastAPI routes, authentication middleware and isolated storage matching the selected persistence implementation. Exercise cookies, CSRF, expiry, password-reset revocation, resource ownership, atomic approval/follow-up, idempotency, stale versions and historical write rejection. Injecting a principal does not test authentication.
- Component integration and browser tests exercise user-visible state transitions, actual UI/API workflows and persisted outcomes. Include stale responses after patient switching and same-doctor reauthentication. Mock external boundaries or explicitly inject faults; do not mock the component/service behavior being accepted.
- Use isolated seeded fixtures, controlled time and explicit synchronization. Prefer semantic selectors and state-based waits. Avoid arbitrary sleeps, brittle layout selectors, broad snapshot assertions and retries that conceal failures. Preserve failure evidence, fix the cause and rerun affected checks.
- Keep the browser suite focused by combining coherent workflows, not by dropping required UI scenarios. Manual visual inspection, screen-reader/accessibility checks, human-factors work and statistical gates remain separate.

The [UX validation map](../plans/ux/06-validation-and-integration.md#verification-layers) assigns UX-T01 through UX-T14 to layers. Every row of the [integrated browser matrix](browser-validation.md#required-integrated-browser-matrix) remains mandatory. Record requirement/test IDs, expected behavior, actual result and evidence; a stub or synthetic fixture cannot masquerade as an accepted model output.
