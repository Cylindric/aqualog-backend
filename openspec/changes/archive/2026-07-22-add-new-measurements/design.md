## Context

The current aquarium measurement capability is implemented and specified around salinity. The API already enforces authenticated ownership checks, validation, timestamp normalization, duplicate prevention, and history retrieval for salinity data. The change extends that same workflow to additional parameters, starting with phosphate, while keeping existing API shape and user-scoped data access patterns.

## Goals / Non-Goals

**Goals:**
- Add support for recording and retrieving phosphate measurements for owned aquariums.
- Reuse the existing measurement ingestion and storage pipeline where possible.
- Define parameter-specific validation that is explicit and testable.
- Support phosphate entry using the consumer-friendly `ppm` unit only for this phase.
- Keep response formats graph-friendly and consistent with current measurement history output.
- Accept parameter names case-insensitively, trim surrounding whitespace, and normalize to lowercase before storing.
- Add simplified parameter filtering to measurement history retrieval: no filter returns all results, a single filter returns one parameter.

**Non-Goals:**
- Introducing pagination, analytics, or aggregation APIs for measurements.
- Backfilling historical phosphate data from external systems.
- Designing support for all possible parameter types in this change; this change establishes a repeatable pattern starting with phosphate.

## Decisions

1. Keep a single measurement endpoint and add parameter-aware validation.
- Rationale: avoids endpoint sprawl and preserves client integration patterns.
- Alternative considered: separate endpoint per parameter (e.g., `/salinity`, `/phosphate`), rejected due to duplicated auth and history logic.

2. Store and return phosphate in `ppm` units for this phase.
- Rationale: `ppm` is the common unit in consumer test devices and avoids unnecessary conversion friction.
- Alternative considered: canonical `mg/L` storage with conversion, rejected for now to keep UX and validation straightforward.

3. Preserve existing ownership, timestamp truncation, and duplicate constraints.
- Rationale: these are cross-parameter data integrity rules and should remain consistent.
- Alternative considered: parameter-specific duplicate behavior, rejected because it increases edge cases with little user value.

4. Expand history retrieval semantics to include phosphate records in chronological order with optional `parameter` filtering.
- Rationale: clients need efficient graph queries for selected parameters without extra endpoints.
- Alternative considered: multi-filter query syntax (lists/combinations), rejected because complex combinations can be handled client-side.

5. Normalize incoming parameter names by trimming surrounding whitespace and lowercasing before persistence and query matching.
- Rationale: supports user/device variation in formatting while keeping a stable canonical representation in storage.
- Alternative considered: strict formatting and case-sensitive matching, rejected due to avoidable validation failures and poorer UX.

## Risks / Trade-offs

- Parameter rule drift between API validation and persistence constraints -> Mitigation: centralize parameter validation rules and cover with request and repository tests.
- Future parameter additions may create branching complexity -> Mitigation: represent per-parameter constraints declaratively (allowed units, ranges, canonical unit).
- Existing clients may assume salinity-only payloads -> Mitigation: preserve existing salinity fields and add backward-compatible parameter handling with explicit tests.

## Migration Plan

- Add/adjust schema fields only if needed for parameter-safe constraints and indexing.
- Deploy API with phosphate support enabled by default.
- No data migration required for existing salinity rows.
- Rollback strategy: revert API code and any additive migration; existing salinity behavior remains intact.

## Open Questions

- None for this phase; future needs will be addressed in future changes.
