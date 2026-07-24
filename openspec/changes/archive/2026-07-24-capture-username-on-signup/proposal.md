## Why

When a new user first authenticates via OAuth, the backend persists a local `User` row keyed only on `oauth_issuer` + `oauth_subject`. No human-readable username is captured, so there is no way to identify a user (in admin views, support, or the profile response) without cross-referencing the identity provider. The OIDC token already carries a `preferred_username` claim that goes unused at signup time.

## What Changes

- Add a `username` column to the `User` model, populated from the OAuth token's `preferred_username` claim the first time a local user record is created for that identity.
- `resolve_or_create_authenticated_user` / `UserRepository.resolve_or_create` capture and persist this value on creation only — existing users are not retroactively updated by this change.
- If `preferred_username` is missing from the token claims, fall back to storing `null` rather than failing signup.
- Expose `username` as a read-only field in the profile GET response (not editable via the profile update endpoint).
- Add an Alembic migration adding the nullable `username` column to `users`.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `api-user-persistence`: user creation now also captures and stores the OAuth `preferred_username` claim as `username` at first-login time.
- `api-user-profile`: the profile read response now includes the stored `username` alongside existing profile fields.

## Impact

- `src/models.py` (`User` model), `src/user_repository.py`, `src/user_service.py`, `src/profile.py`.
- New Alembic migration under `alembic/versions/`.
- `tests/test_user_repository.py`, `tests/test_users.py`/`tests/test_profile.py` (or equivalents) need coverage for the new field.
