# api-aquarium-parameter-thresholds Specification

## Purpose
Define authenticated API behavior for setting and retrieving per-aquarium, per-parameter thresholds (target/min/max), including validation, ownership scoping, and canonical-unit storage semantics.

## Requirements

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

### Requirement: Users can set target/min/max thresholds for owned aquariums
The system SHALL provide an authenticated operation to set `target`, `min`, and `max` threshold values for a supported parameter on an aquarium owned by the requesting user. Each of `target`, `min`, and `max` SHALL be individually optional.

#### Scenario: Set thresholds for owned aquarium succeeds
- **WHEN** an authenticated user submits valid `target`, `min`, and/or `max` values to `PUT /aquariums/{aquarium_id}/thresholds/{parameter}` for an aquarium they own
- **THEN** the system persists the submitted threshold values associated with that aquarium and parameter, and returns the stored thresholds

#### Scenario: Partial thresholds are accepted
- **WHEN** an authenticated user submits only one or two of `target`, `min`, or `max` for a supported parameter
- **THEN** the system persists only the submitted fields and leaves the remaining fields unset

#### Scenario: Setting thresholds for a non-owned aquarium is rejected
- **WHEN** an authenticated user submits a threshold set request for an aquarium owned by another user
- **THEN** the system rejects the request with a not-found or unauthorized result and does not persist threshold data

#### Scenario: Setting thresholds again replaces the previous values
- **WHEN** an authenticated user submits a new threshold set request for a parameter that already has stored thresholds on that aquarium
- **THEN** the system replaces the previously stored `target`, `min`, and `max` values with the newly submitted values rather than creating a duplicate record

### Requirement: Threshold values are validated for internal consistency and parameter-appropriate range
The system SHALL validate that, when more than one of `target`, `min`, and `max` are provided, `min` is less than or equal to `target` and `target` is less than or equal to `max`. The system SHALL reject non-numeric or out-of-range values for the parameter being configured.

#### Scenario: Inconsistent min/target/max ordering is rejected
- **WHEN** an authenticated user submits threshold values where `min` is greater than `target`, or `target` is greater than `max`, or `min` is greater than `max`
- **THEN** the system rejects the request with a validation error and does not persist the threshold values

#### Scenario: Out-of-range salinity threshold is rejected
- **WHEN** an authenticated user submits a `salinity` threshold value outside the accepted salinity range used for salinity measurements
- **THEN** the system rejects the request with a validation error and does not persist the threshold values

#### Scenario: Out-of-range phosphate threshold is rejected
- **WHEN** an authenticated user submits a `phosphate` threshold value outside the accepted phosphate range used for phosphate measurements
- **THEN** the system rejects the request with a validation error and does not persist the threshold values

#### Scenario: Out-of-range temperature threshold is rejected
- **WHEN** an authenticated user submits a `temperature` threshold value outside the accepted sanity range for aquarium temperature
- **THEN** the system rejects the request with a validation error and does not persist the threshold values

#### Scenario: Non-numeric threshold value is rejected
- **WHEN** an authenticated user submits a non-numeric value for `target`, `min`, or `max`
- **THEN** the system rejects the request with a validation error and does not persist the threshold values

### Requirement: Users can retrieve thresholds for owned aquariums
The system SHALL provide an authenticated operation to retrieve the stored `target`, `min`, and `max` threshold values for a supported parameter on a user-owned aquarium.

#### Scenario: Retrieve stored thresholds
- **WHEN** an authenticated user requests `GET /aquariums/{aquarium_id}/thresholds/{parameter}` for an owned aquarium with previously stored thresholds
- **THEN** the system returns the stored `target`, `min`, and `max` values along with the parameter's canonical unit

#### Scenario: Retrieve thresholds for a parameter with none configured
- **WHEN** an authenticated user requests thresholds for a supported parameter that has no stored threshold record on that aquarium
- **THEN** the system returns a successful response indicating no thresholds are configured, rather than a not-found error

#### Scenario: Retrieving thresholds for a non-owned aquarium is rejected
- **WHEN** an authenticated user requests thresholds for an aquarium owned by another user
- **THEN** the system returns a not-found or unauthorized result and does not expose threshold data

### Requirement: Thresholds are stored and returned in the parameter's canonical unit
The system SHALL store and return threshold values in the same canonical unit used for that parameter's measurements (`ppt` for salinity, `ppm` for phosphate) or a defined canonical unit for parameters without existing measurement support (`celsius` for temperature).

#### Scenario: Persisted threshold includes canonical unit
- **WHEN** an authenticated user sets thresholds for a supported parameter
- **THEN** the persisted and returned threshold record includes the parameter's canonical unit alongside `target`, `min`, and `max`
