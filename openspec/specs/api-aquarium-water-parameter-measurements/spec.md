# api-aquarium-water-parameter-measurements Specification

## Purpose
Define authenticated API behavior for recording and retrieving aquarium water parameter measurements, including salinity validation, normalization, ownership scoping, and history retrieval semantics.

## Requirements

### Requirement: Users can record salinity measurements for owned aquariums
The system SHALL provide an authenticated operation to record a salinity measurement for an aquarium owned by the requesting user.

#### Scenario: Record salinity measurement for owned aquarium
- **WHEN** an authenticated user submits a valid salinity value and timestamp for an aquarium they own
- **THEN** the system persists the salinity measurement associated with that aquarium and user

#### Scenario: Recording measurement for non-owned aquarium is rejected
- **WHEN** an authenticated user submits a salinity measurement for an aquarium owned by another user
- **THEN** the system rejects the request with a not-found or unauthorized result and does not persist a measurement

### Requirement: Salinity measurement payload is validated and normalized
The system SHALL validate salinity measurement payloads and MUST reject malformed or out-of-range values before persistence.

#### Scenario: Missing required salinity fields are rejected
- **WHEN** an authenticated user submits a salinity measurement request missing required fields (`value`, `unit`, or `measured_at`)
- **THEN** the system rejects the request with a validation error and does not persist a measurement

#### Scenario: Unsupported salinity unit is rejected
- **WHEN** an authenticated user submits a salinity measurement with a unit other than `ppt` or `sg`
- **THEN** the system rejects the request with a validation error and does not persist a measurement

#### Scenario: Invalid salinity value is rejected
- **WHEN** an authenticated user submits a salinity measurement with a non-numeric or out-of-range value
- **THEN** the system rejects the request with a validation error and does not persist a measurement

#### Scenario: Accepted salinity units are converted to canonical ppt storage
- **WHEN** an authenticated user submits a valid salinity measurement in `ppt` or `sg`
- **THEN** the system converts and persists the measurement value in canonical `ppt` units

#### Scenario: Original entered value and unit are preserved
- **WHEN** an authenticated user submits a valid salinity measurement in `ppt` or `sg`
- **THEN** the system persists additional fields containing the original entered value and unit without conversion

#### Scenario: Measurement timestamp is rounded down to whole-second resolution
- **WHEN** an authenticated user submits a salinity measurement with sub-second `measured_at` precision
- **THEN** the system truncates the timestamp to the nearest lower whole second before persistence

### Requirement: Duplicate salinity readings at the same timestamp are not allowed
The system SHALL prevent duplicate salinity records for the same aquarium and normalized measurement timestamp.

#### Scenario: Duplicate reading at same aquarium and second is rejected
- **WHEN** an authenticated user submits a salinity reading for an aquarium where a `salinity` reading already exists at the same normalized `measured_at` second
- **THEN** the system rejects the request with a conflict or validation error and does not create a duplicate record

### Requirement: Users can retrieve salinity measurement history for graphing
The system SHALL provide an authenticated operation to retrieve historical salinity measurements for a user-owned aquarium in chronological order for graph rendering.

#### Scenario: Measurement history is returned in chronological order
- **WHEN** an authenticated user requests salinity measurement history for an owned aquarium
- **THEN** the system returns the measurements sorted by measurement timestamp in ascending order

#### Scenario: Measurement history supports graph-friendly time filtering
- **WHEN** an authenticated user requests salinity measurement history with an optional time window filter
- **THEN** the system returns only measurements within the requested time window

#### Scenario: History retrieval does not require server pagination in v1
- **WHEN** an authenticated user requests salinity measurement history for an owned aquarium
- **THEN** the system returns the full filtered result set without server pagination metadata or page parameters

#### Scenario: Measurement history for non-owned aquarium is not accessible
- **WHEN** an authenticated user requests salinity measurement history for an aquarium owned by another user
- **THEN** the system returns a not-found or unauthorized result and does not expose measurement data

### Requirement: Salinity measurements include canonical and raw fields
The system SHALL store and return salinity measurements with fields required for graphing: parameter name, canonical value, canonical unit, and measurement timestamp. Stored and returned canonical salinity units SHALL be `ppt`. The system SHALL additionally store and return the original entered value and entered unit.

#### Scenario: Persisted measurement stores graph-required fields
- **WHEN** an authenticated user records a valid salinity measurement
- **THEN** the persisted record includes parameter `salinity`, numeric value in `ppt`, unit `ppt`, and measurement timestamp

#### Scenario: Persisted measurement stores raw entered fields
- **WHEN** an authenticated user records a valid salinity measurement
- **THEN** the persisted record includes the original entered numeric value and original entered unit as additional fields

#### Scenario: Retrieved measurement includes graph-required fields
- **WHEN** an authenticated user retrieves salinity measurement history
- **THEN** each returned measurement item includes parameter `salinity`, numeric value in `ppt`, unit `ppt`, and measurement timestamp

#### Scenario: Retrieved measurement includes raw entered fields
- **WHEN** an authenticated user retrieves salinity measurement history
- **THEN** each returned measurement item includes the original entered numeric value and original entered unit in addition to canonical fields

