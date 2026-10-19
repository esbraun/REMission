# Technical appendix reader

Status: implementation plan. Depends on research foundations and the shared help/content registry.

## Entry and reader

Provide Technical appendix on the home dashboard. Open a wide accessible document reader with table of contents, text search, stable heading anchors, version label and explicit Open in separate tab. Closing returns to the originating dashboard or guide with its state intact.

Use the guide system's focus behavior at desktop/narrow widths. Render trusted versioned Markdown; disallow executable embedded HTML/scripts. Search only the published documentation corpus.

## Contents

1. Synthetic demonstration scope and limitations.
2. Data inputs, available-at timing, provenance, missingness and wearable limitations.
3. Clinical versus learning states, ownership and permissions.
4. Estimands, outcome units/horizons, uncertainty and interruption strategies.
5. Bayesian models, borrowing, applicability and prior dependence.
6. N-of-1, behavioral escalation and consent/oversight.
7. MRTs, adaptive support and coordination constraints.
8. Validation gates, pending/failed/undefined outputs and abstention.
9. Historical reconstruction, audit records and versioning.
10. Glossary, references and revision history.

Use canonical specifications as the source of methodological truth, edited into readable explanatory content with source links. Never present simulated effects as clinical efficacy. Explain concepts without publishing hidden simulator truth, credentials or operational secrets.

## Version interface

Documentation manifest: document ID/version, title, reviewed date, compatible method/evidence versions and section anchors. Guide topics reference this manifest rather than duplicate method explanations. Historical basis links resolve to their matching version; if unavailable, state that explicitly and never substitute current documentation silently.

Bundle documentation independently of model services, so an inference-service failure does not prevent reading help.

## Acceptance

Verify dashboard opening, standalone-tab links, search, headings, keyboard/focus behavior, historical version resolution and unavailable-version handling. Check links to canonical references and consistency of terminology across guides and appendix.

Source: [Cloudscape content ramp](https://cloudscape.design/patterns/general/help-system/). Chapter structure and version behavior are project requirements.
