## 1. Settings

- [ ] 1.1 Add `auth_mode: Literal["oauth", "none"] = "oauth"` and `auth_impersonate_user_id: str | None = None` fields to `Settings` in `src/config.py`
- [ ] 1.2 Confirm pydantic rejects an unsupported `AQUALOG_AUTH_MODE` value at `Settings()` construction (covered by `Literal`; add a test)
- [ ] 1.3 Add a `model_validator(mode="after")` on `Settings` that raises when: `auth_mode == "oauth"` and `oauth_issuer_url` or `oauth_audience` is missing; or `auth_mode == "none"` and `auth_impersonate_user_id` is missing/blank. This makes `Settings()` construction (called from `create_app` on the startup path) fail fast for both modes.
- [ ] 1.4 Tests: `Settings()` raises for `oauth` mode missing issuer/audience, and for `none` mode missing/blank `auth_impersonate_user_id`; `Settings()` succeeds for valid config in both modes

## 2. User lookup by id

- [ ] 2.1 Add `UserRepository.get_by_id(user_id: str) -> User | None` in `src/user_repository.py`, returning `None` for both "not found" and an unparseable/invalid id (don't let a bad id raise)
- [ ] 2.2 Add repository-level tests for `get_by_id`: existing id, unknown id, malformed id

## 3. Impersonation authentication path

- [ ] 3.1 In `src/auth.py`, extract the current OAuth logic out of `get_current_user` into a private `_authenticate_oauth(request, credentials, session, settings)` helper with unchanged behavior. The existing missing-issuer/audience 500 check becomes unreachable in practice once 1.3 lands (settings construction would already have failed) but can stay as a defensive guard.
- [ ] 3.2 Add a private `_authenticate_impersonated(session, settings)` helper: look up the user via `UserRepository.get_by_id(settings.auth_impersonate_user_id)`, return `HTTPException(500, "Authentication service is not configured")` if not found, otherwise return `AuthenticatedUser(claims={}, user=user)`
- [ ] 3.3 `get_current_user` dispatches on `settings.auth_mode`: `none` → `_authenticate_impersonated`, `oauth` (default) → `_authenticate_oauth`, unchanged signature/return type either way
- [ ] 3.4 Confirm bearer credentials are accepted-but-ignored in `none` mode (dependency still declares `credentials: HTTPAuthorizationCredentials | None = Depends(security)` so both token-present and token-absent requests work identically)

## 4. Tests

- [ ] 4.1 Router/dependency-level tests for `none` mode: request without Authorization header succeeds and returns data scoped to the impersonated user; request with an Authorization header also succeeds and is still resolved to the impersonated user
- [ ] 4.2 Test: `none` mode with an unknown/nonexistent user id returns 500 and does not create a new `User` row (the missing-id-entirely case is covered by the `Settings()` startup test in 1.4, not here)
- [ ] 4.3 Confirm existing `oauth` mode test suite (`test_aquariums.py`, `test_calculations.py`, etc.) still passes unmodified with `AQUALOG_AUTH_MODE` unset (default)
- [ ] 4.4 Run `task test` and confirm coverage stays at/above the existing threshold

## 5. Config surface & docs

- [ ] 5.1 Add `AQUALOG_AUTH_MODE` and `AQUALOG_AUTH_IMPERSONATE_USER_ID` to backend `.env.example` (and root `.env.example` if OAuth vars are mirrored there), documented as dev/test-only for `none`
- [ ] 5.2 Note the new env vars in relevant Kubernetes manifests / docker-compose docs only if other `AQUALOG_*` auth vars are already enumerated there — do not wire `none` into any deployed environment's actual config values

## 6. Verification

- [ ] 6.1 `task lint` / `task format-check` / `task typecheck` all pass
- [ ] 6.2 Manually exercise both modes locally (`task server` with `AQUALOG_AUTH_MODE=none` + a real user id, and unchanged default) against a protected endpoint
