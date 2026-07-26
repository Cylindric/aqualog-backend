## Context

`Aquarium` (`src/models.py`) currently has no notion of "acceptable range" for a water parameter — only `AquariumMeasurement` records actual readings, keyed by an open-ended `parameter: str` column (`src/aquarium_measurements.py` currently recognizes `salinity` and `phosphate`; `temperature` is added as a third measurement parameter by this change). The proposal asks for `target`/`min`/`max` on three parameters today, with more parameters expected later (e.g. pH, alkalinity, nitrate), and explicitly asks us to weigh normalizing the schema now vs. later.

## Goals / Non-Goals

**Goals:**
- Let an owner store `target`/`min`/`max` for a parameter on their aquarium.
- Make adding a new thresholded parameter in the future a data change, not a schema migration.
- Reuse the existing router/repository/response-envelope/auth conventions rather than inventing new ones.
- Keep threshold values comparable to canonical measurement units for the same parameter (e.g. salinity thresholds in `ppt`, phosphate in `ppm`) so a UI can plot readings against thresholds directly.
- Bring `temperature` to full parity with `salinity`/`phosphate`: recordable as a measurement (with unit conversion, duplicate protection, history retrieval) in addition to having thresholds.

**Non-Goals:**
- Alerting/notifications when a measurement falls outside its threshold (future change; this change only stores and serves the thresholds).
- Frontend consumption of thresholds or temperature measurements.
- Per-species or template-based default thresholds (e.g. "reef tank defaults") — only explicit owner-set values in v1.

## Decisions

### 1. Normalize thresholds into their own table, keyed by `(aquarium_id, parameter)`

**Chosen**: a new `aquarium_parameter_thresholds` table:

| column | type | notes |
|---|---|---|
| `id` | `String(36)` PK | uuid4, app-generated, matches existing PK convention |
| `aquarium_id` | `String(36)` FK → `aquariums.id`, `ondelete=CASCADE` | indexed |
| `parameter` | `String(32)` | indexed; e.g. `temperature`, `salinity`, `phosphate` |
| `target` | `Float`, nullable | |
| `min` | `Float`, nullable | |
| `max` | `Float`, nullable | |
| `unit` | `String(16)` | canonical unit for the parameter, same canon as measurements (`ppt` for salinity, `ppm` for phosphate, `celsius` for temperature) |
| `created_at` / `updated_at` | `DateTime(timezone=True)` | existing convention |

Unique constraint on `(aquarium_id, parameter)` — one threshold row per parameter per aquarium, mirroring the `uq_aquarium_measurements_aquarium_parameter_measured_at` pattern already used for measurements.

**Why over wide columns** (`temperature_target`, `temperature_min`, `temperature_max`, `salinity_target`, ...): the proposal states more parameters are coming. Wide columns mean every new parameter is an Alembic migration touching `aquariums` (or a new all-parameters table with the same problem, just deferred), plus sparse/mostly-NULL columns for aquariums that don't track a given parameter, plus every read/write path needing to know all columns by name. A normalized table means adding `ph` or `alkalinity` next quarter is purely an application-level change (accept the new parameter name, no DDL). This mirrors the precedent already set by `AquariumMeasurement`, which made the same wide-vs-normalized call and chose normalized for the same reason (`parameter: str` column rather than per-parameter measurement tables/columns).

**Alternatives considered:**
- *Wide columns on `Aquarium`* (`temperature_target: float | None`, etc.): simplest reads (thresholds come back "for free" with the aquarium), but rejected — doesn't scale with parameter count, and is inconsistent with how measurements already solved this exact problem.
- *JSON/JSONB column* (`thresholds: dict` on `Aquarium`): avoids a new table, but loses type safety, DB-level constraints (uniqueness, per-column validation), and query/filter ability, and is inconsistent with the rest of the schema (no JSON columns used elsewhere in `src/models.py`). Rejected.
- *Separate table per parameter*: same migration-per-parameter problem as wide columns, just moved to table-creation instead of column-addition. Rejected.

### 2. New standalone resource + router, not fields on the `Aquarium` payload/endpoints

Thresholds get their own endpoints under `/aquariums/{aquarium_id}/thresholds/{parameter}` (`GET`, `PUT`) in a new `src/aquarium_parameter_thresholds.py`, following the exact shape of `src/aquarium_measurements.py` (parameterized path, `_normalize_parameter`, per-parameter validation, repository built from `Depends(get_session)`, `success_response` envelope). `PUT` (not `POST`) because a threshold is a singleton per `(aquarium, parameter)` — set-or-replace semantics, not an append-only log like measurements.

**Why not extend `CreateAquariumRequest`/`AquariumPayload`**: aquarium create/update already validates a fixed set of scalar fields (`name`, `type`, `volume`); folding a variable-length, per-parameter threshold list into that payload complicates its validation and couples the aquarium CRUD spec to the open-ended parameter set. Keeping thresholds as their own resource — like measurements already are — keeps `api-aquarium-management` requirements unchanged (see proposal: no modified capability) and is the smaller, additive change.

