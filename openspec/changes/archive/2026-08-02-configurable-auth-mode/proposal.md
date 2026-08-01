## Why

Every request currently must pass through live OAuth2/OIDC validation against Authentik, so local development, automated tests against a running server, and any future auth provider swap all require a real IdP round-trip. Making the authentication mechanism configurable — with an explicit "no auth, impersonate a fixed user" mode — removes that dependency for testing and gives the codebase a seam for supporting different auth mechanisms later.

## What Changes

- Add a new `AQUALOG_AUTH_MODE` setting with two supported values: `oauth` (default) and `none`.
- When `AQUALOG_AUTH_MODE=oauth`, per-request authentication behaves exactly as it does today (OIDC discovery, JWKS, token validation, user resolution from token claims).
- When `AQUALOG_AUTH_MODE=none`, a new `AQUALOG_AUTH_IMPERSONATE_USER_ID` setting is required and identifies the local `User` row (by id) that every request is authenticated as. No bearer token is required or checked in this mode.
- The app now fails fast at startup (before it starts serving requests) if `AQUALOG_AUTH_MODE` is unsupported, or if the config required by the selected mode (`oauth`'s issuer/audience, or `none`'s impersonation user id) is missing. This is a behavior change from today, where a misconfigured-but-unset-mode app would still start and only 500 once a protected endpoint was hit — deployments that already set valid OAuth config are unaffected either way. Tooling that only needs DB config (e.g. `alembic`/`task db-migrate`) is unaffected, since this check runs only on the app-serving path, not on every `Settings` construction.
- One thing can only be checked at request time, since it needs a DB lookup: `AQUALOG_AUTH_MODE=none` with a configured user id that doesn't correspond to an existing `User` row still returns a 500 per request rather than failing at startup.

## Capabilities

### New Capabilities
- `api-auth-impersonation`: request authentication that bypasses OAuth2 entirely and resolves the current user to a fixed, pre-configured local user id, for use in test/dev environments.

### Modified Capabilities
- `api-oauth2-authentication`: token validation and OIDC/JWKS behavior become scoped to `AQUALOG_AUTH_MODE=oauth`; add a requirement that authentication mode itself is configurable and validated.

## Impact

- `src/config.py`: new `auth_mode` / `auth_impersonate_user_id` settings fields, plus an `ensure_auth_mode_configured()` fail-fast check.
- `src/app.py`: `create_app()` calls `ensure_auth_mode_configured()` right after loading settings, before the app is returned.
- `src/auth.py`: `get_current_user` branches on `settings.auth_mode` before doing token validation.
- `src/user_repository.py`: new lookup-by-id method to resolve the impersonated user.
- `.env.example` (backend and root), Kubernetes manifests, docker-compose: document the new env vars (no default change required since `oauth` remains default).
- Tests: new coverage for `none` mode (impersonation success, missing/invalid config, unknown user id) alongside existing OAuth test suite.
