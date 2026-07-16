## 1. Persistence Foundation

- [x] 1.1 Add PostgreSQL configuration settings and environment variables for API runtime and tests.
- [x] 1.2 Add container/local bootstrap updates so PostgreSQL is available before API startup.
- [x] 1.3 Introduce migration tooling and create the initial migration for a `users` table with unique OAuth identity mapping and profile timestamps.

## 2. Data Access and User Model

- [x] 2.1 Implement the user persistence model and repository layer for create, lookup by OAuth identity, and profile updates.
- [x] 2.2 Add a user service function that resolves-or-creates the local user from validated OAuth claims.
- [x] 2.3 Add validation rules for editable profile fields and immutable identity fields.

## 3. Authentication Integration

- [x] 3.1 Update OAuth authentication flow to attach resolved local user context to authenticated requests.
- [x] 3.2 Ensure authenticated endpoints consume local user context without breaking existing 401 behavior for missing/invalid/expired tokens.
- [x] 3.3 Add safeguards that prevent duplicate user identity mappings under repeated/auth-concurrent requests.

## 4. Profile API Endpoints

- [x] 4.1 Implement authenticated `GET /v1/me` to return the current user's persisted profile.
- [x] 4.2 Implement authenticated `PATCH /v1/me` to update allowed profile fields and return the updated profile.
- [x] 4.3 Standardize profile endpoint responses and validation errors to existing API response conventions.

## 5. Tests and Verification

- [x] 5.1 Add unit tests for user repository operations and resolve-or-create identity behavior.
- [x] 5.2 Add endpoint tests for `GET /v1/me` and `PATCH /v1/me`, including unauthorized and validation-failure scenarios.
- [x] 5.3 Add authentication integration tests that verify local user creation on first login and reuse on subsequent requests.
- [x] 5.4 Run full test suite and confirm coverage remains at or above project target.
