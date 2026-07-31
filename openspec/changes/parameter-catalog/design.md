## Context

Supported water parameters (`salinity`, `phosphate`, `temperature`, `calcium`, `ammonia`, `nitrite`, `nitrate`, `ph`, `alkalinity`, `magnesium`) currently exist only as Python constants: `PARAMETER_RULES` in `src/aquarium_measurements.py` defines units/canonicalization/range-validation per parameter, and `SUPPORTED_PARAMETERS`/`SUPPORTED_THRESHOLD_PARAMETERS` are the membership sets used to validate the `{parameter}` path segment on `AquariumMeasurement` and `AquariumParameterThreshold` rows. Both tables store `parameter` as a bare `String(32)` with no referential integrity. This change introduces a `parameters` table as the single source of truth for which parameter slugs exist, with a display name and description, and makes both existing tables reference it via FK.

## Goals / Non-Goals

**Goals:**
- Persist the catalog of supported parameters (slug, display name, description) in the database, with full CRUD exposed over the API.
- Make `aquarium_measurements.parameter` and `aquarium_parameter_thresholds.parameter` FK-reference the catalog, so referential integrity is enforced by Postgres, not just an in-code set.
- Preserve the existing measurement/threshold API surface and response envelope exactly (paths, payload shapes, status codes) — this is a storage/validation refactor, not an API redesign for those two resources.
- Seed the catalog with the 10 parameters that exist today so current behavior is unchanged on deploy.

**Non-Goals:**
- Moving unit/range-validation rules (`PARAMETER_RULES`: supported units, canonical unit, min/max sanity ranges, conversion functions) into the database. Those stay as Python code keyed by slug; the catalog only governs parameter *identity* (does this slug exist, what is it called/described), not its measurement semantics.
- Allowing arbitrary user-defined parameters to automatically gain working unit conversion/validation — creating a new catalog row makes the slug pass FK/identity checks, but `PARAMETER_RULES`/`THRESHOLD_UNITS`/`THRESHOLD_SANITY_RANGES` still need a matching code entry for measurements/thresholds against that parameter to function. This is called out explicitly as a known gap (see Risks).
- Changing the `parameter` path-segment based API shape (still `/aquariums/{id}/measurements/{parameter}`, still string slugs).
- Multi-tenancy or per-user custom parameters — the catalog is global, not scoped per user.

## Decisions

**FK targets `parameters.slug`, not `parameters.id`.** The slug (e.g. `salinity`) is already the natural key used in URLs and stored today in `aquarium_measurements.parameter`/`aquarium_parameter_thresholds.parameter`. FKing on slug means the existing column type (`String(32)`), existing data, and existing route/serialization code (which reads/writes plain slug strings) need no changes beyond adding the constraint — only an `id` (UUID, for consistency with other tables) is added to `parameters` as its primary key, matching the `id: str = uuid4()` convention used elsewhere, while `slug` stays a separate unique, immutable column. Alternative considered: FK on a new `parameter_id` column added to both tables instead of reusing `parameter` — rejected because it would require renaming/migrating the column, touching every read path (`_to_payload`, filters, repository queries) in both resources for no behavioral benefit.

**Parameter membership validation moves from `SUPPORTED_PARAMETERS`/`SUPPORTED_THRESHOLD_PARAMETERS` (frozensets) to a `ParameterRepository` existence check.** `_normalize_parameter` in both `aquarium_measurements.py` and `aquarium_parameter_thresholds.py` currently does `if normalized not in SUPPORTED_PARAMETERS: raise 422`. This becomes a lookup: `if parameter_repo.get_by_slug(normalized) is None: raise 422`. `PARAMETER_RULES`/`THRESHOLD_UNITS`/`THRESHOLD_SANITY_RANGES` are unaffected — they still gate on `normalized_parameter` being one of their own dict keys, since those tables of validation rules are not moving into the DB (see Non-Goals). In practice, a parameter usable end-to-end still needs both: a `parameters` row (identity/existence) and a matching `PARAMETER_RULES` entry (unit/range rules).

