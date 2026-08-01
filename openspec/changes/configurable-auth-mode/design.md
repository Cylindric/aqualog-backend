## Context

`get_current_user` (`src/auth.py`) is the sole FastAPI dependency protecting endpoints. Today it unconditionally: reads `Settings.oauth_issuer_url`/`oauth_audience`, requires a bearer token, validates it via OIDC/JWKS (`validate_token`), and resolves/creates a local `User` via `resolve_or_create_authenticated_user`. `Settings` (`src/config.py`) is a flat `pydantic-settings` model reading `AQUALOG_*` env vars, with no concept of an auth "mode" today. This affects local dev, running the test server without Authentik, and any CI/e2e flow that currently needs a real token.

## Goals / Non-Goals

**Goals:**
- Let `AQUALOG_AUTH_MODE` select between `oauth` (current behavior, default) and `none` (impersonate a fixed local user, no token required).
- Keep `oauth` mode's request-time behavior and error messages unchanged when `AQUALOG_AUTH_MODE` is unset, so existing deployments need zero config changes.
- Make `none` mode fail loudly and specifically when misconfigured (bad mode value, missing impersonation id, unknown user id) rather than silently granting access as some ambiguous/anonymous identity.

**Non-Goals:**
- No new auth providers beyond `oauth`/`none` (design should not preclude adding one later, but isn't building a plugin system now).
- No change to token validation logic itself, to `AuthenticatedUser`'s shape, or to how routers depend on `get_current_user`.
- `none` mode is not gated to non-prod environments by this change (see Risks) — deployment operators are expected not to set it in prod, same trust level as other `AQUALOG_*` secrets.

## Decisions

**1. `auth_mode: Literal["oauth", "none"] = "oauth"` on `Settings`, plus `auth_impersonate_user_id: str | None = None`.**
Mirrors the existing flat-settings style (`oauth_issuer_url`, etc.) rather than introducing a nested/discriminated settings sub-model. A `Literal` gives pydantic free validation of unsupported values at settings-construction time (app startup), rather than needing a manual check. Alternative considered: a boolean `AQUALOG_AUTH_DISABLED` flag — rejected because the proposal explicitly asks for a mode selector that can grow beyond two values later, and `none` reads better than `disabled` (auth isn't disabled, it's just resolved differently).

**2. Branch inside `get_current_user`, not via a second dependency or DI swap.**
`get_current_user` becomes a thin dispatcher: `if settings.auth_mode == "none": return await _impersonate_user(...)` else run the existing oauth path unchanged (moved into a private `_authenticate_oauth` helper, same logic/exceptions as today). Alternative considered: select the dependency function itself at router-include time (`Depends(get_current_user_none if mode == "none" else get_current_user_oauth)`) — rejected because `settings.app.state.settings` is only known at request time via `request.app.state`, not at router-registration time in `create_app`, and routers already uniformly depend on `get_current_user` by name; branching inside keeps that contract.

**3. `none` mode resolves the user via a new `UserRepository.get_by_id`, does not auto-create.**
Unlike OAuth (which creates a local user on first sight of a new issuer/subject), impersonation has no claims to create a sensible user from — only an id. If that id doesn't exist, the operator has misconfigured the env var (typo, wrong environment's user id) and should get an explicit error rather than a silently-created throwaway user. Verified (`grep -rn ".claims" src/`) that no router or downstream code reads `AuthenticatedUser.claims` — only `.user` is used — so `_authenticate_impersonated` populates `claims={}` rather than inventing synthetic issuer/subject values nothing consumes.

**4. Both modes fail fast at app-serving startup (inside `create_app()`), via a plain `ensure_auth_mode_configured(settings)` function — not a `Settings` model validator.**
A model validator was tried first and reverted: `grep -rn "load_settings\|Settings(" alembic/` shows `alembic/env.py` also calls `load_settings()` → `Settings()` at import time, purely to read `settings.database_url` for migrations — it has no OAuth/impersonation config and no reason to need any. A `Settings`-level validator requiring that config would have broken `task db-migrate`/`alembic upgrade head` (and any CI job that only has DB credentials) the moment `auth_mode` defaults to `oauth` with no issuer/audience set. Instead, `ensure_auth_mode_configured(settings)` lives next to `Settings` in `src/config.py` but is called explicitly and only from `create_app()` (verified via `grep -rn "load_settings\|create_app("` that `create_app()` calls `load_settings()` on the real startup path, not lazily inside a request handler), immediately after settings are loaded and before the app is returned. It requires `oauth_issuer_url` and `oauth_audience` when `auth_mode == "oauth"`, and a non-blank `auth_impersonate_user_id` when `auth_mode == "none"`, raising `RuntimeError` — this is what actually makes the existing "OAuth2 configuration is loaded at startup... MUST fail fast" spec language true for the app-serving path specifically (today it's only enforced at request time in `get_current_user`; this change corrects that without coupling every `Settings()` consumer to auth config). The one thing that still can't be validated at this point is whether the configured impersonation user id exists in the DB — no DB connection is established yet — so that check stays in `get_current_user`/`_authenticate_impersonated` and returns `HTTPException(500, "Authentication service is not configured")` at request time, same status/message family as other configuration errors.

## Risks / Trade-offs

- **[Risk] Operator accidentally leaves `AQUALOG_AUTH_MODE=none` set in a real deployment, bypassing auth entirely.** → Mitigation: this is an explicit, non-default opt-in env var (same trust boundary as other `AQUALOG_*` secrets like DB credentials); document prominently in `.env.example` and README/deploy docs that `none` is dev/test-only. No code-level environment gating is added, consistent with not hardcoding environment assumptions elsewhere in `src/config.py`.
- **[Risk] Impersonated user id silently drifts (e.g. user deleted) → every request now 500s.** → Mitigation: this is the desired fail-fast behavior per proposal; the 500 message is specific enough (once implemented) to point at the misconfiguration.
- **[Trade-off] No startup-time validation that the impersonated user id actually exists (DB isn't guaranteed ready before settings load).** → Accepted: presence of the config value is validated at startup; existence in the DB is unavoidably a request-time check. This is a narrower gap than today's behavior, where the entire OAuth config check happens at request time despite the spec's startup-failure wording — this change fixes that inconsistency rather than extending it.
