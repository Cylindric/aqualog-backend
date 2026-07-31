## 1. Data model

- [ ] 1.1 Add `Unit` model to `src/models.py`: `id` (`Uuid()` PK), `slug` (`String(16)`, unique, not-null, indexed, case preserved as submitted), `display_name` (not-null), `description` (nullable), `created_at`, `updated_at`.
- [ ] 1.2 Add a functional/case-insensitive unique index on `Unit.slug` (e.g. `Index(..., func.lower(Unit.slug), unique=True)`) so `pH`/`Ph`/`ph` collide as duplicates.
- [ ] 1.3 Add `ParameterUnit` association model/table `parameter_units`: `parameter_id` (FK → `parameters.id`, `ondelete="CASCADE"`), `unit_id` (FK → `units.id`, `ondelete="RESTRICT"`), `is_canonical` (bool, not-null, default `False`), composite PK `(parameter_id, unit_id)`.
- [ ] 1.4 Add a partial unique index on `parameter_units.parameter_id WHERE is_canonical` so each parameter has at most one canonical unit.
- [ ] 1.5 Change `AquariumMeasurement.unit`/`raw_unit` in `src/models.py` from `String(16)` to `unit_id`/`raw_unit_id` (`Uuid()`, `ForeignKey("units.id", ondelete="RESTRICT")`, not-null).

## 2. Migration

- [ ] 2.1 Generate Alembic migration (`task db-migration-new NAME="add_unit_catalog"`) creating the `units` and `parameter_units` tables.
- [ ] 2.2 In the migration, bulk-insert the unit catalog: `ppt`, `sg`, `celsius`, `fahrenheit`, `ppm`, `mg/L`, `pH`, `dKH` (measurement units, exact current casing from `PARAMETER_RULES`/`_to_payload` in `src/aquarium_measurements.py`), plus `L`, `gal_us` (aquarium volume units from `SUPPORTED_VOLUME_UNITS` in `src/aquariums.py`, unattached to any parameter).
- [ ] 2.3 In the migration, bulk-insert `parameter_units` rows matching each parameter's current `SUPPORTED_*_UNITS`/canonical unit from `PARAMETER_RULES` (e.g. salinity → `ppt` canonical + `sg`; temperature → `celsius` canonical + `fahrenheit`; phosphate/calcium/nitrite/nitrate/magnesium → `ppm` canonical; ammonia → `mg/L` canonical; ph → `pH` canonical; alkalinity → `dKH` canonical).
- [ ] 2.4 Generate a second Alembic migration (`task db-migration-new NAME="aquarium_measurements_unit_fk"`) that: adds nullable `unit_id`/`raw_unit_id` columns to `aquarium_measurements`; backfills them via `UPDATE ... FROM units WHERE units.slug = aquarium_measurements.unit` (and `raw_unit`); sets both `NOT NULL`; adds the FK constraints and indexes; drops the old `unit`/`raw_unit` string columns.
- [ ] 2.5 Write `downgrade()` for both migrations, reversing column/table creation and re-deriving string columns from the FK'd unit slugs where applicable.
- [ ] 2.6 Run `task db-migrate` locally and confirm both migrations apply cleanly against an existing dev database with pre-existing measurement rows.

## 3. Repository layer

- [ ] 3.1 Create `src/unit_repository.py` with `UnitRepository`: `list_all()`, `get_by_slug(slug)` (case-insensitive), `create(slug, display_name, description)`, `update_by_slug(slug, updates)`, `delete_by_slug(slug)`.
- [ ] 3.2 Raise a `DuplicateUnitSlugError` on unique-constraint violation during create (case-insensitive collision), translated from `IntegrityError`.
- [ ] 3.3 Raise a `UnitInUseError` when `delete_by_slug` hits a FK-violation `IntegrityError` (referenced by a measurement or a `parameter_units` row).
- [ ] 3.4 Add `list_units_for_parameter(parameter_id)` and `get_canonical_unit(parameter_id)` helpers (or equivalent query methods) on `UnitRepository` or a small `ParameterUnitRepository`, backing the new catalog-driven validation in `src/aquarium_measurements.py`.
- [ ] 3.5 Update `AquariumMeasurementRepository.create_measurement`/`list_measurements`/`_to_payload` (`src/aquarium_measurement_repository.py`) to use `unit_id: uuid.UUID`/`raw_unit_id: uuid.UUID` instead of `unit: str`/`raw_unit: str`; resolve slug↔id at the router boundary, not in this repository.

