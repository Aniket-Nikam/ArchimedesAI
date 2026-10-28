# Release scope and compatibility

The release hardening preserves the research workspace, existing database IDs, endpoint paths and saved data. Client-supplied user IDs remain optional for compatibility, but authorization now comes exclusively from the server session. Existing API callers must sign in, retain the session cookie and send the returned CSRF token as `X-CSRF-Token` on mutations.

## Shared-module reuse assessment

Before implementation, the Buildable-Comps registry was searched and the stable `identity.auth` and `identity.users` manifests, READMEs and public exports were inspected. Auth requires users. Its UUID/SQLAlchemy identity contract and versioned routes are incompatible with this application's existing SQLite integer users, foreign keys and history contract.

Copying those modules would require a separate data/API migration and consuming-app wiring. This change instead retains ArchimedesAI's existing password service and adds an application-specific session adapter. No Buildable-Comps shared module, manifest, migration or registry was modified.

## Acceptance checks

- Authenticated isolation for history, bookmarks, exports and project assignment.
- Revocable expiring sessions, CSRF/origin checks, and password endpoint rate limiting.
- Bounded research/provider admission, finite retries, timeout and cooperative cancellation.
- Stable saved-report IDs, normalized deduplication, honest source/retraction states.
- Server-owned citation downloads and working reading-list input to Manuscript Studio.
- Responsive desktop/mobile UI, keyboard navigation and reduced-motion support.
- Regression tests, frontend production build, code checks and CI configuration.
- A live Groq-backed run remains necessary before describing this revision as release complete.
