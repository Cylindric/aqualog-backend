## Context

The service already exposes versioned API routes with standardized response envelopes and health checks. Salinity dosing logic is currently not represented as a dedicated API capability, so clients must calculate this independently. This change introduces a server-side endpoint that receives `volume`, `current`, and `target`, then computes a deterministic salt-addition quantity.

## Goals / Non-Goals

**Goals:**
- Add a stable API contract for salinity dose calculation at `/calculate/dose/salinity`.
- Keep calculation logic centralized in the backend using the provided formula `(target - current) * 1.1 * volume`.
- Ensure request validation and response formatting remain consistent with existing API conventions.
- Add tests for happy path and invalid-input behavior.

**Non-Goals:**
- Persisting calculation requests or responses.
- Introducing unit conversion across measurement systems.
- Adding broader chemistry calculators in this change.

## Decisions

- Decision: Implement as a dedicated HTTP endpoint rather than client-side guidance only.
  - Rationale: Prevents drift across clients and gives a single source of truth for dosing behavior.
  - Alternative considered: Documenting formula only and leaving execution to clients. Rejected due to inconsistency risk.

- Decision: Accept explicit input fields `volume`, `current`, and `target` as request parameters.
  - Rationale: Matches user-facing calculation requirements and keeps API contract simple.
  - Alternative considered: Accepting nested or domain-specific field groups. Rejected to avoid unnecessary payload complexity.

- Decision: Return the computed salt quantity in the standard success envelope.
  - Rationale: Maintains compatibility with response conventions and existing client parsing patterns.
  - Alternative considered: Returning a raw numeric body. Rejected to preserve uniform API response structure.

- Decision: Apply existing validation/error envelope behavior for malformed or missing parameters.
  - Rationale: Keeps error handling predictable and aligned with current API requirements.
  - Alternative considered: Endpoint-specific ad hoc error format. Rejected for inconsistency.

- Decision: Negative computed values should not be rejected with a validation error.

- Decision: Response payload should include echoed inputs for traceability.

## Risks / Trade-offs

- [Risk] Negative result values when `target < current` may be semantically unclear for clients.
  → Mitigation: Document endpoint semantics in spec scenarios and preserve deterministic formula output.

- [Risk] Numeric precision differences across clients may cause expectation mismatches.
  → Mitigation: Define response as numeric result from backend calculation; validate with tests using representative decimal inputs.

- [Trade-off] Keeping formula logic fixed in API simplifies clients but requires backend updates for future domain tuning.
  → Mitigation: Encapsulate computation in one handler/service path so future adjustments are localized.

## Migration Plan

- Add endpoint route and handler in the existing API module.
- Add request validation and standardized response wiring.
- Add tests for successful computation and validation failures.
- Deploy as backward-compatible additive API change.
- Rollback strategy: remove route registration if needed; no data migration required.

## Open Questions
