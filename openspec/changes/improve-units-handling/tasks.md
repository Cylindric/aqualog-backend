## 1. Data model

- [x] 1.1 Add `Unit` model to `src/models.py`: `id` (`Uuid()` PK), `slug` (`String(16)`, unique, not-null, indexed, case preserved as submitted), `display_name` (not-null), `description` (nullable), `created_at`, `updated_at`.
- [x] 1.2 Add a functional/case-insensitive unique index on `Unit.slug` (e.g. `Index(..., func.lower(Unit.slug), unique=True)`) so `pH`/`Ph`/`ph` collide as duplicates.
- [x] 1.3 Add `ParameterUnit` association model/table `parameter_units`: `parameter_id` (FK → `parameters.id`, `ondelete="CASCADE"`), `unit_id` (FK → `units.id`, `ondelete="RESTRICT"`), `is_canonical` (bool, not-null, default `False`), composite PK `(parameter_id, unit_id)`.
- [x] 1.4 Add a partial unique index on `parameter_units.parameter_id WHERE is_canonical` so each parameter has at most one canonical unit. Declared with both `sqlite_where=` and `postgresql_where=` so the SQLite-backed test schema also enforces it (a Postgres-only `postgresql_where` would silently produce a full unique index on SQLite, which would reject salinity's two rows).
- [x] 1.5 Change `AquariumMeasurement.unit`/`raw_unit` in `src/models.py` from `String(16)` to `unit_id`/`raw_unit_id` (`Uuid()`, `ForeignKey("units.id", ondelete="RESTRICT")`, not-null). Added `unit`/`raw_unit` `relationship()` attributes (same names as the old string columns) pointing at `Unit`, so callers read `measurement.unit.slug` instead of a raw string.

## 2. Migration

- [x] 2.1 Hand-written Alembic migration `20260731_000003_add_unit_catalog.py` (no live Postgres in the initial sandbox for `db-migration-new`'s autogenerate; written by hand following the existing `20260730_000001_add_parameter_catalog.py` pattern) creating the `units` and `parameter_units` tables.
- [x] 2.2 Bulk-inserts the unit catalog: `ppt`, `sg`, `celsius`, `fahrenheit`, `ppm`, `mg/L`, `pH`, `dKH`, plus `L`, `gal_us` (aquarium volume units, unattached to any parameter).
- [x] 2.3 Bulk-inserts `parameter_units` rows (via `INSERT ... SELECT` joining `parameters`/`units` by slug) matching each parameter's current `SUPPORTED_*_UNITS`/canonical unit.
- [x] 2.4 Second migration `20260731_000004_aquarium_measurements_unit_fk.py`: adds nullable `unit_id`/`raw_unit_id`, backfills, sets `NOT NULL`, adds FKs/indexes, drops old string columns. **Backfill uses a case-insensitive join** (`lower(units.slug) = lower(aquarium_measurements.unit)`), not exact match — existing `raw_unit` values for ammonia/ph/alkalinity are stored lowercased (`mg/l`, `ph`, `dkh`) by the current create-measurement validator, while the seeded catalog slugs use canonical casing (`mg/L`, `pH`, `dKH`); an exact-match join would leave those rows' `raw_unit_id` NULL and fail the subsequent `SET NOT NULL`.
- [x] 2.5 `downgrade()` written for both migrations, reversing table/column creation and re-deriving string columns from the FK'd unit slugs.
- [x] 2.6 Verified end-to-end against a real, isolated Postgres instance (`docker compose up backenddb` from this worktree's own `docker-compose.yml`, port 5433 — not the user's other running containers): migrated to `20260731_000002`, hand-inserted pre-existing measurement rows including a `raw_unit='mg/l'` vs. canonical `mg/L` casing mismatch, ran `alembic upgrade head` — backfill resolved both rows correctly (`unit_id`/`raw_unit_id` both point at the `mg/L` catalog row), `NOT NULL`/FK constraints applied cleanly. Also verified `alembic downgrade` back to `20260731_000002` and re-`upgrade head` round-trip the data correctly. Container torn down after (`docker compose down`).

## 3. Repository layer

- [x] 3.1 Created `src/unit_repository.py` with `UnitRepository`: `list_all()`, `get_by_slug(slug)` (case-insensitive via `func.lower`), `create(...)`, `update_by_slug(...)`, `delete_by_slug(...)`.
- [x] 3.2 `DuplicateUnitSlugError` raised on unique-constraint violation, translated from `IntegrityError`.
- [x] 3.3 `UnitInUseError` raised when `delete_by_slug` hits a FK-violation `IntegrityError`.
- [x] 3.4 Added `list_units_for_parameter(parameter_id)`, `get_canonical_unit(parameter_id)`, and `is_unit_valid_for_parameter(parameter_id, unit_id)` on `UnitRepository`.
- [x] 3.5 `AquariumMeasurementRepository.create_measurement` now takes `unit_id`/`raw_unit_id` (UUIDs). `create_salinity`/`list_salinity` (legacy convenience wrappers) resolve `"ppt"`/the given raw unit string to ids internally via a new `_unit_id_by_slug` helper, so their own signature is unchanged.

## 4. API router

- [x] 4.1 Created `src/units.py` with `build_unit_router()` exposing `GET /units`, `GET/PATCH/DELETE /units/{slug}`, `POST /units`, behind `get_current_user`, via `success_response`/`error_response`. **Note**: the slug routes use FastAPI's `{slug:path}` converter, not a plain `{slug}` — several canonical unit slugs contain a literal `/` (`mg/L`), which a plain string path parameter cannot match (Starlette's default converter excludes `/`).
- [x] 4.2 Added `CreateUnitRequest`, `UpdateUnitRequest`, `UnitPayload`, list/detail response wrappers. `slug`/`display_name` are trimmed but `slug` is NOT lowercased (unlike `Parameter.slug`); empty/whitespace-only values rejected.
- [x] 4.3 `UpdateUnitRequest` has no `slug` field and `model_config = ConfigDict(extra="forbid")`, so a `slug` in the `PATCH` body is rejected with 422 automatically (same pattern as `UpdateParameterRequest`).
- [x] 4.4 `DuplicateUnitSlugError` → 409, `UnitInUseError` → 409, not-found → 404.
- [x] 4.5 Registered `build_unit_router()` in `src/app.py`.

## 5. Wire measurements to the unit catalog

- [x] 5.1 `_validate_measurement_payload` now takes the `Parameter` row and a `UnitRepository`, looks up the submitted `unit` string case-insensitively, 422s if not found or not associated with the parameter via `parameter_units`, then still runs the existing `rule.validate_value` range check. Returns the resolved `Unit` row.
- [x] 5.2 Create-measurement flow resolves the canonical unit slug (from `rule.canonicalize`) to its `Unit` row before calling `create_measurement(..., unit_id=..., raw_unit_id=...)`.
- [x] 5.3 `_to_payload` reads `measurement.unit.slug`/`measurement.raw_unit.slug` via the new relationships.
- [x] 5.4 `PARAMETER_RULES` (conversion functions, range validation) untouched — only the unit-membership check and storage mechanism changed.
- [x] 5.5 Added `_seed_units`/`_seed_parameter_units` to `src/db.py`, seeded in `init_database` alongside `_seed_parameters`. SQLite FK enforcement (`PRAGMA foreign_keys=ON`, already wired for the parameter catalog) covers the new `unit_id`/`raw_unit_id` FKs without changes.

## 6. Tests

- [x] 6.1 Added `tests/test_unit_repository.py` (7 tests): CRUD, case-insensitive get/duplicate-rejection, delete blocked by measurement reference and by `parameter_units` reference, `list_units_for_parameter`/`get_canonical_unit`/`is_unit_valid_for_parameter`.
- [x] 6.2 Added `tests/test_units.py` (12 tests): auth-required, seeded catalog list, case-insensitive get, create (casing preserved, case-insensitive duplicate rejected, validation errors), update (including slug-lock), delete (unreferenced succeeds; blocked by measurement; blocked by parameter association).
- [x] 6.3 `tests/test_aquarium_measurements.py`: existing unsupported-unit/validation scenarios already catalog-driven now (unchanged pass/fail outcomes) — 30/30 still pass. Updated one assertion (`raw_unit == unit.lower()` → `raw_unit == unit`) to reflect the raw_unit casing normalization described in task 2.4/design.md.
- [x] 6.4 Updated `tests/test_aquarium_measurement_repository.py` for the `unit_id`/`raw_unit_id` signature change (added `_create_unit` helper, `PRAGMA foreign_keys=ON`), plus a new FK-restriction test. Also fixed a knock-on breakage in `tests/test_parameter_repository.py` (it called the old `create_measurement(unit=..., raw_unit=...)` signature).
- [x] 6.5 `test_unit_repository_delete_blocked_while_referenced_by_measurement`, `test_unit_repository_delete_blocked_while_referenced_by_parameter_unit`, `test_measurement_repository_unit_fk_restricts_deletion_while_referenced`, and router-level `test_delete_unit_referenced_by_measurement_is_rejected`/`test_delete_unit_referenced_by_parameter_association_is_rejected` cover FK `ON DELETE RESTRICT` for units from both angles.
- [x] 6.6 Full suite: 163 passed. Coverage 94% overall (matches the prior baseline noted in the `parameter-catalog` change); new modules `unit_repository.py` 100%, `models.py` 100%, `units.py` 99%.

## 7. Verification

- [x] 7.1 `poetry run ruff check .` and `poetry run ruff format .` clean. `poetry run mypy src` clean (fixed one bare-`assert` S101 lint violation by raising `RuntimeError` instead, and one mypy `type` vs `Any` attribute-access error in `db.py`'s new seed helper).
- [x] 7.2 `poetry run pytest -q` (`AQUALOG_APP_ENV=test`): 163 passed, no failures, no hang (unlike the `parameter-catalog` change's noted sandbox issue — full suite ran fine here).
- [x] 7.3 End-to-end verification done via the real-Postgres migration round-trip in 2.6 (schema, backfill, FK constraints, downgrade/re-upgrade) plus the full `TestClient`-based HTTP test suite (auth mocked, real request/response envelope, real SQLite-backed FK enforcement) rather than a live `task server` + Authentik `task token` run — avoided bringing up the shared dev Authentik/db containers for this. `GET /api/v1/units`, measurement create/list with catalog-backed units, and unchanged response shapes are all exercised by `tests/test_units.py` and `tests/test_aquarium_measurements.py`.
