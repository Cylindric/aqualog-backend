## Why

Supported water parameters (salinity, phosphate, temperature, calcium, ammonia, nitrite, nitrate, ph, alkalinity, magnesium) are currently hardcoded as a Python `frozenset`/dict (`PARAMETER_RULES` in `src/aquarium_measurements.py`) and referenced only as a bare `String(32)` column on `aquarium_measurements` and `aquarium_parameter_thresholds`. There is no database-level record of what parameters exist, no way to see the full catalog via the API, and no display name or description a client can show without hardcoding its own copy of the list. Adding, renaming, or documenting a parameter currently requires a code change and redeploy rather than a data change.

## What Changes

- Add a new `parameters` table: `slug` (unique natural key, e.g. `salinity`), `display_name`, `description`.
- Seed the table via migration with the 10 parameters currently hardcoded in `PARAMETER_RULES`.
- Add `build_parameter_router()` exposing CRUD endpoints for the catalog: list, get, create, update, delete, following the existing router-factory/repository/response-envelope conventions.
- Change `aquarium_measurements.parameter` and `aquarium_parameter_thresholds.parameter` from free-standing strings to foreign keys against `parameters.slug`, enforced at the DB level (`ON DELETE RESTRICT`, so a parameter can't be deleted while measurements/thresholds reference it).
- Replace the in-code `SUPPORTED_PARAMETERS` / `SUPPORTED_THRESHOLD_PARAMETERS` membership checks with a lookup against the `parameters` table (via a `ParameterRepository`), so an unknown parameter slug in a measurement/threshold request is rejected because it doesn't exist in the table, not because it's missing from a hardcoded set.
- **BREAKING**: `aquarium_measurements` and `aquarium_parameter_thresholds` gain a real FK constraint on `parameter` — any pre-existing row with a parameter value outside the seeded catalog would fail migration and must be cleaned up first (not expected to occur in current data, since the seeded set matches today's hardcoded set exactly).

Out of scope: the per-parameter unit/range validation logic in `PARAMETER_RULES` (`SUPPORTED_*_UNITS`, min/max sanity ranges, canonicalization functions) stays in code as-is — only the existence/identity of a parameter (slug, display name, description) moves into the database. Unifying validation rules into the catalog table is a separate future change.

## Capabilities

### New Capabilities
- `api-parameter-catalog`: a `parameters` table and CRUD API (`/api/v1/parameters`) for the catalog of supported measurement parameters (slug, display name, description).

### Modified Capabilities
- `api-aquarium-water-parameter-measurements`: `parameter` on a measurement must reference an existing entry in the parameter catalog (FK) instead of an in-code hardcoded set.
- `api-aquarium-parameter-thresholds`: `parameter` on a threshold must reference an existing entry in the parameter catalog (FK) instead of an in-code hardcoded set.

## Impact

- `src/models.py`: new `Parameter` model; `AquariumMeasurement.parameter` and `AquariumParameterThreshold.parameter` gain `ForeignKey("parameters.slug")`.
- New `src/parameter_repository.py` and `src/parameters.py` (router), registered in `src/app.py`.
- `src/aquarium_measurements.py` / `src/aquarium_parameter_thresholds.py`: parameter-membership validation switches from the hardcoded `SUPPORTED_PARAMETERS` set to a DB lookup via `ParameterRepository`.
- New Alembic migration: create `parameters` table, seed the 10 existing parameters, add FK constraints (with a data-backfill-safe approach) to `aquarium_measurements.parameter` and `aquarium_parameter_thresholds.parameter`.
- Tests: new `tests/test_parameter_repository.py` / `tests/test_parameters.py`; existing measurement/threshold repository and router tests updated wherever they assumed an unconstrained string column.
