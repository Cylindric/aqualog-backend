## 1. Data Model and Migration

- [x] 1.1 Add an Alembic migration for aquarium water parameter measurements with foreign key to aquariums, canonical value/unit fields, raw entered value/unit fields, and indexes for aquarium/time queries.
- [x] 1.2 Add a uniqueness constraint/index preventing duplicate `salinity` readings for the same aquarium at the same normalized `measured_at` second.
- [x] 1.3 Add ORM/domain model updates to represent measurement records with `parameter`, canonical `ppt` `value`, canonical `ppt` `unit`, raw entered `raw_value`, raw entered `raw_unit`, and normalized `measured_at` fields.
- [x] 1.4 Ensure migration rollback path cleanly removes new measurement artifacts.

## 2. Repository and Validation

- [x] 2.1 Implement repository create operation for salinity measurement records scoped to a user-owned aquarium.
- [x] 2.2 Implement unit handling that accepts `ppt` and `sg` input, converts persisted canonical values to `ppt`, and preserves original entered value/unit in raw fields.
- [x] 2.3 Implement timestamp normalization that rounds down to whole-second resolution before persistence.
- [x] 2.4 Implement repository list operation returning chronological salinity measurement history with optional time range filtering and no pagination.
- [x] 2.5 Implement salinity payload validation rules for required fields, supported units (`ppt`, `sg`), numeric/range constraints, and normalized timestamp handling.

## 3. API Endpoints and Authorization

- [x] 3.1 Add authenticated endpoint to submit salinity measurements for an aquarium.
- [x] 3.2 Add authenticated endpoint to retrieve salinity measurement history for graphing.
- [x] 3.3 Enforce aquarium ownership checks on create/list operations and return consistent not-found/unauthorized behavior for cross-user access.
- [x] 3.4 Define request/response schemas that include graph-required fields and documented error responses.

## 4. Testing and Quality Gates

- [x] 4.1 Add/extend repository tests for successful persistence of canonical and raw fields, chronological ordering, time filter behavior, ownership scoping, and duplicate timestamp rejection.
- [x] 4.2 Add/extend API tests for successful measurement create/list behavior and response shape.
- [x] 4.3 Add/extend API validation and authorization tests for missing fields, invalid units/values, timestamp truncation behavior, duplicate timestamp rejection, and cross-user access.
- [x] 4.4 Run test suite and ensure new code paths meet project coverage expectations.
