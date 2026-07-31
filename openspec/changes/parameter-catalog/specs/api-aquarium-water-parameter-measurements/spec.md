## MODIFIED Requirements

### Requirement: Measurement routes are parameterized by path
The system SHALL expose canonical authenticated measurement create and retrieval operations at `/aquariums/{aquarium_id}/measurements/{parameter}` for parameters that exist in the parameter catalog.

#### Scenario: Create measurement uses parameterized path
- **WHEN** an authenticated user submits a measurement create request to `/aquariums/{aquarium_id}/measurements/{parameter}` with a parameter value that exists in the parameter catalog
- **THEN** the system uses the `{parameter}` path segment as the measurement parameter selector for validation and persistence

#### Scenario: Retrieve measurement history uses parameterized path
- **WHEN** an authenticated user submits a history request to `/aquariums/{aquarium_id}/measurements/{parameter}` with a parameter value that exists in the parameter catalog
- **THEN** the system returns only history entries matching the requested path parameter

#### Scenario: Unsupported path parameter is rejected
- **WHEN** an authenticated user submits create or history requests to `/aquariums/{aquarium_id}/measurements/{parameter}` with a parameter value that does not exist in the parameter catalog
- **THEN** the system rejects the request with a validation error and does not create or expose measurement data

#### Scenario: Mixed-case path parameter aliases are normalized
- **WHEN** an authenticated user submits create or history requests with a parameter catalog slug using mixed case in `{parameter}` (for example `Salinity` or `PHOSPHATE`)
- **THEN** the system normalizes `{parameter}` to lowercase before validation and processing, and applies behavior for the normalized parameter catalog entry

#### Scenario: Parameter support is driven by the catalog table, not a fixed code list
- **WHEN** a new parameter slug is added to the parameter catalog and a matching measurement validation rule exists in application code
- **THEN** the system accepts measurement create and retrieval requests for that parameter's path segment without requiring a code change to the set of recognized parameter slugs

### Requirement: Measurement parameter values reference the parameter catalog
The system SHALL persist each `AquariumMeasurement.parameter` value as a reference to an existing `slug` in the parameter catalog, enforced by a database foreign key constraint.

#### Scenario: Measurement parameter must exist in the catalog
- **WHEN** an authenticated user submits a measurement create request for a `{parameter}` value that has no corresponding record in the parameter catalog
- **THEN** the system rejects the request before persistence and does not create a measurement referencing a non-existent parameter

#### Scenario: Deleting a referenced parameter from the catalog is blocked
- **WHEN** a parameter catalog record has at least one existing `AquariumMeasurement` referencing its slug
- **THEN** the system rejects deletion of that parameter catalog record and the existing measurement data remains intact and queryable
