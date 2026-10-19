# Documentation migration verification

## Engineering and skill revision verification (October 19, 2026)

- Installed React best-practices, composition-patterns and web-design-guidelines using the system skill-installer helper at upstream commit `063bee94c3f4df8453406c830b0a7df0f2860278`. Compared every installed file byte-for-byte by SHA-256 against the pinned archive: 76 React, 14 composition and 1 web-design files matched.
- Added canonical engineering guidelines and linked them through the plan, worker entry point, runtime instructions, service requirements, UX plans and gates. Recorded separate web-rule provenance and all six fresh adversarial-review dispositions.
- Checked all 44 Markdown files in the root plan/docs set for relative targets, heading fragments, balanced fences, trailing whitespace and the under-400-line convention: zero errors. Checked tracked whitespace with `git diff --check`; the new untracked guide is included in the Markdown checks.
- A fresh GPT-6.1 Sol/high reviewer inspected the saved revision and reported no actionable findings. See the [review record](../plans/ux/07-adversarial-review.md#october-19-2026-engineering-and-skills-review).
- No application tests, model runs, clinician studies or human-factors acceptance occurred. UX-T01-14 and G0-G7 remain planned requirements; skill installation and documentation checks are not application acceptance.

## UX package verification (October 19, 2026)

- Created eight ordered documents under docs/plans/ux and integrated root navigation, canonical UI requirements, evidence, gate reading guidance, requirement mapping and revision dispositions.
- Checked all 42 Markdown files in the root plan/docs set for relative file targets, heading fragments, balanced fenced blocks and the existing under-400-line convention: zero errors.
- Checked whitespace with git diff --check and inspected new untracked UX Markdown for trailing whitespace: zero errors.
- A fresh gpt-6.1-sol/xhigh reviewer inspected the saved package and related specifications; no remaining actionable contradictions were reported. See the [review record](../plans/ux/07-adversarial-review.md).
- No application tests, authentication implementation, model runs, clinician studies or human-factors acceptance occurred. UX-T01 through UX-T14 remain planned checks.

## Earlier migration verification

Date: 2026-10-19. This records documentation checks only. No application, DGP, model fit, SBC study, simulation evaluation or human review was executed.

## Checks performed

- Parsed the original plan at commit `b21f00003e3f31866f29f9dc20f0d367d39ab11f` and retained all 18 numbered sections in canonical gate documents.
- Compared 483 original paragraphs, list entries, table rows and mathematical/explanatory units after whitespace/citation normalization. Preserved 477; six intentional revisions are documented in [history](revision-history.md) and atomic [traceability](requirement-map.md).
- Preserved all 50 original source IDs. Added 15 evidence entries and verification supplements for nine central original references. Legacy verification gaps remain labeled; external URLs were not all revalidated.
- Checked relative Markdown file targets and heading fragments, balanced fenced blocks, and absence of unresolved original footnotes across the planning package.
- Checked that all S01–S32 scenario IDs are unique and all gate traceability bundles exist.
- Checked whitespace errors with `git diff --check`; inspected newly generated Markdown separately because untracked files are not covered by that command.
- Kept every specification/execution/evidence document below 400 lines, with gate-specific context bundles.

## Remaining work

G0–G7 are requirements, not completed gates. Future G0 work must review the synthetic equations, complete any additional implementation parameters and finalize the estimand-specific analysis contracts. Numerical defaults are engineering assumptions. Clinical and human-factors requirements remain outstanding; legacy evidence records require verification before release reliance.
