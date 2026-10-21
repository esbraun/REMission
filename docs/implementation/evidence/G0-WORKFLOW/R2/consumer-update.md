# G0-WORKFLOW R2 consumer identity update

2026-10-21. Root explicitly authorized a minimal update to the historical Inputs paragraph of `docs/implementation/workflow-contract.md`. It now consumes accepted main b24c3c0, TIME-01 2.0.0/wire schema 1.0.0/source SHA256 `fd2fe478e1fbf5237a307af8a2067fd6d485183763086ac7e10c133fda002275`, and the current DGP 1.2.0 candidate. Hash convention is UTF-8 source bytes with CRLF normalized to LF and no JSON reserialization.

Only that Inputs paragraph changed. All low-fidelity thresholds, states, permissions, ownership, consent/hold/history and approval guards remain unchanged. The original workflow document remains in commits 6195f9b and 2c76f4c, with original evidence and raw independent review preserved. The earlier ready_to_ship disposition was scoped to that earlier low-fidelity document; it is not blindly carried to this updated combined candidate. Root will obtain fresh exact-head/base independent review.

Scoped verification compares the complete workflow text with checkpoint 2c76f4c after excluding exactly its Inputs paragraph; the remainder must be byte-equivalent after LF normalization. The full DGP runner also verifies all 60 contract groups, generated DGP/domain exports, ledger and whitespace. Final exact-base whitespace covers this document-only change. No runnable UI, browser, accessibility, intended-user or clinical review was executed; those gates remain separate and deferred/unaccepted.

Ownership CODEX_THREAD_ID `01a15eb8-0f9a-7cb2-b796-608d4ce5864b`; explicitly assigned gpt-6.1-sol/high, independent effective model/effort introspection unavailable. See G0-DGP/R2 verification and handoff for the final candidate and local checks.
