G1 runner path audit (source-only; no runner/tests/Docker invoked)

Checkout: C:/Users/erics/Documents/Projects/REMission-worktrees/g1-runner-path-audit-luna-20261021
Branch: launch/g1-runner-path-audit-20261021
Base/candidate: 95a48144b936c690aa86e5743a5330a594403521
Target base: 69e6ae9dc5bf85ddbf39976d2ce4ce70bce1ea1e
Model/effort: gpt-6-luna/high
CODEX_THREAD_ID: 01a15fc8-e671-7a53-bd32-1f25235d9be6
Source remained unchanged.

Finding — unresolved author-checkout absolute script path replays in the repair chain:
- docs/implementation/evidence/G1-GENERATOR-INTERFACES-20261021/verify_interfaces.py:25–31 appends the own-checkout preservation.py path as command index 13 (in its recorded checks). It runs with cwd=ROOT at line 34.
- repair/verify_repair.py:34–40 replays the first 16 recorded commands. It rewrites command[0] from old python.exe to sys.executable and Docker bind sources, but leaves arguments intact. Its replayed command 13 therefore retains the recorded absolute argument C:\Users\erics\Documents\Projects\REMission-worktrees\g1-generator-interfaces-sol-20261021\docs\implementation\evidence\G1-GENERATOR-INTERFACES-20261021\preservation.py. Current raw repair-check-results.json confirms this command value at checks[13].
- repair/verify_affected.py:13–17 subsequently executes repair-check-results.json command[13] unchanged. In a fresh clone this executes/reads the author Sol worktree copy. The target preservation.py computes ROOT from its own __file__ (lines 6–8) and runs git checks at that root (11, 15–26), so the check silently targets the other checkout.
Minimal repair direction for Sol: normalize command arguments that point inside the previous runner checkout to this checkout (or construct this preservation command from current OUT); re-run current affected sequence and record source-local provenance.

Other path findings: verify_interfaces.py:19–23 consumes prior foundation command rows 0–9 from immutable G1-FOUNDATION final-integration-check-results.json. Those historical rows include g0-sol absolute Python interpreters and g1-foundation Docker bind paths, but the current runner explicitly replaces interpreters and every type=bind source before execution, so I found no unresolved worktree execution/read there. verify_consumers.py:29–30, 66–70 binds current ROOT or fixture-only output paths and uses cwd=ROOT. verify_repair.py Docker build context/file paths are relative to cwd=ROOT; its consumer import path is repo-relative and runs with ROOT cwd; postrepair scripts at lines 54–58 are relative to current ROOT. Fixed BASE/REJECTED hashes and git diff references are repository history refs, not checkout paths.

Evidence distinction: final-integration-check-results.json and current-interface-check-results.json are stored raw command/output evidence. Reading their JSON is intentional; the issue is repair/verify_repair.py replaying commands from that evidence with partial path rewriting, which turns one historical path into executable source dependency. I have not treated raw paths as code execution by themselves.
