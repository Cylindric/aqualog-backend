## Why

Aquarium owners currently only record raw parameter measurements (salinity, phosphate) with no way to say what a "good" reading looks like for their tank. Without stored target/min/max thresholds, the frontend cannot flag out-of-range readings or plot acceptable bands on graphs, and every consumer would have to hardcode aquarium-keeping guidance. This change adds owner-configurable thresholds for temperature, salinity, and phosphate, and settles the schema shape (wide columns vs. a normalized table) before more parameter types are added.

## What Changes

- Add a new authenticated resource for per-aquarium, per-parameter thresholds: `target`, `min`, and `max` values for `temperature`, `salinity`, and `phosphate`.
- Persist thresholds in a normalized table keyed by `(aquarium_id, parameter)` rather than adding three columns per parameter to the `aquariums` table — new parameters become new rows, not new migrations.
- Expose authenticated `GET`/`PUT` operations to read and set thresholds for a given aquarium and parameter, scoped to the owning user, following the same `{aquarium_id}/.../{parameter}` path convention used by measurements.
- Validate that `min <= target <= max` when all three are provided, and enforce the same per-parameter unit/value constraints already used for measurements (e.g. salinity `ppt`/`sg` ranges, phosphate `ppm` range) so thresholds stay comparable to recorded readings.
- All three fields (`target`, `min`, `max`) are individually optional — an owner can set only the ones they care about.
- **`temperature` becomes a fully supported measurement parameter**, matching the capabilities `salinity` and `phosphate` already have: recording readings, unit validation/conversion to a canonical unit, duplicate-timestamp protection, and history retrieval at `/aquariums/{aquarium_id}/measurements/temperature`. This closes the gap so `temperature` has identical measurement *and* threshold support to the other two parameters, rather than thresholds-only.

## Capabilities

### New Capabilities
- `api-aquarium-parameter-thresholds`: authenticated CRUD-style API for reading and setting per-aquarium target/min/max thresholds per parameter, ownership-scoped, with parameter/unit validation consistent with the measurements capability.

### Modified Capabilities
- `api-aquarium-water-parameter-measurements`: add `temperature` as a third supported measurement parameter alongside `salinity` and `phosphate`, with its own accepted units (`celsius`, `fahrenheit`), conversion to a canonical `celsius` value, and the same validation/duplicate/history-retrieval behavior already specified for the existing parameters.

## Impact

- **DB**: new `aquarium_parameter_thresholds` table + Alembic migration. No schema change is needed for `aquarium_measurements` — its `parameter` column is already an open-ended string, so adding `temperature` as a measurement parameter is a pure application-level change (this also reinforces the normalized-schema choice made for thresholds).
- **API**: new router/endpoints (e.g. `src/aquarium_parameter_thresholds.py`) mounted alongside the existing aquarium and measurement routers under `/api/{version}/aquariums/{aquarium_id}/thresholds/{parameter}`; `src/aquarium_measurements.py` gains `temperature` support (`/api/{version}/aquariums/{aquarium_id}/measurements/temperature`).
- **Repository layer**: new `AquariumParameterThresholdRepository`, following the existing repository pattern (constructed from an injected `Session`, translates `IntegrityError` into domain errors). No changes needed to `AquariumMeasurementRepository` — it is already parameter-agnostic.
- **Tests**: new repository-level and router-level test modules for thresholds, following the existing `test_aquarium_repository.py` / `test_aquariums.py` split; new temperature test cases added to the existing measurement test modules.
- No frontend changes are in scope for this change (backend-only); the frontend consuming these thresholds and temperature measurements is a follow-up.
