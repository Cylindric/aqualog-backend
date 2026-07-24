## 1. Data model

- [x] 1.1 Add nullable `username: Mapped[str | None]` column to `User` in `src/models.py`
- [x] 1.2 Generate Alembic migration via `task db-migration-new NAME="add_username_to_users"` and verify it only adds the nullable column
- [x] 1.3 Run `task db-migrate` locally to confirm the migration applies cleanly

## 2. User creation

- [x] 2.1 Update `UserRepository.create_for_identity` (and `resolve_or_create`) in `src/user_repository.py` to accept and persist an optional `username`
- [x] 2.2 Update `resolve_or_create_authenticated_user` in `src/user_service.py` to extract `preferred_username` from `claims` and pass it to `resolve_or_create`
- [x] 2.3 Confirm existing-user resolution path does not overwrite a previously stored `username`

## 3. Profile exposure

- [x] 3.1 Add read-only `username` field to the profile response payload in `src/profile.py` (`_to_profile_payload`)
- [x] 3.2 Ensure the profile update request model rejects/ignores `username` if submitted (not part of the editable `ProfileUpdate` fields)

## 4. Tests

- [x] 4.1 Update/add repository tests in `tests/test_user_repository.py` covering: username captured on creation, null-username fallback when claim missing, username preserved (not re-synced) on repeat login
- [x] 4.2 Update router-level tests (`tests/test_profile.py` or equivalent) to assert `username` appears in the GET profile response, including the null case
- [x] 4.3 Add/adjust a router-level test asserting a `PATCH` profile request including `username` does not change the stored value (validation error or silently ignored, per implementation choice in 3.2)
- [x] 4.4 Run `task test` and confirm coverage stays ≥ 80%

## 5. Docs/spec sync

- [x] 5.1 Verify delta specs under `openspec/changes/capture-username-on-signup/specs/` accurately reflect the implemented behavior before running `/opsx:sync` or archive
