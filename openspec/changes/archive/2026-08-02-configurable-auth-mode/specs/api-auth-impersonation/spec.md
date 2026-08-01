## ADDED Requirements

### Requirement: Impersonation mode bypasses token validation for a fixed local user
The system SHALL, when `AQUALOG_AUTH_MODE` is `none`, resolve every request's authenticated user to a single pre-configured local user identified by `AQUALOG_AUTH_IMPERSONATE_USER_ID`, without requiring or validating a bearer token.

#### Scenario: Request without a bearer token succeeds in none mode
- **WHEN** the authentication mode is `none` and a request is made to a protected endpoint without an Authorization header
- **THEN** the system resolves the configured impersonated user and the request proceeds to the endpoint handler

#### Scenario: Bearer token, if present, is ignored in none mode
- **WHEN** the authentication mode is `none` and a request includes an Authorization header
- **THEN** the system does not validate the token and still resolves the request to the configured impersonated user

#### Scenario: Impersonated user is loaded from persisted storage
- **WHEN** the authentication mode is `none` and the configured impersonation user id corresponds to an existing local user
- **THEN** the system loads that user's record and makes it available to the endpoint handler exactly as it would for an OAuth-resolved user

### Requirement: Impersonation mode requires an explicit, valid user id
The system MUST fail fast at startup when `AQUALOG_AUTH_MODE` is `none` and the impersonation user id is missing, and MUST fail authentication with a configuration error when the configured id does not correspond to an existing local user.

#### Scenario: Missing impersonation user id is rejected at startup
- **WHEN** the application starts with `AQUALOG_AUTH_MODE` set to `none` and `AQUALOG_AUTH_IMPERSONATE_USER_ID` not set (or blank)
- **THEN** the system fails to start with a configuration error

#### Scenario: Unknown impersonation user id is rejected
- **WHEN** the authentication mode is `none` and `AQUALOG_AUTH_IMPERSONATE_USER_ID` does not match any existing local user
- **THEN** the system returns a 500 error indicating authentication is not configured, for every request

#### Scenario: Impersonation mode does not create new users
- **WHEN** the authentication mode is `none` and the configured impersonation user id does not exist
- **THEN** the system does not create a new local user for that id
