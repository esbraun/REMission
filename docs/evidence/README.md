# Evidence register rules

Revision: 2026-10-19. This register records justification, not quantitative training data. [Plan index](../../plan.md).

## Domains

- [Simulation](simulation.md): ADEMP, simulation verification, SBC and computation.
- [Causal](causal.md): estimands, g-computation, transport and borrowing.
- [Experiments](experiments.md): N-of-1, SMART, MRT, bandits and policy evaluation.
- [Clinical](clinical.md): target population, outcomes, care pathways and transport limits.
- [Industry](industry.md): engineering precedents; no clinical efficacy claims.
- [UX and interfaces](ux-and-interfaces.md): usability, accessibility and adapter guidance.

Read only cited entries for an assigned task. Citation anchors replace cross-file footnotes; bibliography records have one canonical home.

## Required record

New or revised records contain a stable ID; full citation and publication year; DOI or official URL; version when mutable; source type; exact supported claim; assumptions and limits; linked requirement IDs; passage/section/table locator; verification date/status; and role (method, rationale, quantitative input or contextual example).

Verification status is `full-text-checked`, `abstract-checked`, `metadata-only`, `inaccessible`, `superseded`, or `legacy-not-reverified`. Original entries retain bibliographic text and limitations. Migration does not upgrade verification. Unverified URLs or locators must be completed before release reliance; never fabricate them.

Entries supplemented on 2026-10-19 record supporting passages inspected during the design review, not an exhaustive systematic review. Distinguish online-first and issue years. Preserve original bibliographic identity when URLs move.

## Maintenance

1. Cite the record beside the requirement it supports; it must not appear to justify adjacent invented thresholds.
2. Recheck when a claim, method, clinical boundary or dependency changes, and before a release relying on it.
3. Record mutable documentation version/accessed revision; recheck at implementation. An accessed version is not an installed dependency.
4. Record corrections/supersession without deleting historical rationale.
5. Distinguish broken links from unsupported claims.
6. Maintain source-to-requirement links in both directions.
7. Real publications do not supply invented DGP coefficients. Synthetic studies have separate generator/seed/version provenance. Real quantitative extraction remains separate work.
8. Industry cases justify engineering analogies only; clinical validity is unestablished.

Maintenance is triggered by edits and release review. No scheduled monitoring is configured.
