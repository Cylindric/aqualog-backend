## 1. Data model

- [x] 1.1 Add `Parameter` model to `src/models.py`: `id` (UUID str PK), `slug` (unique, not-null, indexed), `display_name` (not-null), `description` (nullable), `created_at`, `updated_at`.
- [x] 1.2 Change `AquariumMeasurement.parameter` in `src/models.py` to `ForeignKey("parameters.slug", ondelete="RESTRICT")`.
- [x] 1.3 Change `AquariumParameterThreshold.parameter` in `src/models.py` to `ForeignKey("parameters.slug", ondelete="RESTRICT")`.

## 2. Migration

- [x] 2.1 Generate Alembic migration (`task db-migration-new NAME="add_parameter_catalog"`) creating the `parameters` table.
- [x] 2.2 In the migration, bulk-insert the 10 existing parameters (`salinity`, `phosphate`, `temperature`, `calcium`, `ammonia`, `nitrite`, `nitrate`, `ph`, `alkalinity`, `magnesium`) with display names and short descriptions derived from `PARAMETER_RULES`/`THRESHOLD_UNITS` in `src/aquarium_measurements.py`.
- [x] 2.3 In the migration, add the FK constraints (`ON DELETE RESTRICT`) from `aquarium_measurements.parameter` and `aquarium_parameter_thresholds.parameter` to `parameters.slug`, after the seed insert so existing rows resolve.
- [x] 2.4 Write the migration `downgrade()` to drop the FK constraints, then the seed rows, then the `parameters` table.
- [x] 2.5 Run `task db-migrate` locally and confirm it applies cleanly against an existing dev database with pre-existing measurement/threshold rows.

## 3. Repository layer

- [x] 3.1 Create `src/parameter_repository.py` with `ParameterRepository`: `list_all()`, `get_by_slug(slug)`, `create(slug, display_name, description)`, `update_by_slug(slug, updates)`, `delete_by_slug(slug)`.
- [x] 3.2 Raise a `DuplicateParameterSlugError` on unique-constraint violation during create, translated from `IntegrityError`, matching the pattern used in `AquariumRepository`/`DuplicateAquariumNameError`.
- [x] 3.3 Raise a `ParameterInUseError` when `delete_by_slug` hits a FK-violation `IntegrityError` (i.e. the parameter is still referenced by a measurement or threshold).

## 4. API router

- [x] 4.1 Create `src/parameters.py` with `build_parameter_router()` exposing `GET /parameters`, `GET /parameters/{slug}`, `POST /parameters`, `PATCH /parameters/{slug}`, `DELETE /parameters/{slug}`, all behind `get_current_user`, all responses via `success_response`/`error_response`.
- [x] 4.2 Add request/response Pydantic models (`CreateParameterRequest`, `UpdateParameterRequest`, `ParameterPayload`, list/detail response wrappers), normalizing `slug` to trimmed lowercase and rejecting empty/whitespace-only `slug`/`display_name`.
- [x] 4.3 Reject any `slug` field present in the `PATCH` body (slug is immutable after creation).
- [x] 4.4 Map `DuplicateParameterSlugError` to 409, `ParameterInUseError` to 409, not-found lookups to 404.
- [x] 4.5 Register `build_parameter_router()` in `src/app.py` alongside the other routers.

## 5. Wire existing resources to the catalog

- [x] 5.1 In `src/aquarium_measurements.py`, replace the `SUPPORTED_PARAMETERS`-membership check in `_normalize_parameter` with a `ParameterRepository.get_by_slug` lookup (inject/construct the repo from the request's `Session`), keeping the existing 422 error shape and message.
- [x] 5.2 In `src/aquarium_parameter_thresholds.py`, replace the `SUPPORTED_THRESHOLD_PARAMETERS`-membership check in `_normalize_parameter` with the same catalog lookup, keeping `PARAMETER_RULES`/`THRESHOLD_UNITS`/`THRESHOLD_SANITY_RANGES` gating unchanged (a parameter must exist in the catalog AND have a defined threshold rule to be accepted).
- [x] 5.3 Confirm `SUPPORTED_PARAMETERS`/`SUPPORTED_THRESHOLD_PARAMETERS` frozensets are removed if no longer referenced elsewhere, or retained only where still needed for `PARAMETER_RULES`-keyed validation (unit/range checks, unaffected by this change). Both are still referenced (measurements' rule-membership check and the thresholds alias/import), so retained as-is.
- [x] 5.4 Test env parity: since `tests/conftest.py`/`src/db.py::init_database` builds the schema from model metadata (not Alembic) for `AQUALOG_APP_ENV=test`, add the same 10-parameter seed there so catalog-driven validation behaves identically to a migrated dev/prod DB, and enable `PRAGMA foreign_keys=ON` for SQLite connections so the `ON DELETE RESTRICT` FK is actually enforced in tests (SQLite ignores FKs by default).

## 6. Tests

- [x] 6.1 Add `tests/test_parameter_repository.py`: create/list/get/update/delete, duplicate slug rejected, delete-while-referenced rejected.
- [x] 6.2 Add `tests/test_parameters.py`: router-level tests for all 5 endpoints, auth-required, validation errors, envelope shape, seeded parameters present.
- [x] 6.3 Update `tests/test_aquarium_measurements.py` (or equivalent) so parameter-support assertions reflect catalog-driven validation (e.g. a parameter absent from the catalog is rejected; catalog seed data covers all previously-tested parameters).
- [x] 6.4 Update `tests/test_aquarium_parameter_thresholds.py` (or equivalent) the same way for thresholds.
- [x] 6.5 Add a migration test or repository test confirming FK `ON DELETE RESTRICT` behavior (deleting a referenced parameter raises/fails; deleting an unreferenced one succeeds).
- [x] 6.6 Run `task coverage` and confirm overall coverage stays at/above the existing baseline. Ran in batches (see 7.2 note) due to a pre-existing environment issue; cumulative coverage across all 144 tests is 94%, with the new `models.py`/`parameter_repository.py` at 100% and `parameters.py` at 99%.

## 7. Verification

- [x] 7.1 Run `task lint` and `task typecheck` and fix any issues. Both pass clean (`ruff check`, `mypy src`).
- [x] 7.2 Run `task test` and confirm the full suite passes. Found a **pre-existing, change-unrelated** environment issue: running the entire suite in one `pytest` process hangs partway through (reproduced identically on unmodified `main` via `git stash`) — looks like cumulative resource exhaustion across many `TestClient`/`create_app()` instantiations in this sandbox, not a regression from this change. Ran all 144 tests in smaller batches instead (grouped by file); all 144 pass.
- [x] 7.3 Manually exercise `GET /api/v1/parameters` via `task server` + a dev token (`task token`) to confirm the seeded catalog is returned end-to-end.
