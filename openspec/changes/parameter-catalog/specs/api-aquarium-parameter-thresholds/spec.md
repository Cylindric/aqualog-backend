## MODIFIED Requirements

### Requirement: Threshold routes are parameterized by path
The system SHALL expose authenticated threshold read and set operations at `/aquariums/{aquarium_id}/thresholds/{parameter}` for threshold parameters that exist in the parameter catalog and have a defined threshold rule in application code.

#### Scenario: Set thresholds uses parameterized path
- **WHEN** an authenticated user submits a threshold set request to `PUT /aquariums/{aquarium_id}/thresholds/{parameter}` with a supported parameter value
- **THEN** the system uses the `{parameter}` path segment as the threshold parameter selector for validation and persistence

#### Scenario: Retrieve thresholds uses parameterized path
- **WHEN** an authenticated user submits a request to `GET /aquariums/{aquarium_id}/thresholds/{parameter}` with a supported parameter value
- **THEN** the system returns the threshold values stored for that aquarium and parameter

#### Scenario: Unsupported threshold parameter is rejected
- **WHEN** an authenticated user submits a threshold request to `/aquariums/{aquarium_id}/thresholds/{parameter}` with a parameter value that does not exist in the parameter catalog or has no defined threshold rule in application code
- **THEN** the system rejects the request with a validation error and does not create or expose threshold data

#### Scenario: Mixed-case path parameter aliases are normalized
- **WHEN** an authenticated user submits a threshold request with a supported parameter alias using mixed case (for example `Temperature` or `SALINITY`)
- **THEN** the system normalizes `{parameter}` to lowercase before validation and processing

### Requirement: Threshold parameter values reference the parameter catalog
The system SHALL persist each `AquariumParameterThreshold.parameter` value as a reference to an existing `slug` in the parameter catalog, enforced by a database foreign key constraint.

#### Scenario: Threshold parameter must exist in the catalog
- **WHEN** an authenticated user submits a threshold set request for a `{parameter}` value that has no corresponding record in the parameter catalog
- **THEN** the system rejects the request before persistence and does not create a threshold referencing a non-existent parameter

#### Scenario: Deleting a referenced parameter from the catalog is blocked
- **WHEN** a parameter catalog record has at least one existing `AquariumParameterThreshold` referencing its slug
- **THEN** the system rejects deletion of that parameter catalog record and the existing threshold data remains intact and queryable
