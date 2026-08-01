## Context

`Parameter` (salinity, temperature, ph, ...) is already a DB-backed catalog (`parameters` table, `ParameterRepository`, `/parameters` CRUD API) from the recently-implemented (not yet archived/synced) `parameter-catalog` change. Units are not: `SUPPORTED_*_UNITS` frozensets and the `PARAMETER_RULES` dict in `src/aquarium_measurements.py` hardcode, per parameter, which unit strings are accepted, which one is canonical, and how to convert between them. `AquariumMeasurement.unit`/`raw_unit` are bare `String(16)` columns with no DB-level constraint tying them to a known set of units.

Two casing conventions collide in the current code and constrain this design:
- Client-submitted `unit` values are lowercased/trimmed before validation (`CreateMeasurementRequest` validator, `src/aquarium_measurements.py`), and checked against lowercase sets (e.g. `{"ph"}`, `{"mg/l"}`, `{"dkh"}`).
- Canonical (stored and returned) unit strings use mixed case: `pH`, `mg/L`, `dKH`, alongside lowercase ones: `ppt`, `sg`, `celsius`, `fahrenheit`, `ppm`.

This design must preserve both behaviors (forgiving input casing, exact-cased output) since the proposal commits to no client-facing contract change on existing measurement endpoints.

**Revision note**: an earlier iteration of this design used a single `Unit.slug` field for both the measurement API's notation string (`"mg/L"`) and the `/units/{slug}` routing key, with case-insensitive matching and a FastAPI `:path` converter to work around `/` in slugs like `mg/L`. Post-implementation review flagged this as fragile — URL routing keys shouldn't need special-case handling for `/`. The design was revised to split these into two columns: `unit` (the notation, unconstrained) and `slug` (a derived, URL-safe routing key: lowercase, `/` → `_`). The sections below describe the final, revised design.

`AquariumParameterThreshold.unit` and `Aquarium.volume_liters`'s unit strings (`L`/`gal_us`, in `src/aquariums.py`) have the same "bare string" shape but are explicitly out of scope (see Non-Goals).

## Goals / Non-Goals

**Goals:**
- Units become a real DB catalog (`units` table) with a stable `unit` notation and a derived `slug`, browsable/manageable via a `/units` CRUD API, following the same router/repository/response-envelope shape as `/parameters`.
- `aquarium_measurements.unit`/`raw_unit` become FK references (`unit_id`/`raw_unit_id`) to `units.id`, enforced at the DB level.
- A `parameter_units` many-to-many join table records which units are valid for which parameter, including which one is that parameter's canonical (stored) unit — replacing the membership-check role of `SUPPORTED_*_UNITS`.
- Existing measurement create/list API request/response shapes are unchanged: clients still send/receive unit **notation** strings via `units.unit` (e.g. `"ppt"`, `"pH"`, `"mg/L"`), never UUIDs and never the URL-safe `slug`, with the same forgiving input-casing behavior as today.
- `units.slug` is a URL-safe, unique routing key (lowercase, `/` → `_`) usable directly as a single path segment in `/units/{slug}` — no path converters or case-insensitive matching required for it.

**Non-Goals:**
- Making unit *conversion* (the math in `_to_ppt`, `_to_celsius`, `fahrenheit_to_celsius`) generic or data-driven. Only two parameters (salinity, temperature) have real multi-unit conversion; it stays as parameter-keyed Python functions in `PARAMETER_RULES`, now validated against the DB catalog rather than a Python frozenset.
- Migrating `aquarium_parameter_thresholds.unit` to `unit_id`. Left as a follow-up change; it keeps its current string column and its own `THRESHOLD_UNITS` mapping.
- Migrating `Aquarium.volume_liters`'s unit handling (`SUPPORTED_VOLUME_UNITS = {"L", "gal_us"}` in `src/aquariums.py`) to reference `units`. Volume units are seeded into the `units` catalog (since the proposal names `L` as an example unit) but are not wired into `parameter_units` or the aquarium volume code path in this change.
- Normalizing unit slug casing (e.g. forcing everything lowercase). Existing canonical casing (`pH`, `mg/L`, `dKH`) is preserved as-is to avoid an unrelated breaking change to response payloads.

## Decisions

**`Unit` model shape**: `id` (UUID PK, `Uuid()` type per existing convention), `unit` (`String(16)`, the physical notation as used in measurement data, e.g. `"mg/L"`), `slug` (`String(16)`, unique, indexed, derived from `unit`), `display_name`, `description` (nullable), timestamps. Mirrors `Parameter` in shape but splits identity into two fields instead of one.

