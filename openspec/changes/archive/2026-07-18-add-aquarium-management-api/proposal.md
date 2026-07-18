## Why

Users currently lack a dedicated API area to manage aquariums they own. We need this now to support account-scoped aquarium lifecycle workflows (create, view, edit, delete) and establish a clear ownership boundary for future features.

## What Changes

- Add a new authenticated Aquarium management API category.
- Enforce aquarium ownership so each aquarium is associated with exactly one user.
- Restrict aquarium visibility so users can only list and fetch their own aquariums.
- Add endpoints for creating, updating, and deleting user-owned aquariums.
- Define initial aquarium properties: name, type, and volume.

## Capabilities

### New Capabilities
- `api-aquarium-management`: User-scoped aquarium CRUD requirements including ownership, authorization boundaries, and initial aquarium data fields.

### Modified Capabilities
- None.

## Impact

- API surface: New aquarium endpoints under authenticated API.
- Data model/storage: New persisted aquarium entity linked to user records.
- Authorization: Ownership checks on all aquarium reads/writes/deletes.
- Testing: New unit/integration/endpoint tests for ownership, validation, and CRUD behavior.