**Catalog rows can't be deleted while referenced.** `parameters.slug` FK on both dependent tables uses `ON DELETE RESTRICT` (not `CASCADE`) — deleting a parameter that has existing measurements or thresholds must fail with a clear conflict rather than silently orphaning/cascading away historical data. Alternative considered: `CASCADE` — rejected, since silently deleting a user's measurement history as a side effect of an admin catalog edit is surprising and hard to recover from.

**Catalog CRUD is unauthenticated-shape-compatible with existing conventions but is a global admin-style resource, not owned by a user.** Unlike `Aquarium`/`AquariumMeasurement`, `Parameter` has no `owner_user_id` — it's a shared reference table. Endpoints still sit behind `get_current_user` (no anonymous access, consistent with the rest of the API) but are not ownership-scoped. Alternative considered: leaving catalog management to direct DB/migration edits only (no API) — rejected because the proposal explicitly asks for CRUD endpoints.

**Seeding is a data migration, not application startup logic.** The 10 existing parameters are inserted via an Alembic `op.bulk_insert` in the same migration (or an immediately-following one) that creates the `parameters` table and adds the FK constraints, executed before the FK constraints are added, so existing measurement/threshold rows resolve cleanly. Alternative considered: seeding lazily from `PARAMETER_RULES` at app startup — rejected because it would make schema state depend on which code version last booted against a given DB, instead of being a deterministic, reviewable migration step.

## Risks / Trade-offs

- [Adding a parameter via the new CRUD API does not make it usable for measurements/thresholds unless `PARAMETER_RULES`/`THRESHOLD_UNITS`/`THRESHOLD_SANITY_RANGES` also gain a matching code entry — a client could create a catalog row for a parameter that then 422s on every measurement/threshold write because no rule exists.] → Document this clearly in the API description; this change intentionally scopes the catalog to identity/metadata only (see Non-Goals) and is a deliberate trade-off to avoid redesigning the validation-rules system in the same change.
- [Adding the FK constraint to existing `aquarium_measurements`/`aquarium_parameter_thresholds` tables fails if any existing row has a `parameter` value outside the seeded 10 (e.g. stale/manually-inserted data).] → Migration seeds the catalog first, then adds the FK; if it fails, this surfaces as a migration error in `task db-migrate`, not silent data loss. Current hardcoded set matches the seed list exactly, so no pre-existing data is expected to violate it.
- [`ON DELETE RESTRICT` means a parameter can never be removed from the catalog once any measurement/threshold references it — effectively permanent once used.] → Acceptable for v1 given the small, curated parameter set; deletion is realistically only needed for catalog rows created by mistake before any data references them.

## Migration Plan

1. Alembic migration: create `parameters` table (`id`, `slug` unique not-null, `display_name`, `description`, `created_at`, `updated_at`).
2. Same or immediately-following migration: bulk-insert the 10 existing parameters (slug/display name/description derived from current `PARAMETER_RULES` keys and canonical units).
3. Same or immediately-following migration: add FK constraint `aquarium_measurements.parameter -> parameters.slug` and `aquarium_parameter_thresholds.parameter -> parameters.slug`, `ON DELETE RESTRICT`.
4. Application code changes (`Parameter` model, `ParameterRepository`, `parameters.py` router, wiring in `app.py`, validation switch in the two existing resource modules) ship in the same deploy as the migration — there is no intermediate state where code expects the FK but the migration hasn't run, since `task server`/`task db-migrate` runs migrations before serving.
5. Rollback: Alembic downgrade drops the FK constraints, then the seed data, then the `parameters` table; application code would need to roll back in lockstep since the validation switch depends on `ParameterRepository`/the table existing.

## Open Questions

None outstanding. Resolved: seeded parameters are not special-cased — `display_name`/`description` are editable via `PATCH /parameters/{slug}` for seeded and user-created rows alike, with no "system" flag or protection tier. Deletion is blocked whenever a parameter is still referenced by `aquarium_measurements` (or `aquarium_parameter_thresholds`, via the same `ON DELETE RESTRICT` FK) — this applies uniformly to seeded and user-created parameters, not just seeded ones.
