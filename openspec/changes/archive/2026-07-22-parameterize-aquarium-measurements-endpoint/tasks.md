## 1. API Route Contract Refactor

- [x] 1.1 Update measurement `POST` route to `/aquariums/{aquarium_id}/measurements/{parameter}` in `src/aquarium_measurements.py`.
- [x] 1.2 Update measurement `GET` route to `/aquariums/{aquarium_id}/measurements/{parameter}` in `src/aquarium_measurements.py`.
- [x] 1.3 Ensure route handlers use the path `{parameter}` value as the authoritative parameter selector for create/list flows.
- [x] 1.4 Remove or disable obsolete legacy salinity-specific routing behavior that conflicts with or duplicates the canonical parameterized route.

## 2. Validation and Service Wiring

- [x] 2.1 Align request validation to parameterized routing so unsupported path parameters return validation errors.
- [x] 2.2 Accept mixed-case `{parameter}` aliases and normalize to lowercase before validation, authorization, and repository calls.
- [x] 2.3 Preserve existing ownership checks, timestamp normalization, duplicate prevention, and parameter-specific canonicalization behavior under the new route contract.
- [x] 2.4 Verify query behavior for retrieval remains time-window capable and returns only the selected path parameter history.

## 3. Tests and Regression Coverage

- [x] 3.1 Update API endpoint tests in `tests/test_aquarium_measurements.py` for new `GET`/`POST` path signatures.
- [x] 3.2 Add tests that unsupported `{parameter}` path values are rejected for both create and read operations.
- [x] 3.3 Add tests that mixed-case `{parameter}` aliases are accepted and normalized to lowercase before processing.
- [x] 3.4 Add/adjust tests ensuring legacy generic route behavior is no longer treated as canonical and obsolete salinity-specific compatibility handling is removed.
- [x] 3.5 Run targeted measurement test suites and ensure coverage expectations remain satisfied.

## 4. Documentation and Contract Updates

- [x] 4.1 Update API docs/spec references that still mention `/aquariums/{aquarium_id}/measurements` without `{parameter}`.
- [x] 4.2 Update developer notes/changelog entries to call out the breaking endpoint contract migration.
