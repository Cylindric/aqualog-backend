# api-user-profile Specification

## Purpose
Define authenticated API behavior for viewing and updating the current user's profile.

## Requirements

### Requirement: Authenticated user can read own profile
The system SHALL provide an authenticated endpoint that returns the profile of the current authenticated user, including the username captured at signup.

#### Scenario: Read own profile succeeds
- **WHEN** an authenticated request is made to the current-user profile endpoint
- **THEN** the system returns the persisted profile for the authenticated user, including its username field

#### Scenario: Unauthenticated profile read is rejected
- **WHEN** a request is made to the current-user profile endpoint without a valid OAuth token
- **THEN** the system returns 401 Unauthorized

#### Scenario: Profile read reflects null username
- **WHEN** an authenticated request is made to the current-user profile endpoint for a user whose stored username is null
- **THEN** the response includes a null username value rather than omitting the field

### Requirement: Authenticated user can update own profile
The system SHALL provide an authenticated endpoint that updates allowed profile fields for the current authenticated user. The username field is not user-editable through this endpoint.

#### Scenario: Profile update persists allowed fields
- **WHEN** an authenticated request submits valid updates for allowed profile fields
- **THEN** the system persists those updates and returns the updated profile

#### Scenario: Profile update rejects disallowed fields
- **WHEN** an authenticated request attempts to update fields that are not user-editable
- **THEN** the system rejects the request with a validation error response

#### Scenario: Partial profile update preserves unspecified fields
- **WHEN** an authenticated request updates only a subset of allowed profile fields
- **THEN** fields not included in the request remain unchanged in persisted storage

#### Scenario: Username update attempt is rejected
- **WHEN** an authenticated request attempts to update the username field via the profile update endpoint
- **THEN** the system rejects the request with a validation error response and does not modify the stored username
