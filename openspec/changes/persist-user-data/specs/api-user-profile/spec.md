## Purpose

Define authenticated API behavior for viewing and updating the current user's profile.

## ADDED Requirements

### Requirement: Authenticated user can read own profile
The system SHALL provide an authenticated endpoint that returns the profile of the current authenticated user.

#### Scenario: Read own profile succeeds
- **WHEN** an authenticated request is made to the current-user profile endpoint
- **THEN** the system returns the persisted profile for the authenticated user

#### Scenario: Unauthenticated profile read is rejected
- **WHEN** a request is made to the current-user profile endpoint without a valid OAuth token
- **THEN** the system returns 401 Unauthorized

### Requirement: Authenticated user can update own profile
The system SHALL provide an authenticated endpoint that updates allowed profile fields for the current authenticated user.

#### Scenario: Profile update persists allowed fields
- **WHEN** an authenticated request submits valid updates for allowed profile fields
- **THEN** the system persists those updates and returns the updated profile

#### Scenario: Profile update rejects disallowed fields
- **WHEN** an authenticated request attempts to update fields that are not user-editable
- **THEN** the system rejects the request with a validation error response

#### Scenario: Partial profile update preserves unspecified fields
- **WHEN** an authenticated request updates only a subset of allowed profile fields
- **THEN** fields not included in the request remain unchanged in persisted storage