### Requirement: Users can record phosphate measurements for owned aquariums
The system SHALL provide an authenticated operation to record a phosphate measurement for an aquarium owned by the requesting user.

#### Scenario: Record phosphate measurement for owned aquarium
- **WHEN** an authenticated user submits a valid phosphate value, unit, and timestamp for an aquarium they own
- **THEN** the system persists the phosphate measurement associated with that aquarium and user

#### Scenario: Recording phosphate measurement for non-owned aquarium is rejected
- **WHEN** an authenticated user submits a phosphate measurement for an aquarium owned by another user
- **THEN** the system rejects the request with a not-found or unauthorized result and does not persist a measurement

### Requirement: Phosphate measurement payload is validated and normalized
The system SHALL validate phosphate payloads and MUST reject malformed or out-of-range values before persistence.

#### Scenario: Missing required phosphate fields are rejected
- **WHEN** an authenticated user submits a phosphate measurement request missing required fields (`value`, `unit`, or `measured_at`)
- **THEN** the system rejects the request with a validation error and does not persist a measurement

#### Scenario: Unsupported phosphate unit is rejected
- **WHEN** an authenticated user submits a phosphate measurement with a unit other than `ppm`
- **THEN** the system rejects the request with a validation error and does not persist a measurement

#### Scenario: Invalid phosphate value is rejected
- **WHEN** an authenticated user submits a phosphate measurement with a non-numeric or out-of-range value
- **THEN** the system rejects the request with a validation error and does not persist a measurement

#### Scenario: Valid phosphate values are stored in canonical unit
- **WHEN** an authenticated user submits a valid phosphate measurement in `ppm`
- **THEN** the system persists the measurement value in canonical `ppm` units

#### Scenario: Parameter name casing is normalized before persistence
- **WHEN** an authenticated user submits a phosphate measurement using any synonymous casing of the parameter name (for example `Phosphate` or `PHOSPHATE`)
- **THEN** the system normalizes the parameter name to lowercase `phosphate` before persistence

#### Scenario: Whitespace-padded parameter name is trimmed before persistence
- **WHEN** an authenticated user submits a phosphate measurement with leading or trailing whitespace in the parameter name (for example ` phosphate `)
- **THEN** the system trims the whitespace and persists the normalized lowercase parameter name `phosphate`

#### Scenario: Phosphate timestamp is rounded down to whole-second resolution
- **WHEN** an authenticated user submits a phosphate measurement with sub-second `measured_at` precision
- **THEN** the system truncates the timestamp to the nearest lower whole second before persistence

### Requirement: Duplicate phosphate readings at the same timestamp are not allowed
The system SHALL prevent duplicate phosphate records for the same aquarium and normalized measurement timestamp.

#### Scenario: Duplicate phosphate reading at same aquarium and second is rejected
- **WHEN** an authenticated user submits a phosphate reading for an aquarium where a `phosphate` reading already exists at the same normalized `measured_at` second
- **THEN** the system rejects the request with a conflict or validation error and does not create a duplicate record

### Requirement: Users can retrieve phosphate measurement history for graphing
The system SHALL provide an authenticated operation to retrieve historical phosphate measurements for a user-owned aquarium in chronological order for graph rendering.

#### Scenario: Phosphate history is returned in chronological order
- **WHEN** an authenticated user requests phosphate measurement history for an owned aquarium
- **THEN** the system returns the measurements sorted by measurement timestamp in ascending order

#### Scenario: Phosphate history supports graph-friendly time filtering
- **WHEN** an authenticated user requests phosphate measurement history with an optional time window filter
- **THEN** the system returns only phosphate measurements within the requested time window

#### Scenario: History retrieval supports parameter filtering
- **WHEN** an authenticated user requests measurement history with a `parameter` filter set to `phosphate`
- **THEN** the system returns only measurements matching the requested parameter

#### Scenario: History retrieval without parameter filter returns all results
- **WHEN** an authenticated user requests measurement history without a `parameter` filter
- **THEN** the system returns all matching measurements for the aquarium within any provided time window

#### Scenario: History retrieval accepts only a single parameter filter
- **WHEN** an authenticated user requests measurement history with more than one parameter value in the filter
- **THEN** the system rejects the request with a validation error

#### Scenario: Phosphate history for non-owned aquarium is not accessible
- **WHEN** an authenticated user requests phosphate measurement history for an aquarium owned by another user
- **THEN** the system returns a not-found or unauthorized result and does not expose measurement data

### Requirement: Phosphate measurements include canonical graph fields
The system SHALL store and return phosphate measurements with fields required for graphing: parameter name, canonical value, canonical unit, and measurement timestamp.

#### Scenario: Persisted phosphate measurement stores graph-required fields
- **WHEN** an authenticated user records a valid phosphate measurement
- **THEN** the persisted record includes parameter `phosphate`, numeric value in `ppm`, unit `ppm`, and measurement timestamp

#### Scenario: Retrieved phosphate measurement includes graph-required fields
- **WHEN** an authenticated user retrieves phosphate measurement history
- **THEN** each returned measurement item includes parameter `phosphate`, numeric value in `ppm`, unit `ppm`, and measurement timestamp
