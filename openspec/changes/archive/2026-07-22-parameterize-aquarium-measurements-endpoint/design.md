## Context

The aquarium measurement capability currently supports multiple water parameters (including salinity and phosphate), but route semantics are inconsistent: clients rely on `/aquariums/{aquarium_id}/measurements` and legacy salinity-specific behavior for some flows. This inconsistency increases routing ambiguity, complicates client usage, and makes parameter-specific behavior harder to reason about as more parameters are added.

This change standardizes measurement create/list operations on a single path contract: `/aquariums/{aquarium_id}/measurements/{parameter}`. The path parameter becomes the canonical selector for which water parameter is being created or listed.

## Goals / Non-Goals

**Goals:**
- Make `GET` and `POST` measurement operations parameterized by route path segment `{parameter}`.
- Accept mixed-case aliases in `{parameter}` and normalize to lowercase before validation, authorization, and repository calls.
- Preserve existing ownership, authentication, validation, duplicate-prevention, and timestamp-normalization rules.
- Keep existing storage model and parameter-specific canonicalization behavior (for example, salinity canonical `ppt`, phosphate canonical `ppm`).
- Remove reliance on legacy salinity-specific endpoint handling and generic query-filter-driven route behavior for canonical reads/writes.
- Provide clear backward-incompatible contract definition in specs and implementation tasks.

**Non-Goals:**
- Introducing new measurement parameters or changing value/unit validation rules beyond route selection semantics.
- Changing repository schema, indexes, or migration strategy unless required by implementation cleanup.
- Adding pagination, aggregation, or reporting features.

## Decisions

### 1. Path parameter is the authoritative parameter selector
Use `/aquariums/{aquarium_id}/measurements/{parameter}` for both `POST` and `GET`, and treat `{parameter}` as authoritative for parameter selection.

Rationale:
- Unifies route semantics for creation and retrieval.
- Avoids ambiguity between path, payload, and query selectors.
- Scales cleanly as additional supported parameters are introduced.

Alternatives considered:
- Keep `/measurements` and rely on payload/query `parameter`: rejected due to ambiguous contract and inconsistent routing behavior.

### 2. Preserve existing domain rules; move only endpoint contract
Keep current ownership checks, per-parameter validation, canonical conversion, timestamp truncation, and duplicate constraints unchanged in behavior.

Rationale:
- Limits risk by narrowing the change to API contract/routing semantics.
- Maintains compatibility of persisted data and business invariants.

Alternatives considered:
- Reworking validation/repository behavior simultaneously: rejected to avoid unnecessary scope coupling.

### 3. Normalize path parameter aliases to lowercase before processing
Accept mixed-case path aliases (for example `Salinity`, `PHOSPHATE`) and normalize to lowercase before applying supported-parameter checks, authorization scoping logic, and repository operations.

Rationale:
- Improves client ergonomics and tolerance for case variation in integrations.
- Ensures consistent downstream parameter handling across validation and persistence paths.

Alternatives considered:
- Enforce strict lowercase path values only: rejected because it causes avoidable client errors without improving domain integrity.

### 4. Treat legacy salinity endpoint behavior as obsolete
Any legacy compatibility behavior that duplicates salinity handling outside the canonical parameterized route is removed or documented as deprecated/obsolete in this change.

Rationale:
- Prevents dual-contract drift and long-term maintenance burden.
- Forces convergence on one endpoint pattern.

Alternatives considered:
- Keep long-lived route aliases: rejected because they preserve ambiguity and test surface complexity.

## Risks / Trade-offs

- [Risk] Existing clients calling `/aquariums/{aquarium_id}/measurements` may break.
  → Mitigation: clearly mark the change as breaking in proposal/specs, update docs, and adjust tests to new contract.

- [Risk] Route conflicts or precedence issues with old salinity-specific handlers.
  → Mitigation: remove/disable obsolete handlers and verify route table behavior with endpoint tests.

- [Risk] Parameter normalization mismatches between path extraction and existing validation logic.
  → Mitigation: normalize path parameter consistently (trim/lowercase if applicable) before validation and add focused tests.

## Migration Plan

1. Update API routing for measurement `POST` and `GET` to `/aquariums/{aquarium_id}/measurements/{parameter}`.
2. Adapt request parsing so parameter source is path-based and no longer depends on generic query filter behavior for canonical list-by-parameter access.
3. Remove obsolete salinity-specific compatibility route behavior.
4. Update endpoint tests, authorization tests, and validation tests to the new path contract.
5. Update API docs/spec deltas and release notes to communicate the breaking change.

Rollback strategy:
- Revert route-contract commits and restore previous handlers if rollout issues occur.
- No data rollback is expected because persistence schema/shape is unchanged.

## Open Questions

- None.
