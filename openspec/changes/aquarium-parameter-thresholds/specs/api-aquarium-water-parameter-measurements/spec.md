## ADDED Requirements

### Requirement: Users can record temperature measurements for owned aquariums
The system SHALL provide an authenticated operation to record a temperature measurement for an aquarium owned by the requesting user using the parameterized endpoint path.

#### Scenario: Record temperature measurement for owned aquarium
- **WHEN** an authenticated user submits a valid temperature value, unit, and timestamp to `POST /aquariums/{aquarium_id}/measurements/temperature` for an aquarium they own
- **THEN** the system persists the temperature measurement associated with that aquarium and user

#### Scenario: Recording temperature measurement for non-owned aquarium is rejected
- **WHEN** an authenticated user submits a temperature measurement to `POST /aquariums/{aquarium_id}/measurements/temperature` for an aquarium owned by another user
- **THEN** the system rejects the request with a not-found or unauthorized result and does not persist a measurement

### Requirement: Temperature measurement payload is validated and normalized
The system SHALL validate temperature measurement payloads and MUST reject malformed or out-of-range values before persistence.

#### Scenario: Missing required temperature fields are rejected
- **WHEN** an authenticated user submits a temperature measurement request missing required fields (`value`, `unit`, or `measured_at`)
- **THEN** the system rejects the request with a validation error and does not persist a measurement

#### Scenario: Unsupported temperature unit is rejected
- **WHEN** an authenticated user submits a temperature measurement with a unit other than `celsius` or `fahrenheit`
- **THEN** the system rejects the request with a validation error and does not persist a measurement

#### Scenario: Invalid temperature value is rejected
- **WHEN** an authenticated user submits a temperature measurement with a non-numeric value or a value outside the accepted sanity range for aquarium temperature
- **THEN** the system rejects the request with a validation error and does not persist a measurement

#### Scenario: Accepted temperature units are converted to canonical celsius storage
- **WHEN** an authenticated user submits a valid temperature measurement in `celsius` or `fahrenheit`
- **THEN** the system converts and persists the measurement value in canonical `celsius` units

#### Scenario: Original entered value and unit are preserved
- **WHEN** an authenticated user submits a valid temperature measurement in `celsius` or `fahrenheit`
- **THEN** the system persists additional fields containing the original entered value and unit without conversion

#### Scenario: Temperature timestamp is rounded down to whole-second resolution
- **WHEN** an authenticated user submits a temperature measurement with sub-second `measured_at` precision
- **THEN** the system truncates the timestamp to the nearest lower whole second before persistence

### Requirement: Duplicate temperature readings at the same timestamp are not allowed
The system SHALL prevent duplicate temperature records for the same aquarium and normalized measurement timestamp.

#### Scenario: Duplicate temperature reading at same aquarium and second is rejected
- **WHEN** an authenticated user submits a temperature reading for an aquarium where a `temperature` reading already exists at the same normalized `measured_at` second
- **THEN** the system rejects the request with a conflict or validation error and does not create a duplicate record

### Requirement: Users can retrieve temperature measurement history for graphing
The system SHALL provide an authenticated operation to retrieve historical temperature measurements for a user-owned aquarium in chronological order for graph rendering using the parameterized endpoint path.

#### Scenario: Temperature history is returned in chronological order
- **WHEN** an authenticated user requests temperature measurement history from `GET /aquariums/{aquarium_id}/measurements/temperature` for an owned aquarium
- **THEN** the system returns the measurements sorted by measurement timestamp in ascending order

#### Scenario: Temperature history supports graph-friendly time filtering
- **WHEN** an authenticated user requests temperature measurement history from `GET /aquariums/{aquarium_id}/measurements/temperature` with an optional time window filter
- **THEN** the system returns only temperature measurements within the requested time window

#### Scenario: History retrieval supports temperature parameter filtering
- **WHEN** an authenticated user requests measurement history with a `parameter` filter set to `temperature`
- **THEN** the system returns only measurements matching the requested parameter

#### Scenario: Temperature history for non-owned aquarium is not accessible
- **WHEN** an authenticated user requests temperature measurement history from `GET /aquariums/{aquarium_id}/measurements/temperature` for an aquarium owned by another user
- **THEN** the system returns a not-found or unauthorized result and does not expose measurement data

### Requirement: Temperature measurements include canonical and raw fields
The system SHALL store and return temperature measurements with fields required for graphing: parameter name, canonical value, canonical unit, and measurement timestamp. Stored and returned canonical temperature units SHALL be `celsius`. The system SHALL additionally store and return the original entered value and entered unit.

#### Scenario: Persisted temperature measurement stores graph-required fields
- **WHEN** an authenticated user records a valid temperature measurement
- **THEN** the persisted record includes parameter `temperature`, numeric value in `celsius`, unit `celsius`, and measurement timestamp

#### Scenario: Persisted temperature measurement stores raw entered fields
- **WHEN** an authenticated user records a valid temperature measurement
- **THEN** the persisted record includes the original entered numeric value and original entered unit as additional fields

#### Scenario: Retrieved temperature measurement includes graph-required fields
- **WHEN** an authenticated user retrieves temperature measurement history
- **THEN** each returned measurement item includes parameter `temperature`, numeric value in `celsius`, unit `celsius`, and measurement timestamp

#### Scenario: Retrieved temperature measurement includes raw entered fields
- **WHEN** an authenticated user retrieves temperature measurement history
- **THEN** each returned measurement item includes the original entered numeric value and original entered unit in addition to canonical fields
