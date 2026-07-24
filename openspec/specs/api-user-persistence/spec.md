# api-user-persistence Specification

## Purpose
Define durable storage requirements for application user records and their profile data.

## Requirements

### Requirement: Authenticated identities are mapped to persisted users
The system SHALL persist a local user record for each authenticated OAuth identity and SHALL use that persisted record for subsequent authenticated requests. When creating a new local user record, the system SHALL capture the OAuth token's `preferred_username` claim, if present, as the persisted user's username.

#### Scenario: First authenticated request creates a local user
- **WHEN** a valid OAuth token is accepted for an identity that has no existing local user record
- **THEN** the system creates a new persisted user and associates it with that OAuth identity

#### Scenario: Existing authenticated identity resolves to existing user
- **WHEN** a valid OAuth token is accepted for an identity that is already associated with a local user record
- **THEN** the system loads the existing persisted user without creating a duplicate record

#### Scenario: Duplicate identity association is prevented
- **WHEN** the system attempts to create a user mapping for an OAuth identity that is already associated
- **THEN** the operation is rejected or resolved without creating a second user mapping for the same identity

#### Scenario: Username is captured from token claims at creation
- **WHEN** a new local user record is created from a valid OAuth token whose claims include `preferred_username`
- **THEN** the persisted user record stores that value as its username

#### Scenario: Missing username claim does not block signup
- **WHEN** a new local user record is created from a valid OAuth token whose claims do not include `preferred_username`
- **THEN** the system creates the user record with a null username rather than rejecting the request

#### Scenario: Username is not re-captured for existing users
- **WHEN** a valid OAuth token is accepted for an identity that already has a persisted local user record
- **THEN** the system does not modify the existing user's stored username, even if the token's `preferred_username` claim differs from the stored value

### Requirement: User persistence stores profile data durably
The system SHALL persist user profile attributes in durable storage and SHALL make stored values available across API restarts.

#### Scenario: Persisted profile survives restart
- **WHEN** a user's profile data has been written and the API service restarts
- **THEN** a subsequent read returns the same persisted profile data

#### Scenario: Profile timestamps are tracked
- **WHEN** a user record is created or updated
- **THEN** the system records creation and update timestamps for the persisted user profile
