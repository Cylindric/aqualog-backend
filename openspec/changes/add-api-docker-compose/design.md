## Context

The project now has a Dockerfile for building and running the API image, but startup still requires explicit docker commands. A compose file can provide a single, repeatable command for bringing up the API service with defaults, environment overrides, and local port mapping.

## Goals / Non-Goals

**Goals:**
- Add a `docker-compose.yml` file that can bring up the API server service.
- Reuse the existing Dockerfile image definition for compose startup.
- Define stable default environment values and allow overrides via compose runtime configuration.
- Keep compose scope minimal and focused on the API service bootstrap path.

**Non-Goals:**
- Introducing additional dependent services (database, cache, queue) in this change.
- Defining production orchestration artifacts (Kubernetes manifests, Helm charts).
- Replacing direct docker workflows for all use cases.

## Decisions

- Decision: Define a single API service in compose that builds from the local Dockerfile.
  - Rationale: Keeps startup simple and aligns compose behavior with the already-supported image build path.
  - Alternative considered: Referencing only a prebuilt remote image. Rejected because local bring-up should work from source.

- Decision: Map container port 8000 to a host port in compose.
  - Rationale: Provides predictable local access to API routes.
  - Alternative considered: Running without host port mapping. Rejected because it would make local testing harder.

- Decision: Provide compose-level environment defaults while allowing runtime override mechanisms.
  - Rationale: Improves out-of-the-box startup while retaining flexibility for alternate app environment values.
  - Alternative considered: Requiring all values from the caller. Rejected due to unnecessary startup friction.

- Decision: Keep compose startup aligned with module-based API entrypoint already chosen for the container image.
  - Rationale: Avoids divergence between direct container startup and compose startup behavior.
  - Alternative considered: Introducing compose-only startup command differences. Rejected because it would fragment runtime behavior.

- Decision: Compose defaults should prioritize `dev` for `AQUALOG_APP_ENV` in local workflows.
  - Rationale: the compose file in this repository will only be used for dev/test.

## Risks / Trade-offs

- [Risk] Compose defaults may drift from Dockerfile defaults over time.
  → Mitigation: Keep compose environment keys explicit and verify startup behavior in tests/docs.

- [Risk] Users may assume compose implies production readiness.
  → Mitigation: Keep scope documented as local/developer bootstrap.

- [Trade-off] Minimal single-service compose is easy to maintain but does not model full stack dependencies.
  → Mitigation: Extend in future changes only when additional services are needed.

## Migration Plan

- Add `docker-compose.yml` at repository root.
- Configure the API service to build from the project Dockerfile and expose API port mapping.
- Add compose environment configuration with overridable defaults.
- Validate compose startup path and API endpoint reachability.
- Roll back by removing compose file if needed.

## Open Questions

