## Context

`Parameter` (salinity, temperature, ph, ...) is already a DB-backed catalog (`parameters` table, `ParameterRepository`, `/parameters` CRUD API) from the recently-implemented (not yet archived/synced) `parameter-catalog` change. Units are not: `SUPPORTED_*_UNITS` frozensets and the `PARAMETER_RULES` dict in `src/aquarium_measurements.py` hardcode, per parameter, which unit strings are accepted, which one is canonical, and how to convert between them. `AquariumMeasurement.unit`/`raw_unit` are bare `String(16)` columns with no DB-level constraint tying them to a known set of units.

Two casing conventions collide in the current code and constrain this design:
- Client-submitted `unit` values are lowercased/trimmed before validation (`CreateMeasurementRequest` validator, `src/aquarium_measurements.py`), and checked against lowercase sets (e.g. `{"ph"}`, `{"mg/l"}`, `{"dkh"}`).
- Canonical (stored and returned) unit strings use mixed case: `pH`, `mg/L`, `dKH`, alongside lowercase ones: `ppt`, `sg`, `celsius`, `fahrenheit`, `ppm`.

This design must preserve both behaviors (forgiving input casing, exact-cased output) since the proposal commits to no client-facing contract change on existing measurement endpoints.

`AquariumParameterThreshold.unit` and `Aquarium.volume_liters`'s unit strings (`L`/`gal_us`, in `src/aquariums.py`) have the same "bare string" shape but are explicitly out of scope (see Non-Goals).

## Goals / Non-Goals

**Goals:**
- Units become a real DB catalog (`units` table) with a stable `slug`, browsable/manageable via a `/units` CRUD API, following the same router/repository/response-envelope shape as `/parameters`.
- `aquarium_measurements.unit`/`raw_unit` become FK references (`unit_id`/`raw_unit_id`) to `units.id`, enforced at the DB level.
- A `parameter_units` many-to-many join table records which units are valid for which parameter, including which one is that parameter's canonical (stored) unit — replacing the membership-check role of `SUPPORTED_*_UNITS`.
- Existing measurement create/list API request/response shapes are unchanged: clients still send/receive unit `slug` strings (e.g. `"ppt"`, `"pH"`), never UUIDs, with the same forgiving input-casing behavior as today.

**Non-Goals:**
- Making unit *conversion* (the math in `_to_ppt`, `_to_celsius`, `fahrenheit_to_celsius`) generic or data-driven. Only two parameters (salinity, temperature) have real multi-unit conversion; it stays as parameter-keyed Python functions in `PARAMETER_RULES`, now validated against the DB catalog rather than a Python frozenset.
- Migrating `aquarium_parameter_thresholds.unit` to `unit_id`. Left as a follow-up change; it keeps its current string column and its own `THRESHOLD_UNITS` mapping.
- Migrating `Aquarium.volume_liters`'s unit handling (`SUPPORTED_VOLUME_UNITS = {"L", "gal_us"}` in `src/aquariums.py`) to reference `units`. Volume units are seeded into the `units` catalog (since the proposal names `L` as an example unit) but are not wired into `parameter_units` or the aquarium volume code path in this change.
- Normalizing unit slug casing (e.g. forcing everything lowercase). Existing canonical casing (`pH`, `mg/L`, `dKH`) is preserved as-is to avoid an unrelated breaking change to response payloads.

## Decisions

**`Unit` model shape**: `id` (UUID PK, `Uuid()` type per existing convention), `slug` (`String(16)`, unique, indexed — sized to fit the largest existing unit string), `display_name`, `description` (nullable), timestamps. Mirrors `Parameter` exactly except for the slug-casing rule below.

**Slug casing and lookup**: unlike `Parameter.slug` (always normalized to lowercase), `Unit.slug` is stored using its current canonical casing (`ppt`, `sg`, `celsius`, `fahrenheit`, `ppm`, `mg/L`, `pH`, `dKH`, `L`, `gal_us`) so existing response payloads are byte-for-byte unchanged. Lookups (both `GET /units/{slug}` and internal validation of a submitted `unit` string) are case-insensitive (`func.lower(Unit.slug) == value.lower()`), matching today's forgiving input behavior where `"PH"`/`"Ph"`/`"ph"` are all accepted.
- *Alternative considered*: normalize `Unit.slug` to lowercase like `Parameter`, with a separate `display_symbol` field for the pretty form. Rejected — it would require the measurement router to swap `unit` in responses from `slug` to `display_symbol`, which is a real (if cosmetic) breaking change to every existing response, and the proposal explicitly rules that out.

**`parameter_units` join table**: composite table `parameter_id` (FK → `parameters.id`), `unit_id` (FK → `units.id`), `is_canonical` (bool, not null, default false), `PRIMARY KEY (parameter_id, unit_id)`, plus a partial unique index on `parameter_id WHERE is_canonical` so each parameter has at most one canonical unit. This table is the DB source of truth for "which units are valid for this parameter" and "which one is canonical," replacing `ParameterRule.supported_units` / `ParameterRule.canonical_unit` as the *membership* check — `ParameterRule` itself stays in code for the *conversion function*.
- *Alternative considered*: store `canonical_unit_id` directly on `Parameter` instead of a flag on the join row. Rejected — a flag on the join row keeps "is this unit valid for this parameter" and "is it the canonical one" as a single queryable fact per pair, and avoids a circular-ish FK from `parameters` back into a `units`-derived id at the same time the join table is being introduced.

