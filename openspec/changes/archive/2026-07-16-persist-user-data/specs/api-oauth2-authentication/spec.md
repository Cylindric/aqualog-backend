## Purpose

Ensure OAuth-authenticated requests are bound to a persisted local user identity.

## MODIFIED Requirements

### Requirement: OAuth2 token validation is available for endpoint protection
The system SHALL provide OAuth2 bearer token validation that can be applied to API endpoints, and SHALL resolve validated token identity to a persisted local user context for endpoint handlers.

#### Scenario: Valid token grants access to protected endpoint
- **WHEN** a request includes a valid OAuth2 bearer token in the Authorization header
- **THEN** the token is validated, the local user is resolved, and the request proceeds to the endpoint handler

#### Scenario: Missing token is rejected with 401
- **WHEN** a request to a protected endpoint is made without an Authorization header
- **THEN** the system returns a 401 Unauthorized response

#### Scenario: Invalid token is rejected with 401
- **WHEN** a request includes a malformed or invalid bearer token
- **THEN** the system returns a 401 Unauthorized response with appropriate error details

#### Scenario: Expired token is rejected with 401
- **WHEN** a request includes an expired bearer token
- **THEN** the system returns a 401 Unauthorized response indicating token expiration

#### Scenario: New OAuth identity is persisted on first successful authentication
- **WHEN** a valid token is presented for an OAuth identity with no associated local user
- **THEN** the system creates and associates a persisted local user before the request reaches the endpoint handler

#### Scenario: Existing OAuth identity reuses persisted local user
- **WHEN** a valid token is presented for an OAuth identity already associated with a local user
- **THEN** the system loads the existing local user association and does not create a duplicate user
