## ADDED Requirements

### Requirement: Measurement unit values reference the unit catalog
The system SHALL persist each `AquariumMeasurement.unit` and `AquariumMeasurement.raw_unit` value as a reference to an existing unit catalog record (`unit_id`, `raw_unit_id`), enforced by a database foreign key constraint, and SHALL further require that the referenced unit is associated with the measurement's parameter via `parameter_units`.

#### Scenario: Measurement unit must exist in the catalog
- **WHEN** an authenticated user submits a measurement create request with a `unit` value that has no corresponding record (matched against the catalog's `unit` notation) in the unit catalog
- **THEN** the system rejects the request before persistence with a validation error and does not create a measurement referencing a non-existent unit

#### Scenario: Measurement unit must be valid for the requested parameter
- **WHEN** an authenticated user submits a measurement create request with a `unit` value that exists in the unit catalog but has no `parameter_units` association with the requested parameter
- **THEN** the system rejects the request with a validation error and does not persist a measurement

#### Scenario: Unit support is driven by the catalog tables, not a fixed code list
- **WHEN** a new unit is added to the unit catalog and associated with a parameter via `parameter_units`, without an application code change
- **THEN** the system accepts measurement create requests using that unit for that parameter

#### Scenario: Deleting a unit referenced by a measurement is blocked
- **WHEN** a unit catalog record has at least one existing `AquariumMeasurement` referencing it as its stored or raw unit
- **THEN** the system rejects deletion of that unit catalog record and the existing measurement data remains intact and queryable

### Requirement: Measurement API continues to accept and return unit notation strings, not identifiers or URL-safe slugs
The system SHALL accept `unit` as a unit-catalog **notation** string (the catalog's `unit` field, e.g. `"ppt"`, `"mg/L"`) in measurement create requests and SHALL return `unit` and `raw_unit` as notation strings in measurement responses, never exposing the underlying `unit_id`/`raw_unit_id` database identifiers and never the catalog's URL-safe `slug` (which cannot represent notations containing `/`, e.g. `mg/L`).

#### Scenario: Create request accepts a unit notation string
- **WHEN** an authenticated user submits a measurement create request with `unit` set to a catalog notation string (for example `"ppt"` or `"mg/L"`)
- **THEN** the system resolves the notation to the corresponding unit catalog record for validation and storage, without requiring the client to supply a unit identifier or URL-safe slug

#### Scenario: Response echoes unit as a notation string
- **WHEN** an authenticated user retrieves a persisted measurement
- **THEN** the response's `unit` and `raw_unit` fields contain the unit catalog's `unit` notation string, in its original catalog casing (e.g. `"mg/L"`, not `"mg_l"`), not a numeric or UUID identifier