### 3. `temperature` is added to `aquarium_measurements.SUPPORTED_PARAMETERS`, matching thresholds exactly

`SUPPORTED_THRESHOLD_PARAMETERS = {"temperature", "salinity", "phosphate"}` (new module) and `aquarium_measurements.SUPPORTED_PARAMETERS` now both contain the same three values. `temperature` measurement recording follows the existing dual-unit pattern used by `salinity` (`ppt`/`sg` → canonical `ppt`), not the single-unit pattern used by `phosphate`: accepted units are `celsius` and `fahrenheit`, canonicalized to `celsius`. No `aquarium_measurements` schema change is required — `parameter`/`unit` are already free-text columns — only the application-level allow-list, conversion function, and sanity-range validation need updating.

### 4. Shared temperature unit constants/conversion live in one place, used by both modules

To avoid the two parameter lists (`measurements`, `thresholds`) drifting on unit names or sanity bounds now that they must agree exactly, temperature's canonical unit name (`celsius`), accepted-unit set, conversion function (`fahrenheit_to_celsius`), and sanity range (`MIN_TEMPERATURE_CELSIUS`/`MAX_TEMPERATURE_CELSIUS`, generously bounded e.g. 0–45 °C to cover chillers/heaters/quarantine setups) are defined once in `aquarium_measurements.py` (the existing home for the analogous `salinity`/`phosphate` constants) and imported by `aquarium_parameter_thresholds.py`, rather than introducing a new shared module for a single parameter. `salinity`'s `ppt`/`sg` and `phosphate`'s `ppm` bounds (`MAX_SALINITY_PPT`, `MIN_SALINITY_SG`, `MAX_SALINITY_SG`, `MAX_PHOSPHATE_PPM`) are reused the same way — imported, not duplicated, into the thresholds module.

### 5. Threshold validation: `min <= target <= max` when present, using the same per-parameter numeric conventions as measurements

Each field is optional; when two or more of `min`/`target`/`max` are provided, enforce `min <= target <= max`. Per-parameter sanity bounds reuse the constants from Decision 4 rather than redefining parallel ones.

### 6. Alembic revision IDs use the project's date-based naming convention, not the tool's default hash

**Requirement**: new Alembic revisions in this change SHALL use the same date-based naming convention as the preceding migrations in `alembic/versions/` — `YYYYMMDD_NNNNNN` (e.g. `20260716_000001`, `20260717_000001`, `20260719_000001`) — for both the filename and the `revision`/`down_revision` identifiers, rather than the hash-like ID `alembic revision --autogenerate` generates by default (e.g. `a4a75c38846a`). `NNNNNN` increments per same-day revision (`_000001`, `_000002`, ...) rather than resetting per migration name. This keeps revision history readable and chronologically sortable by filename, matching the existing migrations rather than mixing two ID schemes.

## Risks / Trade-offs

- [An extra join/query is needed to fetch thresholds alongside an aquarium] → Acceptable: thresholds are fetched per-parameter on demand (matching the measurement history pattern), not required on every aquarium list/get call.
- [Sharing constants between `aquarium_measurements.py` and `aquarium_parameter_thresholds.py` creates a one-directional import between two resource modules] → Acceptable: it's a handful of constants/pure functions, not a circular or heavyweight dependency; keeps the two parameter lists provably in sync instead of relying on convention.
- [Normalized table adds one more migration and one more repository/router to maintain vs. bolting fields onto `Aquarium`] → Accepted trade-off: matches existing measurement precedent and directly serves the stated future-parameter-growth requirement.

## Migration Plan

1. Add `temperature` support to `aquarium_measurements.py`: extend `SUPPORTED_PARAMETERS`, add unit constants/conversion, and add validation/canonicalization branches — no DB migration required (`parameter`/`unit` columns are already free-text).
2. Add `AquariumParameterThreshold` model + Alembic autogenerate migration (`task db-migration-new NAME="add_aquarium_parameter_thresholds"`), then rename the generated file and its `revision`/`down_revision` identifiers to the project's `YYYYMMDD_NNNNNN` convention (Decision 6) instead of leaving the tool-generated hash ID.
3. Add `AquariumParameterThresholdRepository`.
4. Add `build_aquarium_parameter_threshold_router()` and mount it in `src/app.py` alongside the other resource routers.
5. No backfill needed — table starts empty; absence of a row for a parameter simply means "no thresholds set," which routes should treat as a valid (empty/`null`) response rather than a 404.
6. Rollback: `alembic downgrade -1` drops the new table only; no existing table/column is touched, so rollback carries no data-loss risk to `aquariums`/`aquarium_measurements`.

## Open Questions

- Should unset thresholds return `200` with `null`/omitted fields, or `404`, for a parameter that has never had thresholds configured on that aquarium? (Design leans `200` + nulls, since the parameter is valid even if unconfigured — confirm during `tasks`/implementation.)
- Should `DELETE /aquariums/{aquarium_id}/thresholds/{parameter}` be included in v1, or is `PUT` with all-null fields sufficient to "clear" a threshold? (Leaning: no separate delete endpoint in v1 — `PUT` with nulls covers it — but open for reconsideration.)
