## Context

The API currently supports OAuth2-based authentication for protected endpoints but does not persist user records. Request processing is stateless with respect to account identity, which blocks profile management and future user-scoped features.

The system already runs in Docker and has an API container pattern in place. Adding persistence introduces data schema, environment configuration, and test setup concerns that cross module boundaries (authentication, routing, configuration, and bootstrap).

## Goals / Non-Goals

**Goals:**
- Add durable storage for application user records and profile attributes.
- Resolve OAuth-authenticated identities to a local user row on first successful auth and reuse it on subsequent requests.
- Provide authenticated profile read and update behavior for the current user.
- Keep local development and containerized execution straightforward with explicit DB configuration.

**Non-Goals:**
- Building a full user administration console or multi-user management endpoints.
- Replacing the current OAuth provider or token validation approach.
- Introducing authorization roles/permissions beyond authenticated self-access.

## Decisions

1. Use PostgreSQL as the primary persistence mechanism.
   - Rationale: relational consistency, mature ecosystem with FastAPI/Python tooling, and good fit for identity-keyed user records.
   - Alternatives considered:
     - SQLite: easy local setup but weaker concurrency/deployment fit for multi-instance production.
     - Document store: flexible schema but unnecessary for the current normalized user/profile domain.

2. Introduce a `users` table keyed by internal UUID, with a unique external OAuth subject key.
   - Rationale: stable internal identity plus deterministic mapping to OAuth claims (`iss` + `sub` or equivalent provider-scoped identity).
   - Alternatives considered:
     - Use external subject as primary key: leaks provider semantics into internal data model and complicates provider migrations.

3. Resolve-or-create user during authenticated request handling.
   - Rationale: avoids separate onboarding flows and guarantees protected endpoints have a local user context.
   - Alternatives considered:
     - Dedicated sign-up endpoint: adds client complexity and can drift from token-truth identity data.

4. Add `/v1/me` profile endpoints (`GET` and `PATCH`) for self-service profile operations.
   - Rationale: clear API contract for “current authenticated user,” minimizing identifier spoofing risk.
   - Alternatives considered:
     - `/users/{id}` self-managed endpoint: larger surface area and more authorization checks for little benefit.

5. Use migration-driven schema management and isolated DB config via environment variables.
   - Rationale: deterministic schema changes across local, CI, and containerized deployments.
   - Alternatives considered:
     - Ad hoc startup DDL: harder to audit and prone to drift.

## Risks / Trade-offs

- [Database lifecycle complexity in local/CI] -> Provide sane defaults in compose/task tooling and explicit health checks before API start.
- [OAuth claim variance across providers] -> Define a canonical identity mapping rule in spec and enforce validation with tests.
- [Write path coupling in authentication flow] -> Keep repository logic isolated and test auth resolution separately from route handlers.
- [Schema migration failures] -> Add rollback notes per migration and validate migrations in CI.

## Migration Plan

1. Add database service configuration and API connection settings.
2. Introduce initial migration for `users` profile schema and unique identity constraints.
3. Integrate user resolve-or-create behavior into authenticated request handling.
4. Implement `/v1/me` profile endpoints and response contracts.
5. Add unit/integration tests covering storage, identity mapping, and profile CRUD behavior.
6. Rollout strategy: deploy DB migration before enabling profile endpoints; keep rollback by reverting app image and applying backward-compatible down migration if required.

## Open Questions

- Which profile fields are mandatory at create-time vs optional mutable metadata?
- Should first-login user creation be synchronous on every protected request path, or cached per token lifetime with fallback writes?
- Do we need audit timestamps/history for profile updates in the initial release?