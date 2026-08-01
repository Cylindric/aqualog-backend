## MODIFIED Requirements

### Requirement: OAuth2 token validation is available for endpoint protection
The system SHALL provide OAuth2 bearer token validation that can be applied to API endpoints, and SHALL resolve validated token identity to a persisted local user context for endpoint handlers, when the configured authentication mode is `oauth`.

#### Scenario: Valid token grants access to protected endpoint
- **WHEN** the authentication mode is `oauth` and a request includes a valid OAuth2 bearer token in the Authorization header
- **THEN** the token is validated, the local user is resolved, and the request proceeds to the endpoint handler

#### Scenario: Missing token is rejected with 401
- **WHEN** the authentication mode is `oauth` and a request to a protected endpoint is made without an Authorization header
- **THEN** the system returns a 401 Unauthorized response

#### Scenario: Invalid token is rejected with 401
- **WHEN** the authentication mode is `oauth` and a request includes a malformed or invalid bearer token
- **THEN** the system returns a 401 Unauthorized response with appropriate error details

#### Scenario: Expired token is rejected with 401
- **WHEN** the authentication mode is `oauth` and a request includes an expired bearer token
- **THEN** the system returns a 401 Unauthorized response indicating token expiration

#### Scenario: New OAuth identity is persisted on first successful authentication
- **WHEN** the authentication mode is `oauth` and a valid token is presented for an OAuth identity with no associated local user
- **THEN** the system creates and associates a persisted local user before the request reaches the endpoint handler

#### Scenario: Existing OAuth identity reuses persisted local user
- **WHEN** the authentication mode is `oauth` and a valid token is presented for an OAuth identity already associated with a local user
- **THEN** the system loads the existing local user association and does not create a duplicate user

### Requirement: Calculation endpoints require authentication
The system SHALL enforce authentication on all calculation endpoints when the configured authentication mode is `oauth`.

#### Scenario: Salinity dose calculation requires valid token
- **WHEN** the authentication mode is `oauth` and a request is made to `/calculate/dose/salinity` without a valid token
- **THEN** the system returns 401 Unauthorized before processing the calculation

#### Scenario: Authenticated calculation request is processed
- **WHEN** the authentication mode is `oauth` and a request to a calculation endpoint includes a valid bearer token
- **THEN** the calculation is performed and results are returned

### Requirement: OAuth2 configuration is loaded at startup
The system MUST load OAuth2 provider configuration at startup and MUST fail fast if required OAuth2 settings are missing, when the configured authentication mode is `oauth`.

#### Scenario: Startup fails when OAuth2 issuer URL is missing
- **WHEN** the authentication mode is `oauth` and the application starts without the OAuth2 issuer URL configured
- **THEN** the system exits with a configuration error

#### Scenario: Startup fails when OAuth2 audience is missing
- **WHEN** the authentication mode is `oauth` and the application starts without the OAuth2 audience configured
- **THEN** the system exits with a configuration error

#### Scenario: Startup succeeds with valid OAuth2 configuration
- **WHEN** the authentication mode is `oauth` and all required OAuth2 configuration values are present and valid
- **THEN** the application completes startup and token validation is available

## ADDED Requirements

### Requirement: Authentication mode is configurable and validated
The system SHALL support selecting the authentication mechanism via an `AQUALOG_AUTH_MODE` setting with allowed values `oauth` and `none`, SHALL default to `oauth` when unset, and MUST fail fast if an unsupported value is configured.

#### Scenario: Authentication mode defaults to oauth
- **WHEN** the application starts without `AQUALOG_AUTH_MODE` set
- **THEN** the system behaves as if `oauth` mode were explicitly configured

#### Scenario: Unsupported authentication mode is rejected at startup
- **WHEN** the application starts with `AQUALOG_AUTH_MODE` set to a value other than `oauth` or `none`
- **THEN** the system fails to start with a configuration error
