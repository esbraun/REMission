# Candidate v1 byte compatibility audit

- Audit scope: read-only Git-blob/attribute audit, bounded to the protected paths in `v1-byte-inventory-raw.json`, the new `.gitattributes` rules, and raw-log metadata. No generation, tests, Docker, services, or source edits were performed.
- Checkout: `C:/Users/erics/Documents/Projects/REMission-worktrees/g1-obs2-candidate-v1-audit-luna-20261021`
- Base: `6bc8bd998e8a0baaef9884998e740665fb5fd7b1`
- HEAD: `44d25a06cc8e996eb2b5aeb01c2ff2694ca4d72f`
- Model/effort: `gpt-6-luna/high`
- CODEX_THREAD_ID: `01a1603a-dae7-71d1-ab6c-e2cd9246544a`
- Applicable `AGENTS.md`: none found in the checkout.

The inventory file's candidate Git blob is exactly `451c68a3e1777dc8a47b320564622a2c0ed86ffe`, matching the requested baseline inventory. Its scope contains 41 generated v1 products (schemas, dictionaries, bindings), 10 v1 binding input paths and 2 raw fixtures: 53 paths total. Comparing `git rev-parse <revision>:<path>` for every listed path at base and HEAD found zero changed or missing paths. Since the files themselves are identical Git blobs, their v1 schema URNs and binding input bytes are unchanged in the protected scope.

Reading the 53 ordinary worktree files against their HEAD blobs found 30 byte mismatches, all fully explained by CRLF checkout conversion (`worktree.replace(CRLF, LF) == Git blob`); the other 23 matched directly. This classifies working-copy bytes only and does not alter or normalize any Git blob.

The `.gitattributes` diff appends 19 lines. Existing rules are untouched. The new rules set LF for new v2 Python/schemas, `binary` for check and curated/clone attempt logs, `-text` for raw JSON and raw Markdown, and LF for the accepted source manifest. `git check-attr` confirmed these behaviors on representative v1 products, v2 products, check logs, curated/clone logs and JSON, raw Markdown, and the source manifest. There are no deleted paths under `docs/implementation/evidence/G1-OBS-REP` in this range; that directory had no paths at base (290 paths at HEAD). Existing G0 and G1 foundation raw-artifact attribute lines precede the append and are unchanged. This is an attribute-scope check, not a byte audit of unrelated historical evidence corpora.

For separate Astra source review, `contracts/runs/admission.py` is modified, while `contracts/runs/export.py` and the listed v1 generated products/binding inputs are not. Candidate adds v2 domain/run parsers and exporters (`observed_v2.py`, `admission_v2.py`, `export_v2.py` and related v2 modules). This audit did not assess parser/export behavior or gate readiness; those shared parser changes need independent code review.