**Validation flow change**: `_validate_measurement_payload`/`_normalize_parameter` in `src/aquarium_measurements.py` gain a DB check — given a `parameter_id` and a lowercased `unit` string, look up `Unit` case-insensitively, then confirm a `parameter_units` row exists for that `(parameter_id, unit_id)` pair — 422 if either lookup fails. `PARAMETER_RULES[slug].canonicalize(value, unit)` still runs afterward for the actual value conversion and continues to return the fixed canonical unit string (e.g. `"pH"`); that string is resolved to `unit_id` via the same case-insensitive `Unit` lookup before persisting.

**Repository signature change**: `AquariumMeasurementRepository.create_measurement`/`list_measurements` move from `unit: str`/`raw_unit: str` params to `unit_id: uuid.UUID`/`raw_unit_id: uuid.UUID`. Slug↔id resolution happens in the router layer (via `UnitRepository`), matching how `parameter_id` resolution already works — the measurement repository itself stays free of slug-string concerns.

**Test seeding**: `src/db.py`'s `_seed_parameters`-style test bootstrap gains an equivalent `_seed_units` + `_seed_parameter_units`, seeded with the same literal strings as the migration, so SQLite-backed tests match Postgres-backed prod data.

## Risks / Trade-offs

- [Backfill migration depends on exact string match between old `unit`/`raw_unit` values and seeded `Unit.slug` values] → Seed `units` with the literal current canonical strings (`pH` not `ph`, `mg/L` not `mg/l`, etc.) confirmed by inspecting `PARAMETER_RULES` canonical units and existing DB values before writing the backfill; add a post-backfill assertion (`unit_id IS NOT NULL`) before dropping the old columns.
- [Two sources of truth for parameter↔unit validity: `parameter_units` table for existence, `PARAMETER_RULES` in Python for conversion math and value-range rules] → Same trade-off already accepted by `parameter-catalog` for parameter identity vs. parameter validation rules; acceptable since only 10 parameters / ~9 units exist and both are touched together in code review when either changes.
- [Case-insensitive `Unit.slug` lookups need a functional index (`lower(slug)`) to stay indexed in Postgres] → Add `Index("ix_units_slug_lower", func.lower(Unit.slug))` (or equivalent) alongside the unique constraint in the migration.
- [`AquariumParameterThreshold.unit` and `Aquarium.volume_liters` units are left as bare strings, so the codebase temporarily has both FK-backed and string-backed unit fields] → Explicitly called out as a Non-Goal/follow-up; not a regression since thresholds/volume units are unaffected by this change either way.

## Migration Plan

1. Create `units` table (empty) and `parameter_units` table (empty) via Alembic migration.
2. Seed `units` with the full current unit-string set: `ppt`, `sg`, `celsius`, `fahrenheit`, `ppm`, `mg/L`, `pH`, `dKH`, plus `L`, `gal_us` (aquarium-volume units, unattached to any parameter for now).
3. Seed `parameter_units` from the current `PARAMETER_RULES` supported-units/canonical-unit mapping (e.g. salinity → `ppt` (canonical), `sg`; temperature → `celsius` (canonical), `fahrenheit`; phosphate → `ppm` (canonical); ... ph → `pH` (canonical)).
4. Add nullable `unit_id`/`raw_unit_id` columns to `aquarium_measurements`.
5. Backfill: `UPDATE aquarium_measurements SET unit_id = units.id FROM units WHERE units.slug = aquarium_measurements.unit` (same for `raw_unit_id`/`raw_unit`).
6. Set `unit_id`/`raw_unit_id` `NOT NULL`, add FK constraints (`ON DELETE RESTRICT`, matching the `parameter_id` FK precedent) and indexes.
7. Drop the old `unit`/`raw_unit` string columns.
8. Follow the same backfill-then-cutover pattern used by `20260731_000002_parameter_fk_to_id.py` (already in this codebase) — steps 4-7 can be one migration given the small expected data volume, or split for extra safety; either is acceptable since this is a pre-production dataset.

Rollback: downgrade migration reverses steps 7→4 (re-add string columns, backfill from `units.slug` via the FK, drop `unit_id`/`raw_unit_id`, drop `parameter_units`/`units`). No data loss in either direction since the mapping is 1:1.

## Open Questions

- Should `aquarium_parameter_thresholds.unit` be migrated to `unit_id` in this change or a dedicated follow-up? Current call: follow-up, to keep this change's blast radius to measurements + the new catalog, matching how `parameter-catalog` scoped its first pass.
- Should `Aquarium.volume_liters` eventually reference `units` too (for `L`/`gal_us`)? Out of scope here; flagged as a natural next candidate once the catalog exists.
