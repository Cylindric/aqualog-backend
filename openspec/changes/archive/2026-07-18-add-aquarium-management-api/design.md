## Context

The API currently supports authentication and user profile persistence but has no first-class aquarium resource. We need a user-scoped aquarium domain model and endpoints that enforce ownership boundaries by default. The platform stack is FastAPI with PostgreSQL and existing OAuth-authenticated request context carrying a resolved local user.

## Goals / Non-Goals

**Goals:**
- Add an authenticated aquarium management API category for create, list/read, update, and delete operations.
- Persist aquariums in PostgreSQL with a strict association to one owning user.
- Enforce authorization so users can only view and mutate their own aquariums.
- Support initial aquarium fields: name, type, and volume with validation.
- Provide deterministic API responses and tests for ownership and validation behavior.

**Non-Goals:**
- Multi-user/shared aquarium access or role-based collaboration.
- Advanced aquarium metadata (equipment, livestock, chemistry history).
- Bulk import/export workflows.
- Soft delete, audit trails, or event sourcing in this revision.

## Decisions

- Introduce a new persisted `aquariums` table keyed by UUID and linked to `users.id` via non-null foreign key.
Rationale: aligns with existing user persistence model and enforces ownership at the data layer.
Alternatives considered: storing aquariums as JSON in user profile (rejected due to poor queryability and update concurrency concerns).

- Enforce aquarium name uniqueness per owner using a database unique constraint on `(owner_user_id, name)`.
Rationale: guarantees per-user uniqueness under concurrent writes and keeps integrity checks close to storage.
Alternatives considered: application-only duplicate checks (rejected because race conditions can bypass app-level checks).

- Expose authenticated endpoints under a dedicated `/v1/aquariums` category.
Rationale: clear REST grouping and future extensibility.
Alternatives considered: embedding aquarium CRUD into `/v1/me` (rejected because resource boundaries become unclear).

- Scope all read/write/delete queries by `owner_user_id` from authenticated user context.
Rationale: prevents cross-user access even if aquarium IDs are guessed.
Alternatives considered: post-query authorization checks (rejected because pre-scoped queries are safer and simpler).

- Validate aquarium fields server-side:
  - `name`: required non-empty string (bounded length)
  - `type`: required open string category, trimmed, length 3..24 after trimming
  - `volume`: required positive numeric value with explicit unit metadata; supported units in v1 are `L` and `gal_us`, and values are converted and stored internally in liters
Rationale: ensures consistent persisted data and predictable API behavior.
Alternatives considered: permissive schema with weak validation (rejected for data quality reasons).

- Use hard delete for this iteration.
Rationale: simpler semantics for first release and matches requested behavior.
Alternatives considered: soft delete with tombstones (deferred).

## Risks / Trade-offs

- Ownership bypass risk if any query path forgets user scoping -> Mitigation: centralize repository methods requiring `owner_user_id`; add negative authorization tests.
- Validation ambiguity for `type` and `volume` units -> Mitigation: define accepted type values and volume unit contract in API schema/tests.
- Unit conversion accuracy risk when clients submit non-liter values -> Mitigation: require explicit unit metadata, use deterministic conversion constants, and add conversion-focused tests.
- Duplicate name conflict risk under concurrent writes -> Mitigation: enforce `(owner_user_id, name)` unique constraint and map conflicts to deterministic validation/error responses.
- Migration risk introducing new foreign-keyed table -> Mitigation: additive migration with explicit indexes and rollback script.
- Hard delete may remove data users later want restored -> Mitigation: document behavior now; evaluate soft delete in a follow-up change.

## Migration Plan

- Add migration creating `aquariums` table with owner FK to `users`, timestamps, and indexes (`owner_user_id`) plus a required unique constraint on `(owner_user_id, name)`.
- Deploy migration before API rollout.
- Release endpoints behind normal versioned API path.
- Rollback: remove endpoint routing and deploy reverse migration if rollback is required.

## Open Questions

- None.