**`unit` vs. `slug` split**: `unit` carries the real notation exactly as used in measurement data and API responses (mixed case, may contain `/`: `pH`, `mg/L`, `dKH`, `ppt`, ...). `slug` is derived from it via `slugify_unit()` (`src/unit_slug.py`: `unit.strip().lower().replace("/", "_")`) at creation time and is immutable thereafter — e.g. `"mg/L"` → `"mg_l"`. `slug` is a plain unique-indexed column (case-sensitive equality is fine since it's always lowercase by construction); `unit` has no separate DB uniqueness constraint of its own, but two units that would derive the same `slug` (e.g. `"mg/L"` and `"MG/l"`) collide on the `slug` unique constraint at create time, which is the desired protection.
- *Alternative considered (original design)*: a single `slug` field carrying the canonical-cased notation, matched case-insensitively, with `/units/{slug:path}` routes to tolerate `/`. Rejected on review — mixing a display/notation string with a URL routing key forced case-insensitive lookups and a path-converter workaround everywhere `slug` was used. Splitting the two concerns removes both workarounds entirely.
- *Alternative considered*: normalize `Unit.slug` to lowercase with no separate notation field, requiring the measurement API to switch to lowercase-only unit strings (e.g. `"mg_l"` instead of `"mg/L"`). Rejected — a real (if cosmetic) breaking change to every existing measurement response, which the proposal rules out.

**`raw_unit` casing normalizes to the catalog's casing (implementation finding)**: `CreateMeasurementRequest.validate_unit` (`src/aquarium_measurements.py`) unconditionally lowercases the submitted `unit` string before it's used as `raw_unit`. Today this means `raw_unit` for `ammonia`/`ph`/`alkalinity` is stored/returned lowercased (`mg/l`, `ph`, `dkh`) even though the canonical `unit` for those parameters is mixed-case (`mg/L`, `pH`, `dKH`) — the "original entered unit" was never byte-faithful to begin with, only the raw *value* was ever preserved unconverted. Since both `unit_id` and `raw_unit_id` now resolve (case-insensitively, via `UnitRepository.get_by_unit`) to the *same* single `Unit` catalog row per physical unit, `raw_unit` in the response necessarily takes on that row's canonical (`unit` column) casing too. This is a deliberate, minor behavior normalization (see proposal.md), not a regression — updated `tests/test_aquarium_measurements.py` accordingly.

**Two lookup methods on `UnitRepository`, not one**: `get_by_slug(slug)` — exact match after lowercasing the input, used only by the `/units/{slug}` CRUD routes. `get_by_unit(unit)` — case-insensitive match against the `unit` notation column, used by measurement validation/canonicalization (`_validate_measurement_payload`, resolving `rule.canonical_unit` to a catalog row) and by `AquariumMeasurementRepository`'s legacy `create_salinity`/`list_salinity` wrappers. These serve genuinely different callers (URL routing vs. measurement-notation matching) and conflating them was the root cause of the `:path`-converter workaround above.

**Unit catalog CRUD routes use a plain `{slug}` path parameter**: since `slug` can no longer contain `/`, `src/units.py`'s `GET/PATCH/DELETE /units/{slug}` routes need no path converter or case-insensitive matching — a plain FastAPI string path parameter suffices.

**`parameter_units` join table**: composite table `parameter_id` (FK → `parameters.id`), `unit_id` (FK → `units.id`), `is_canonical` (bool, not null, default false), `PRIMARY KEY (parameter_id, unit_id)`, plus a partial unique index on `parameter_id WHERE is_canonical` so each parameter has at most one canonical unit. This table is the DB source of truth for "which units are valid for this parameter" and "which one is canonical," replacing `ParameterRule.supported_units` / `ParameterRule.canonical_unit` as the *membership* check — `ParameterRule` itself stays in code for the *conversion function*.
- *Alternative considered*: store `canonical_unit_id` directly on `Parameter` instead of a flag on the join row. Rejected — a flag on the join row keeps "is this unit valid for this parameter" and "is it the canonical one" as a single queryable fact per pair, and avoids a circular-ish FK from `parameters` back into a `units`-derived id at the same time the join table is being introduced.

**Validation flow change**: `_validate_measurement_payload`/`_normalize_parameter` in `src/aquarium_measurements.py` gain a DB check — given a `parameter_id` and a lowercased `unit` string, look up `Unit` via `get_by_unit` (case-insensitive), then confirm a `parameter_units` row exists for that `(parameter_id, unit_id)` pair — 422 if either lookup fails. `PARAMETER_RULES[slug].canonicalize(value, unit)` still runs afterward for the actual value conversion and continues to return the fixed canonical unit string (e.g. `"pH"`); that string is resolved to `unit_id` via the same `get_by_unit` lookup before persisting.

**Repository signature change**: `AquariumMeasurementRepository.create_measurement`/`list_measurements` move from `unit: str`/`raw_unit: str` params to `unit_id: uuid.UUID`/`raw_unit_id: uuid.UUID`. Slug↔id resolution happens in the router layer (via `UnitRepository`), matching how `parameter_id` resolution already works — the measurement repository itself stays free of slug-string concerns.

**Test seeding**: `src/db.py`'s `_seed_parameters`-style test bootstrap gains an equivalent `_seed_units` + `_seed_parameter_units`, seeded with the same literal strings as the migration, so SQLite-backed tests match Postgres-backed prod data.

## Risks / Trade-offs

- [Backfill migration depends on exact string match between old `unit`/`raw_unit` values and seeded `Unit.slug` values (pre-revision) / `Unit.unit` values (post-revision)] → The `20260731_000003_add_unit_catalog` seed step and the `20260731_000004_aquarium_measurements_unit_fk` backfill join case-insensitively on `slug` (which at that point in the migration chain still holds the original notation, before `20260731_000005` normalizes it) — confirmed against a real Postgres instance with a deliberately mismatched-casing pre-existing row (`raw_unit='mg/l'` vs. seeded `'mg/L'`).
- [Two sources of truth for parameter↔unit validity: `parameter_units` table for existence, `PARAMETER_RULES` in Python for conversion math and value-range rules] → Same trade-off already accepted by `parameter-catalog` for parameter identity vs. parameter validation rules; acceptable since only 10 parameters / ~9 units exist and both are touched together in code review when either changes.
- [`AquariumParameterThreshold.unit` and `Aquarium.volume_liters` units are left as bare strings, so the codebase temporarily has both FK-backed and string-backed unit fields] → Explicitly called out as a Non-Goal/follow-up; not a regression since thresholds/volume units are unaffected by this change either way.

## Migration Plan

1. Create `units` table (empty) and `parameter_units` table (empty) via Alembic migration (`20260731_000003_add_unit_catalog`).
2. Seed `units` with the full current unit-string set: `ppt`, `sg`, `celsius`, `fahrenheit`, `ppm`, `mg/L`, `pH`, `dKH`, plus `L`, `gal_us` (aquarium-volume units, unattached to any parameter for now) — at this point `slug` still holds the original notation (this migration predates the `unit`/`slug` split).
3. Seed `parameter_units` from the current `PARAMETER_RULES` supported-units/canonical-unit mapping (e.g. salinity → `ppt` (canonical), `sg`; temperature → `celsius` (canonical), `fahrenheit`; phosphate → `ppm` (canonical); ... ph → `pH` (canonical)).
4. Add nullable `unit_id`/`raw_unit_id` columns to `aquarium_measurements`; backfill via a case-insensitive join on `units.slug` (still notation-valued at this point); set `NOT NULL`; add FK constraints and indexes; drop the old `unit`/`raw_unit` string columns (`20260731_000004_aquarium_measurements_unit_fk`).
5. Add `units.unit` (nullable), backfill `unit = slug` (copying the notation values seeded in step 2), set `NOT NULL`; transform `slug` in place to its URL-safe form (`UPDATE units SET slug = lower(replace(slug, '/', '_'))`); replace the functional case-insensitive slug index with a plain unique index on `slug` (`20260731_000005_units_add_unit_and_normalize_slug`). `parameter_units` rows are unaffected since they reference `unit_id` (UUID), not the slug string.

Rollback: each migration's `downgrade()` reverses its own steps — `20260731_000005` restores `slug = unit` and drops the `unit` column; `20260731_000004` re-derives `unit`/`raw_unit` strings from the FK'd `unit_id`/`raw_unit_id` via `units.slug`; `20260731_000003` drops `parameter_units`/`units`. No data loss in any direction since every step is a 1:1 mapping.

## Open Questions

- Should `aquarium_parameter_thresholds.unit` be migrated to `unit_id` in this change or a dedicated follow-up? Current call: follow-up, to keep this change's blast radius to measurements + the new catalog, matching how `parameter-catalog` scoped its first pass.
- Should `Aquarium.volume_liters` eventually reference `units` too (for `L`/`gal_us`)? Out of scope here; flagged as a natural next candidate once the catalog exists.
