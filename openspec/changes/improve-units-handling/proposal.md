## Why

Units of measurement (`ppt`, `celsius`, `ppm`, `pH`, etc.) currently exist only as hardcoded Python frozensets and per-parameter `ParameterRule` conversion logic in `src/aquarium_measurements.py`. Unlike parameters (already a DB-backed catalog since `parameter-catalog`), units cannot be listed, validated, or managed via the database or API — every new unit requires a code change. Storing `unit`/`raw_unit` as raw strings on `aquarium_measurements` also allows any string through at the DB layer, with validity enforced only in application code.

## What Changes

- Add a `units` table: `id` (UUID PK), `slug` (unique, e.g. `L`, `ppt`, `pH`), `display_name`, `description`, timestamps — mirroring the existing `Parameter` catalog shape.
- Add a `parameter_units` many-to-many join table linking `parameters` to `units`, marking which units are valid for each parameter (e.g. salinity → `ppt`, `sg`), including a flag for each parameter's canonical (stored) unit.
- **BREAKING**: Replace `aquarium_measurements.unit` (string) with `unit_id` (FK to `units.id`).
- **BREAKING**: Replace `aquarium_measurements.raw_unit` (string) with `raw_unit_id` (FK to `units.id`).
- Add a `units` CRUD API (list/get/create/update/delete by `slug`), following the same router/repository factory pattern as `src/parameters.py`.
- Unit validation for measurement create/list requests now checks the `parameter_units` join table (parameter ↔ allowed units) instead of the hardcoded `SUPPORTED_*_UNITS` frozensets.
- API request/response bodies continue to accept and return unit `slug` strings (e.g. `"ppt"`), never raw UUIDs — no client-facing contract change for existing measurement endpoints.
- Existing per-parameter conversion functions (`_to_ppt`, `_to_celsius`, etc.) and canonicalization behavior are preserved as-is, now looked up/validated against the DB catalog rather than Python constants.
- Data migration backfills `units` and `parameter_units` from the current hardcoded constants, then backfills `unit_id`/`raw_unit_id` on existing `aquarium_measurements` rows before dropping the old string columns.
- Out of scope: `aquarium_parameter_thresholds.unit` keeps its current string column for now (same shape/problem, left as a candidate follow-up change to avoid growing this change's blast radius).

## Capabilities

### New Capabilities
- `api-unit-catalog`: CRUD API for managing the unit catalog (`slug`, `display_name`, `description`) and the parameter↔unit many-to-many associations (including canonical-unit designation per parameter).

### Modified Capabilities
- `api-aquarium-water-parameter-measurements`: unit validation for measurement create/list now sources valid units from the `parameter_units` catalog relationship instead of hardcoded per-parameter unit sets; stored `unit`/`raw_unit` become catalog-backed while API request/response shape (slug strings) is unchanged.

## Impact

- **Models**: `src/models.py` — new `Unit`, `ParameterUnit` (or association table) models; `AquariumMeasurement.unit`/`raw_unit` become `unit_id`/`raw_unit_id` FK columns.
- **New modules**: `src/units.py` (router), `src/unit_repository.py` (repository), following `src/parameters.py`/`src/parameter_repository.py` shape.
- **Modified**: `src/aquarium_measurements.py` (`_validate_measurement_payload`, `_canonicalize_measurement`, `PARAMETER_RULES` lookups now cross-check the DB catalog), `src/aquarium_measurement_repository.py` (`create_measurement`/`list_measurements`/`_to_payload` signatures move from `unit: str` to `unit_id: UUID` with slug resolution at the boundary).
- **DB**: new Alembic migrations for `units`, `parameter_units` tables + seed data, and the `unit`/`raw_unit` → `unit_id`/`raw_unit_id` column swap on `aquarium_measurements` (same backfill-then-cutover pattern as `20260731_000002_parameter_fk_to_id.py`).
- **Tests**: `src/db.py` test-seeding (`_seed_parameters`-equivalent for units/parameter_units) plus updated fixtures across `tests/test_aquarium_measurements.py`, `tests/test_aquarium_measurement_repository.py`.
- **API**: new `/api/v1/units` endpoints; existing `/api/v1/aquariums/{id}/measurements/...` endpoints unchanged in request/response shape.
