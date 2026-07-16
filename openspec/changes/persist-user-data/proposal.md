## Why

The API currently performs calculations and authentication checks, but it does not persist user data. We need durable user records and profile data so authenticated users have an account context that can support current profile behavior and future user-scoped features.

## What Changes

- Introduce persistent storage for user data using a relational database suitable for authenticated account records and profile attributes.
- Add a first-class `user` entity model keyed to the OAuth identity used by the existing authentication flow.
- Add authenticated profile read/update behavior for the signed-in user.
- Define bootstrap expectations for local/dev and containerized environments so persistence is consistently available.

## Capabilities

### New Capabilities
- `api-user-persistence`: Defines requirements for durable user data storage, the user entity schema, and identity mapping from OAuth claims.
- `api-user-profile`: Defines requirements for authenticated user profile retrieval and updates.

### Modified Capabilities
- `api-oauth2-authentication`: Extend authentication requirements to ensure OAuth-authenticated users are resolved to a persisted local user record.

## Impact

- Affected code: authentication integration, new persistence/data-access layer, and new profile endpoints.
- APIs: new authenticated user profile endpoint(s) and response contracts.
- Dependencies/systems: add and configure a production-suitable database (for example PostgreSQL) and related environment configuration.
- Testing: add unit and integration tests for persistence behavior, OAuth identity linking, and profile endpoint behavior.