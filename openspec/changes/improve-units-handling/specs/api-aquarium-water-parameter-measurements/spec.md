## ADDED Requirements

### Requirement: Measurement unit values reference the unit catalog
The system SHALL persist each `AquariumMeasurement.unit` and `AquariumMeasurement.raw_unit` value as a reference to an existing `slug` in the unit catalog (`unit_id`, `raw_unit_id`), enforced by a database foreign key constraint, and SHALL further require that the referenced unit is associated with the measurement's parameter via `parameter_units`.

#### Scenario: Measurement unit must exist in the catalog
- **WHEN** an authenticated user submits a measurement create request with a `unit` value that has no corresponding record in the unit catalog
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

### Requirement: Measurement API continues to accept and return unit slugs, not identifiers
The system SHALL accept `unit` as a slug string in measurement create requests and SHALL return `unit` and `raw_unit` as slug strings in measurement responses, never exposing the underlying `unit_id`/`raw_unit_id` database identifiers.

#### Scenario: Create request accepts a unit slug
- **WHEN** an authenticated user submits a measurement create request with `unit` set to a catalog slug string (for example `"ppt"`)
- **THEN** the system resolves the slug to the corresponding unit catalog record for validation and storage, without requiring the client to supply a unit identifier

#### Scenario: Response echoes unit as a slug string
- **WHEN** an authenticated user retrieves a persisted measurement
- **THEN** the response's `unit` and `raw_unit` fields contain the unit catalog `slug` string, in its original catalog casing, not a numeric or UUID identifier
