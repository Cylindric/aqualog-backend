# api-oauth2-authentication Specification

## Purpose
TBD - created by archiving change add-oauth2-authentication. Update Purpose after archive.
## Requirements
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

### Requirement: Token validation uses OIDC discovery
The system SHALL discover OAuth2 provider configuration via OIDC discovery endpoint and validate tokens using the provider's JWKS keys.

#### Scenario: JWKS keys are fetched from provider
- **WHEN** the application starts or needs to refresh validation keys
- **THEN** the system fetches the current JWKS from the OIDC provider's published endpoint

#### Scenario: Token signature is validated against JWKS
- **WHEN** a bearer token is presented for validation
- **THEN** the system verifies the token signature using the appropriate key from JWKS

#### Scenario: Token issuer claim matches expected issuer
- **WHEN** a token is validated
- **THEN** the system verifies the `iss` claim matches the configured OAuth2 issuer URL

#### Scenario: Token audience claim is validated
- **WHEN** a token is validated
- **THEN** the system verifies the `aud` claim contains the configured audience identifier

### Requirement: Calculation endpoints require authentication
The system SHALL enforce authentication on all calculation endpoints.

#### Scenario: Salinity dose calculation requires valid token
- **WHEN** a request is made to `/calculate/dose/salinity` without a valid token
- **THEN** the system returns 401 Unauthorized before processing the calculation

#### Scenario: Authenticated calculation request is processed
- **WHEN** a request to a calculation endpoint includes a valid bearer token
- **THEN** the calculation is performed and results are returned

### Requirement: OAuth2 configuration is loaded at startup
The system MUST load OAuth2 provider configuration at startup and MUST fail fast if required OAuth2 settings are missing.

#### Scenario: Startup fails when OAuth2 issuer URL is missing
- **WHEN** the application starts without the OAuth2 issuer URL configured
- **THEN** the system exits with a configuration error

#### Scenario: Startup fails when OAuth2 audience is missing
- **WHEN** the application starts without the OAuth2 audience configured
- **THEN** the system exits with a configuration error

#### Scenario: Startup succeeds with valid OAuth2 configuration
- **WHEN** all required OAuth2 configuration values are present and valid
- **THEN** the application completes startup and token validation is available

