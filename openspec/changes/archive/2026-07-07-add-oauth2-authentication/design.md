## Context

The API currently has no authentication mechanism. The infrastructure already includes Authentik (an OAuth2/OIDC provider) in docker-compose-authentik.yml. This design integrates OAuth2 authentication into the FastAPI application to protect endpoints while maintaining operational accessibility for health monitoring.

Current state:
- FastAPI application with versioned routing (`/api/v1/*`)
- Health endpoints at `/api/v1/health/live` and `/api/v1/health/ready`
- Calculation endpoints (e.g., `/api/v1/calculate/dose/salinity`)
- Authentik already available in the docker-compose stack

## Goals / Non-Goals

**Goals:**
- Integrate OAuth2/OIDC authentication with Authentik
- Protect all business logic endpoints (calculations, future data endpoints)
- Keep health/liveness endpoints unauthenticated for monitoring
- Validate JWT tokens on protected endpoints
- Provide clear 401 responses for unauthenticated requests

**Non-Goals:**
- Role-based authorization (RBAC) - future enhancement
- API key authentication - OAuth2 only for now
- Custom authentication UI - leverage Authentik's hosted pages
- Rate limiting - separate concern

## Decisions

### Decision 1: Use FastAPI's built-in OAuth2 support with authlib for token validation

**Rationale:** FastAPI provides OAuth2 security schemes out of the box. We'll use `authlib` for JWT validation because it has robust OIDC support, handles JWKS key rotation, and integrates well with FastAPI's dependency injection.

**Alternatives considered:**
- `python-jose` - less actively maintained, requires manual JWKS handling
- `PyJWT` - lower level, would require more custom code for OIDC discovery
- `requests-oauthlib` - focused on client flows, not ideal for token validation

### Decision 2: Token validation via OIDC discovery with caching

**Rationale:** Use Authentik's OIDC discovery endpoint (`/.well-known/openid-configuration`) to fetch issuer metadata and JWKS keys. Cache the validation keys with a TTL to minimize external calls while supporting key rotation.

**Alternatives considered:**
- Hardcoded JWKS - brittle, fails on key rotation
- No caching - poor performance, unnecessary external calls

### Decision 3: Apply authentication as an optional dependency, explicitly require on protected routes

**Rationale:** Define an OAuth2 dependency that can be applied selectively. Health endpoints don't use it; calculation endpoints explicitly require it. This makes authentication visible in route definitions and supports future public endpoints.

**Alternatives considered:**
- Global middleware - harder to exempt health endpoints, less explicit
- Decorator pattern - not idiomatic in FastAPI, loses OpenAPI integration

### Decision 4: Configuration via environment variables

**Rationale:** Add Authentik OAuth2 config to existing environment-based configuration system (pydantic-settings). Required: issuer URL, audience/client ID. Client secret not needed for public token validation.

**Configuration:**
- `AQUALOG_OAUTH_ISSUER_URL` - Authentik issuer (e.g., `https://auth.example.com/application/o/aqualog/`)
- `AQUALOG_OAUTH_AUDIENCE` - Expected audience claim (client ID)

## Risks / Trade-offs

**[Risk] Authentik unavailable → API cannot validate tokens**  
→ Mitigation: Health endpoints remain accessible. Consider adding token validation result caching with short TTL for resilience.

**[Risk] JWT validation adds latency to every request**  
→ Mitigation: Cache JWKS keys. Token signature validation is fast (<5ms). Consider adding request-scoped token validation cache for repeat validations within a request lifecycle.

**[Risk] Breaking change for existing API consumers**  
→ Mitigation: Acceptable during v1 pre-release. Document in changelog. Health endpoints remain accessible for monitoring.

**[Trade-off] No refresh token handling**  
→ Accept: Clients handle token refresh via OAuth2 flow. API only validates access tokens. Standard OAuth2 pattern.

**[Trade-off] No user context extraction yet**  
→ Accept: Initial implementation validates tokens only. User claims extraction (sub, email) is a future enhancement when we need user-scoped data.
