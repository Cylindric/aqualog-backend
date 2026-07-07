## 1. Configuration and Dependencies

- [x] 1.1 Add OAuth2 configuration fields to config.py (AQUALOG_OAUTH_ISSUER_URL, AQUALOG_OAUTH_AUDIENCE)
- [x] 1.2 Add authlib to project dependencies in pyproject.toml
- [x] 1.3 Run uv sync to install new dependencies
- [x] 1.4 Update .env.example with OAuth2 configuration placeholders

## 2. OAuth2 Authentication Module

- [x] 2.1 Create aqualog_api/auth.py module for OAuth2 token validation
- [x] 2.2 Implement OIDC discovery and JWKS key fetching with caching
- [x] 2.3 Create OAuth2 security scheme for FastAPI using authlib
- [x] 2.4 Implement token validation function with issuer and audience checks
- [x] 2.5 Create FastAPI dependency function for protected endpoints (get_current_user or similar)

## 3. Apply Authentication to Endpoints

- [x] 3.1 Add authentication dependency to salinity dose calculation endpoint in app.py
- [x] 3.2 Verify health endpoints (liveness, readiness) do NOT have authentication dependency
- [x] 3.3 Update FastAPI OpenAPI schema to show authentication requirements

## 4. Error Handling

- [x] 4.1 Implement custom exception handler for authentication failures (401 responses)
- [x] 4.2 Add structured error messages for missing, invalid, and expired tokens
- [x] 4.3 Ensure authentication failures are logged appropriately

## 5. Testing

- [x] 5.1 Create test fixtures for mock OAuth2 tokens and JWKS keys in tests/conftest.py
- [x] 5.2 Add tests for token validation (valid, invalid, expired, missing) in tests/test_auth.py
- [x] 5.3 Update tests/test_salinity_dose.py to include authentication in requests
- [x] 5.4 Add tests verifying health endpoints remain unauthenticated
- [x] 5.5 Verify test coverage meets 80% threshold with coverage report

## 6. Integration Verification

- [x] 6.1 Update docker-compose.yml to include Authentik OAuth2 environment variables
- [x] 6.2 Test API startup with valid OAuth2 configuration
- [x] 6.3 Test API startup failure with missing OAuth2 configuration
- [x] 6.4 Manually verify protected endpoint returns 401 without token
- [x] 6.5 Manually verify health endpoints work without authentication

## 7. Documentation

- [x] 7.1 Update README.md with OAuth2 configuration instructions
- [x] 7.2 Document how to obtain tokens from Authentik for testing
- [x] 7.3 Add OAuth2 setup to any deployment/operations documentation
