# api-unit-catalog Specification

## Purpose
Define authenticated CRUD API behavior for the unit catalog — the source-of-truth table of measurement unit notations (e.g. `ppt`, `mg/L`, `pH`) referenced by aquarium measurements and their parameter associations, including slug derivation, validation, and deletion-guard semantics.

## Requirements

### Requirement: Unit catalog is exposed as a CRUD resource
The system SHALL provide an authenticated CRUD API for the unit catalog at `/units`, where each unit record has a `unit` notation, a derived `slug`, a `display_name`, and an optional `description`.

#### Scenario: List all units
- **WHEN** an authenticated user requests `GET /units`
- **THEN** the system returns all unit catalog records with their `slug`, `unit`, `display_name`, and `description`

#### Scenario: Retrieve a single unit by slug
- **WHEN** an authenticated user requests `GET /units/{slug}` for a slug that exists in the catalog
- **THEN** the system returns that unit's `slug`, `unit`, `display_name`, and `description`

#### Scenario: Retrieve a non-existent unit
- **WHEN** an authenticated user requests `GET /units/{slug}` for a slug that does not exist in the catalog
- **THEN** the system returns a not-found result

#### Scenario: Create a new unit
- **WHEN** an authenticated user submits a valid `unit` and `display_name` (and optional `description`) to `POST /units`
- **THEN** the system persists a new unit catalog record, deriving `slug` from `unit`, and returns it

#### Scenario: Update an existing unit
- **WHEN** an authenticated user submits updated `display_name` and/or `description` values to `PATCH /units/{slug}` for a slug that exists in the catalog
- **THEN** the system persists the updated fields and returns the updated unit record

#### Scenario: Delete a unit
- **WHEN** an authenticated user requests `DELETE /units/{slug}` for a unit that has no measurements referencing it and no parameter associations
- **THEN** the system removes the unit catalog record and indicates successful deletion

### Requirement: Unit slugs are URL-safe, unique, and derived from the unit notation
The system SHALL derive each unit's `slug` from its `unit` notation by lowercasing it and replacing every `/` character with `_`, so the `slug` never contains a `/` and is safe as a single URL path segment. The system SHALL enforce that every unit's derived `slug` is unique across the catalog. Both `unit` and `slug` SHALL NOT be changeable after creation.

#### Scenario: Slug is derived from the unit notation
- **WHEN** an authenticated user submits `unit: "mg/L"` to `POST /units`
- **THEN** the system persists and returns the record with `slug: "mg_l"` and `unit: "mg/L"`

#### Scenario: Units that would derive a duplicate slug are rejected
- **WHEN** an authenticated user submits a `POST /units` request with a `unit` value that derives a `slug` already present in the catalog (for example submitting `unit: "PH"` when a unit with `unit: "pH"` — both deriving `slug: "ph"` — already exists)
- **THEN** the system rejects the request with a conflict or validation error and does not create a duplicate unit

#### Scenario: Whitespace is trimmed from unit before deriving the slug
- **WHEN** an authenticated user submits a `unit` value with leading or trailing whitespace (for example ` pH `)
- **THEN** the system trims the whitespace, persists `unit: "pH"`, and derives `slug: "ph"`

#### Scenario: Slug lookups use the exact derived form
- **WHEN** an authenticated user requests `GET /units/{slug}` using the unit's derived slug (for example `ph`)
- **THEN** the system returns the matching unit catalog record

#### Scenario: Neither slug nor unit can be changed on update
- **WHEN** an authenticated user submits a `PATCH /units/{slug}` request that includes a `slug` or `unit` field
- **THEN** the system rejects the request with a validation error and does not change the unit's identity

### Requirement: Required unit fields are validated
The system SHALL require `unit` and `display_name` on unit creation and MUST reject requests missing them or containing empty/whitespace-only values.

#### Scenario: Missing required fields on create are rejected
- **WHEN** an authenticated user submits a `POST /units` request missing `unit` or `display_name`
- **THEN** the system rejects the request with a validation error and does not persist a unit

#### Scenario: Empty or whitespace-only required fields are rejected
- **WHEN** an authenticated user submits a `unit` or `display_name` that is empty or contains only whitespace
- **THEN** the system rejects the request with a validation error and does not persist a unit

### Requirement: Units referenced by measurements or parameters cannot be deleted
The system SHALL prevent deletion of a unit catalog record while any `AquariumMeasurement` references it (as `unit_id` or `raw_unit_id`) or any `parameter_units` association references it.

#### Scenario: Deleting a unit referenced by a measurement is rejected
- **WHEN** an authenticated user requests `DELETE /units/{slug}` for a unit that has at least one measurement record referencing it as its stored or raw unit
- **THEN** the system rejects the request with a conflict error and does not delete the unit catalog record or any dependent data

#### Scenario: Deleting a unit referenced by a parameter association is rejected
- **WHEN** an authenticated user requests `DELETE /units/{slug}` for a unit that is associated with at least one parameter via `parameter_units`
- **THEN** the system rejects the request with a conflict error and does not delete the unit catalog record or the association

### Requirement: Parameters declare their supported units via a many-to-many association
The system SHALL record, for each parameter, the set of units valid for that parameter and which one is its canonical (stored) unit, via a `parameter_units` association between the parameter catalog and the unit catalog.

#### Scenario: Parameter's supported units are listed
- **WHEN** an authenticated user requests the unit associations for a parameter that exists in the catalog
- **THEN** the system returns the set of units valid for that parameter, indicating which one is canonical

#### Scenario: Exactly one canonical unit per parameter
- **WHEN** a parameter has one or more associated units
- **THEN** at most one of those associations is marked canonical for that parameter

#### Scenario: Unit validity for measurements is driven by the association table, not a fixed code list
- **WHEN** a new unit is added to the unit catalog and associated with a parameter via `parameter_units`, without an application code change
- **THEN** the system accepts that unit's notation for measurement create requests against that parameter

### Requirement: Unit catalog seed data matches previously hardcoded units
The system SHALL ship with the unit catalog pre-populated with the unit notations previously hardcoded in application code: `ppt`, `sg`, `celsius`, `fahrenheit`, `ppm`, `mg/L`, `pH`, `dKH`, `L`, and `gal_us`; and with `parameter_units` pre-populated to match each parameter's previously hardcoded supported units and canonical unit.

#### Scenario: Seeded units are present after migration
- **WHEN** the unit catalog migration has been applied
- **THEN** `GET /units` returns a record for each of the previously hardcoded unit notations, with `unit` preserving the original notation and `slug` holding its derived URL-safe form

#### Scenario: Seeded parameter-unit associations match previous validation behavior
- **WHEN** the unit catalog migration has been applied
- **THEN** each parameter's associated units and canonical unit match the parameter's previously hardcoded `SUPPORTED_*_UNITS` set and canonical unit