## 4. API router

- [ ] 4.1 Create `src/units.py` with `build_unit_router()` exposing `GET /units`, `GET /units/{slug}`, `POST /units`, `PATCH /units/{slug}`, `DELETE /units/{slug}`, all behind `get_current_user`, all responses via `success_response`/`error_response`.
- [ ] 4.2 Add request/response Pydantic models (`CreateUnitRequest`, `UpdateUnitRequest`, `UnitPayload`, list/detail response wrappers). Trim whitespace on `slug`/`display_name` but do NOT lowercase `slug`; reject empty/whitespace-only `slug`/`display_name`.
- [ ] 4.3 Reject any `slug` field present in the `PATCH` body (slug is immutable after creation).
- [ ] 4.4 Map `DuplicateUnitSlugError` to 409, `UnitInUseError` to 409, not-found lookups to 404.
- [ ] 4.5 Register `build_unit_router()` in `src/app.py` alongside the other routers.

## 5. Wire measurements to the unit catalog

- [ ] 5.1 In `src/aquarium_measurements.py`, update `_validate_measurement_payload` to look up the submitted `unit` string case-insensitively via `UnitRepository.get_by_slug`, 422 if not found, then confirm a `parameter_units` row exists for `(parameter_id, unit.id)`, 422 if not — replacing the `unit not in rule.supported_units` frozenset check while keeping the existing 422 error shape/message.
- [ ] 5.2 Update `_canonicalize_measurement`/the create-measurement flow so the canonical unit string returned by `rule.canonicalize(...)` is resolved to a `Unit` row (case-insensitive lookup) before calling `measurement_repo.create_measurement(..., unit_id=..., raw_unit_id=...)`.
- [ ] 5.3 Update `_to_payload` (and any list/history serialization) to resolve `unit_id`/`raw_unit_id` back to slug strings for the response, preserving the catalog's stored casing.
- [ ] 5.4 Keep `PARAMETER_RULES` (conversion functions, value-range validation, `supported_units` used only as the seed source in 2.3) in place — this change does not touch conversion math, only the membership/storage mechanism.
- [ ] 5.5 Test env parity: add `_seed_units`/`_seed_parameter_units` to `src/db.py` (mirroring `_seed_parameters`) with the same literal seed data as the migration, so SQLite-backed tests match Postgres-backed prod data. Confirm SQLite FK enforcement (`PRAGMA foreign_keys=ON`) already established for the parameter catalog also covers the new `unit_id`/`raw_unit_id` FKs.

## 6. Tests

- [ ] 6.1 Add `tests/test_unit_repository.py`: create/list/get/update/delete, case-insensitive duplicate-slug rejected, delete-while-referenced rejected (by measurement and by `parameter_units`).
- [ ] 6.2 Add `tests/test_units.py`: router-level tests for all 5 endpoints, auth-required, validation errors, envelope shape, case-insensitive `GET /units/{slug}`, seeded units present.
- [ ] 6.3 Update `tests/test_aquarium_measurements.py`: unsupported-unit-per-parameter scenarios still 422 (now catalog-driven); a unit that exists in the catalog but isn't associated with the requested parameter is rejected; response `unit`/`raw_unit` fields remain slug strings in original casing (e.g. `"pH"`, `"mg/L"`), never UUIDs.
- [ ] 6.4 Update `tests/test_aquarium_measurement_repository.py` for the `unit_id`/`raw_unit_id` signature change.
- [ ] 6.5 Add a repository/router test confirming FK `ON DELETE RESTRICT` behavior for units (deleting a referenced unit fails; deleting an unreferenced one succeeds).
- [ ] 6.6 Run `task coverage` and confirm overall coverage stays at/above the existing baseline.

## 7. Verification

- [ ] 7.1 Run `task lint` and `task typecheck` and fix any issues.
- [ ] 7.2 Run `task test` and confirm the full suite passes.
- [ ] 7.3 Manually exercise `GET /api/v1/units` and a measurement create/list round-trip via `task server` + a dev token (`task token`) to confirm catalog-backed units work end-to-end and response shapes are unchanged from before this change.
