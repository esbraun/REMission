# Doctor accounts and application shell

Status: implementation plan. Depends on [00](00-research-and-foundations.md) and accepted G0 contracts.

## Accounts and access

Use the specified React/TypeScript frontend and FastAPI service. Provision synthetic doctor accounts and patient ownership through an administrative seed/CLI operation; no public registration or account-switcher bypass. Each patient has exactly one owning doctor in this version. Other care-team names can be task metadata without granting another account access.

Provide username/password sign-in, sign-out and expired-session states. Store password hashes using a maintained password-hashing implementation; use opaque server-managed sessions, HttpOnly cookies, Secure cookies outside loopback development, SameSite protection and CSRF protection for mutations. Rate-limit login attempts and return generic invalid-credential errors. Administrative password reset revokes sessions.

Authorize patient, task, decision, draft, history, aggregate and job-result access server-side against the authenticated principal. Never trust a doctor ID from a query string as authorization. Unknown and unauthorized resources must not disclose patient details. Scope caches to the principal and patient/context; clear them on logout/expiry.

## Shell and navigation

After sign-in, land on My panel. A selected patient exposes Overview, Current decision, Monitoring and History. Current decision has task-local subviews rather than additional global navigation. Provide Back to My panel with preserved list context.

Reserve a persistent banner for synthetic patient name and ID, current/historical mode, selected decision/date, cutoff/freshness and relevant hold. Keep the synthetic demonstration label visible. Update identity before enabling controls after patient switching.

Use explicit URL context: patient ID and destination; task/decision ID when applicable; historical mode and selected snapshot for historical routes. Reload must preserve historical mode. Navigation never advances clinical or learning state.

## Interfaces

- Session capability: login, current principal, logout; expiry returns an authentication failure.
- Principal: stable doctor ID and display name; ownership is resolved on the server.
- Patient shell context: patient identifiers, current clinical/learning state, selected decision, mode, freshness and server-derived permissions.
- Patient/task data requests are canceled or ignored when their context no longer matches the active route. Invalidate outstanding requests across logout, expiry and reauthentication, including when the same doctor signs in again. Use an authentication-generation guard in addition to principal/patient context; cancellation alone must not allow a late response to restore content.
- Session expiry hides patient content, clears client caches and unsaved local drafts, and returns to sign-in. Only explicitly saved server drafts can be recovered after authentication.

## Acceptance

Use two doctors with disjoint synthetic panels. Verify direct API/URL access, history, drafts, aggregate counts, nested resources and async job results cannot cross ownership boundaries. Test login failures, logout, expiry, browser Back after logout and a delayed patient response arriving after a switch. Patient identity and active data must always agree. Include logout and same-doctor reauthentication with a delayed pre-logout response. Exercise real cookie/session middleware, CSRF enforcement, expiry and administrative password-reset revocation through service routes; injecting a principal does not satisfy these checks.

Sources: [foundation](00-research-and-foundations.md), especially NIST identity guidance and NHS consistency. Authentication choices are engineering requirements, not UX research findings.
