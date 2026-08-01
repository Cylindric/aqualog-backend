## Why

Every request currently must pass through live OAuth2/OIDC validation against Authentik, so local development, automated tests against a running server, and any future auth provider swap all require a real IdP round-trip. Making the authentication mechanism configurable — with an explicit "no auth, impersonate a fixed user" mode — removes that dependency for testing and gives the codebase a seam for supporting different auth mechanisms later.

## What Changes

- Add a new `AQUALOG_AUTH_MODE` setting with two supported values: `oauth` (default) and `none`.
- When `AQUALOG_AUTH_MODE=oauth`, authentication behaves exactly as it does today (OIDC discovery, JWKS, token validation, user resolution from token claims) — **no behavior change** for existing deployments that don't set the new variable.
- When `AQUALOG_AUTH_MODE=none`, a new `AQUALOG_AUTH_IMPERSONATE_USER_ID` setting is required and identifies the local `User` row (by id) that every request is authenticated as. No bearer token is required or checked in this mode.
- Fail fast at request time (consistent with existing OAuth misconfiguration handling) with a clear 500 error if:
  - `AQUALOG_AUTH_MODE` is set to an unsupported value, or
  - `AQUALOG_AUTH_MODE=none` but `AQUALOG_AUTH_IMPERSONATE_USER_ID` is missing/blank, or
  - `AQUALOG_AUTH_MODE=none` and the configured user id does not correspond to an existing `User` row (this one can only be checked at request time, since it needs a DB lookup; the other misconfigurations fail at app startup).
- No breaking changes — `oauth` remains the default when `AQUALOG_AUTH_MODE` is unset.

## Capabilities

### New Capabilities
- `api-auth-impersonation`: request authentication that bypasses OAuth2 entirely and resolves the current user to a fixed, pre-configured local user id, for use in test/dev environments.

### Modified Capabilities
- `api-oauth2-authentication`: token validation and OIDC/JWKS behavior become scoped to `AQUALOG_AUTH_MODE=oauth`; add a requirement that authentication mode itself is configurable and validated.

## Impact

- `src/config.py`: new `auth_mode` / `auth_impersonate_user_id` settings fields and validation.
- `src/auth.py`: `get_current_user` branches on `settings.auth_mode` before doing token validation.
- `src/user_repository.py`: new lookup-by-id method to resolve the impersonated user.
- `.env.example` (backend and root), Kubernetes manifests, docker-compose: document the new env vars (no default change required since `oauth` remains default).
- Tests: new coverage for `none` mode (impersonation success, missing/invalid config, unknown user id) alongside existing OAuth test suite.
