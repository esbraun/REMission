# Tooltips and guides for each view

Status: implementation plan. Depends on shell/view definitions; implement alongside each view, not after UI completion.

## Help hierarchy

Use brief tooltips for unfamiliar terms, abbreviations and symbols. Required values, uncertainty, blockers, validation errors and action consequences remain inline. Interactive links or lengthy explanations belong in the guide.

Each view has a consistently placed Guide to this view button, including sign-in, panel, overview, each task-local view, monitoring and history. Guide topics follow route, task variant and current/historical mode.

## Interaction and content

On desktop open a nonmodal side panel that reflows the workspace and permits continued work. On narrow screens use a modal guide with focus moved inside, keyboard containment, Escape/close and focus restoration. Never cover active controls with a desktop overlay. Provide a labeled keyboard path between the workspace and nonmodal guide.

Guide content: purpose; what to review; how to interpret this display; available actions; blockers/recovery; next step; related appendix sections. Context follows navigation while open; the heading announces its new subject. Do not open help automatically or destroy draft input. Only one guide/appendix help surface is open at once, with Back to guide when following a documentation link.

Tooltips work on hover and focus, remain hoverable/persistent, dismiss with Escape and do not contain focusable links. Touch users get an equivalent labeled tap disclosure. Use aria-describedby for tooltip association and visible focus for triggers.

## Interface and acceptance

A versioned topic registry maps view ID, task variant and mode to topic content and appendix anchors. Missing topics are a build-validation failure; runtime shows an explicit help-unavailable message rather than an unrelated fallback topic.

Verify keyboard-only and touch access, screen-reader labeling, focus return, narrow layouts, context changes, draft preservation and no nested modal traps. Observe whether intended users can understand the primary action without opening help.

Sources: [Cloudscape](https://cloudscape.design/patterns/general/help-system/), [WCAG hover/focus](https://www.w3.org/WAI/WCAG22/Understanding/content-on-hover-or-focus.html), [WAI dialog pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/).
