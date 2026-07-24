## Context

The service currently supports authenticated user profiles, aquarium ownership, and aquarium CRUD operations. It does not yet persist historical water parameter measurements, which prevents trend tracking and graphing workflows in clients.

This change introduces the first water parameter tracking path for salinity. The implementation must preserve existing ownership boundaries so users can only create and read measurements for their own aquariums. The data model and API shape should be extensible so future parameters (for example temperature, nitrate, or pH) can be added without reworking the persistence and query pattern.

## Goals / Non-Goals

**Goals:**
- Add an authenticated way to record salinity measurements against a user-owned aquarium.
- Add an authenticated way to retrieve salinity measurement history in chronological order for graphing.
- Persist measurement records with stable graph-required fields (`parameter`, `value`, `unit`, `measured_at`) and ownership-safe association.
- Validate input (required fields, type/range, unit) before persistence.
- Keep the schema and repository approach extensible to additional water parameters.

**Non-Goals:**
- Building frontend graph rendering or chart styling.
- Supporting parameters other than salinity in this first version.
- Providing aggregate analytics (rolling averages, anomaly detection) beyond raw historical series retrieval.
- Bulk import/export of measurements.

## Decisions

### 1. Add a dedicated measurement persistence model linked to aquariums
Use a dedicated database table/model for water parameter measurements with a foreign key to aquariums rather than embedding measurements inside aquarium records.

Rationale:
- Supports unbounded time-series growth without inflating aquarium row payloads.
- Enables indexed queries by aquarium and time range.
- Makes it straightforward to add additional parameter types later.

Alternatives considered:
- JSON array column on aquariums: rejected due to poor queryability and update contention.
- One table per parameter: rejected as unnecessarily rigid and harder to scale across many parameters.

### 2. Parameter-first schema with explicit salinity unit handling in v1
Persist a `parameter` field (value `salinity` for v1) along with canonical fields `value`, `unit`, and `measured_at`, plus additional raw-input fields `raw_value` and `raw_unit`. The API accepts salinity input units `ppt` and `sg`, converts accepted values to `ppt`, stores canonical normalized values with storage unit `ppt`, and also stores the original entered value/unit for auditability and future conversion refinements.

Rationale:
- Keeps the storage model future-proof while delivering a focused v1 scope.
- Avoids migration churn when introducing more parameters.
- Ensures a single canonical storage unit for graphing and analytics.
- Preserves user-entered source data to support future reprocessing and cross-system conversion improvements.

Alternatives considered:
- Hard-code salinity-only table/columns: rejected because it introduces avoidable refactor debt.

### 3. Reuse ownership enforcement patterns from aquarium APIs
Measurement create/list paths will resolve the aquarium in user scope before write/read operations. Cross-user resource access returns not-found/unauthorized behavior consistent with existing aquarium endpoints.

Rationale:
- Preserves security posture and user data isolation.
- Aligns with existing API conventions and test expectations.

Alternatives considered:
- Post-query filtering after unrestricted lookups: rejected due to security risk and unnecessary data access.

### 4. Return chronological measurement series with optional bounded filters and no pagination in v1
History responses will be sorted by `measured_at` ascending and support optional range filtering (`from`/`to`) to reduce payload size and support graph windows. Server pagination is explicitly out of scope for this change and may be introduced later.

Rationale:
- Ascending order is graph-ready for plotting on time axes.
- Range filters reduce transfer and processing for long histories.

Alternatives considered:
- Descending default order: rejected because clients would need to reorder for plotting.
- No time filtering: rejected due to scalability concerns for long-running aquariums.
- Add pagination now: rejected to keep first delivery focused on core capture/history behavior.

### 5. Enforce per-second timestamp normalization and uniqueness
The system will normalize `measured_at` by truncating to whole-second resolution (round down to the nearest second) before persistence, and enforce uniqueness for each aquarium/parameter/timestamp tuple.

Rationale:
- Prevents accidental duplicate readings at the same logical sample moment.
- Avoids inconsistencies from sub-second client timestamp precision differences.

Alternatives considered:
- Keep sub-second precision: rejected due to duplicate risks and inconsistent client precision.
- Allow duplicates at same timestamp: rejected because it complicates graph interpretation and data quality.

## Risks / Trade-offs

- [Risk] Unit conventions for salinity may vary (for example ppt vs sg) and can cause client/server mismatch.
  → Mitigation: Define supported v1 unit set explicitly in request validation and API docs; reject unsupported units with clear validation errors.

- [Risk] Unbounded history growth can increase query cost over time.
  → Mitigation: Add indexes on `(aquarium_id, measured_at)` and default query constraints via optional filters.

- [Risk] Future parameters may require parameter-specific validation ranges.
  → Mitigation: Centralize validation logic by parameter key so new parameter rules can be added without endpoint redesign.

- [Risk] Timestamp ambiguity (time zones, client-local times) can create graph inconsistencies.
  → Mitigation: Require ISO 8601 timestamps and normalize storage to UTC.

- [Risk] Conversion from `sg` to `ppt` could introduce rounding differences.
  → Mitigation: Define and test a deterministic conversion/rounding rule, document response precision, and retain `raw_value`/`raw_unit` for traceability.

## Migration Plan

1. Add Alembic migration creating measurement table with canonical and raw-input value/unit fields, plus indexes.
2. Add ORM/domain models and repository methods for create/list within owner scope and dual-value persistence.
3. Add API routes and request/response schemas for salinity measurement create/list with `ppt`/`sg` input and canonical `ppt` storage/output.
4. Add validation and authorization checks consistent with existing aquarium conventions.
5. Add/extend tests for migration behavior, repository queries, timestamp truncation/uniqueness, API success paths, and validation/authorization failures.
6. Deploy with backward-compatible additive changes only (no existing endpoint contract breaks).

Rollback strategy:
- Revert API/repository code changes and roll back to prior release.
- If migration rollback is required, remove dependent application usage first, then apply down migration in controlled maintenance window.

## Open Questions

- None at this stage.
