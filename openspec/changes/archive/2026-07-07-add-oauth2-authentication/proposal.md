## Why

The API currently has no authentication mechanism, allowing unrestricted access to all endpoints. This poses security risks and prevents proper user authorization for an aquarium management platform that will handle user-specific data.

## What Changes

- Add OAuth2/OIDC authentication using Authentik (already in docker-compose stack)
- Protect all calculation and data endpoints with authentication requirements
- Maintain unauthenticated access to health/liveness endpoints for monitoring
- Add token validation and request authentication middleware to the API service
- Configure FastAPI security dependencies for OAuth2

## Capabilities

### New Capabilities
- `api-oauth2-authentication`: OAuth2/OIDC authentication integration with Authentik, including token validation, authentication middleware, and endpoint protection configuration

### Modified Capabilities
- `api-service-bootstrap`: Add authentication middleware to the request lifecycle
- `api-health-endpoints`: Explicitly define that health endpoints remain unauthenticated for operational monitoring

## Impact

- All existing calculation endpoints (e.g., `/calculate/dose/salinity`) will require valid authentication tokens
- New dependencies: OAuth2 client library (likely authlib or python-jose)
- Configuration changes: Authentik OAuth2 provider details (issuer URL, client credentials)
- Test infrastructure needs authentication fixtures for integration tests
- Breaking change for any existing API consumers (marked as v1, pre-release acceptable)
