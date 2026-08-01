## ADDED Requirements

### Requirement: Parameter catalog is exposed as a CRUD resource
The system SHALL provide an authenticated CRUD API for the parameter catalog at `/parameters`, where each parameter record has a unique `slug`, a `display_name`, and a `description`.

#### Scenario: List all parameters
- **WHEN** an authenticated user requests `GET /parameters`
- **THEN** the system returns all parameter catalog records with their `slug`, `display_name`, and `description`

#### Scenario: Retrieve a single parameter by slug
- **WHEN** an authenticated user requests `GET /parameters/{slug}` for a slug that exists in the catalog
- **THEN** the system returns that parameter's `slug`, `display_name`, and `description`

#### Scenario: Retrieve a non-existent parameter
- **WHEN** an authenticated user requests `GET /parameters/{slug}` for a slug that does not exist in the catalog
- **THEN** the system returns a not-found result

#### Scenario: Create a new parameter
- **WHEN** an authenticated user submits a valid `slug`, `display_name`, and `description` to `POST /parameters`
- **THEN** the system persists a new parameter catalog record and returns it

#### Scenario: Update an existing parameter
- **WHEN** an authenticated user submits updated `display_name` and/or `description` values to `PATCH /parameters/{slug}` for a slug that exists in the catalog
- **THEN** the system persists the updated fields and returns the updated parameter record

#### Scenario: Delete a parameter
- **WHEN** an authenticated user requests `DELETE /parameters/{slug}` for a parameter that has no measurements or thresholds referencing it
- **THEN** the system removes the parameter catalog record and indicates successful deletion

### Requirement: Parameter slugs are unique, immutable, and normalized
The system SHALL enforce that every parameter's `slug` is unique across the catalog. The `slug` SHALL be normalized to trimmed lowercase before validation and persistence, and SHALL NOT be changeable after creation.

#### Scenario: Duplicate slug on create is rejected
- **WHEN** an authenticated user submits a `POST /parameters` request with a `slug` that already exists in the catalog
- **THEN** the system rejects the request with a conflict or validation error and does not create a duplicate parameter

#### Scenario: Slug casing and whitespace are normalized
- **WHEN** an authenticated user submits a `slug` with mixed case or leading/trailing whitespace (for example ` Salinity `)
- **THEN** the system normalizes the slug to trimmed lowercase (`salinity`) before validation and persistence

#### Scenario: Slug cannot be changed on update
- **WHEN** an authenticated user submits a `PATCH /parameters/{slug}` request that includes a different `slug` value
- **THEN** the system rejects the request with a validation error and does not change the parameter's identity

### Requirement: Required parameter fields are validated
The system SHALL require `slug` and `display_name` on parameter creation and MUST reject requests missing them or containing empty/whitespace-only values.

#### Scenario: Missing required fields on create are rejected
- **WHEN** an authenticated user submits a `POST /parameters` request missing `slug` or `display_name`
- **THEN** the system rejects the request with a validation error and does not persist a parameter

#### Scenario: Empty or whitespace-only required fields are rejected
- **WHEN** an authenticated user submits a `slug` or `display_name` that is empty or contains only whitespace
- **THEN** the system rejects the request with a validation error and does not persist a parameter

### Requirement: Parameters referenced by measurements or thresholds cannot be deleted
The system SHALL prevent deletion of a parameter catalog record while any `AquariumMeasurement` or `AquariumParameterThreshold` record references its slug.

#### Scenario: Deleting a referenced parameter is rejected
- **WHEN** an authenticated user requests `DELETE /parameters/{slug}` for a parameter that has at least one measurement or threshold record referencing it
- **THEN** the system rejects the request with a conflict error and does not delete the parameter catalog record or any dependent data

### Requirement: Parameter catalog seed data matches previously hardcoded parameters
The system SHALL ship with the parameter catalog pre-populated with the parameters previously hardcoded in application code: `salinity`, `phosphate`, `temperature`, `calcium`, `ammonia`, `nitrite`, `nitrate`, `ph`, `alkalinity`, and `magnesium`.

#### Scenario: Seeded parameters are present after migration
- **WHEN** the parameter catalog migration has been applied
- **THEN** `GET /parameters` returns a record for each of the 10 previously hardcoded parameter slugs
