# api-aquarium-water-parameter-measurements Specification

## Purpose
Define authenticated API behavior for recording and retrieving aquarium water parameter measurements, including salinity validation, normalization, ownership scoping, and history retrieval semantics.

## Requirements

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

### Requirement: Users can record salinity measurements for owned aquariums
The system SHALL provide an authenticated operation to record a salinity measurement for an aquarium owned by the requesting user using the parameterized endpoint path.

#### Scenario: Record salinity measurement for owned aquarium
- **WHEN** an authenticated user submits a valid salinity value and timestamp to `POST /aquariums/{aquarium_id}/measurements/salinity` for an aquarium they own
- **THEN** the system persists the salinity measurement associated with that aquarium and user

#### Scenario: Recording measurement for non-owned aquarium is rejected
- **WHEN** an authenticated user submits a salinity measurement to `POST /aquariums/{aquarium_id}/measurements/salinity` for an aquarium owned by another user
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
The system SHALL provide an authenticated operation to retrieve historical salinity measurements for a user-owned aquarium in chronological order for graph rendering using the parameterized endpoint path.

#### Scenario: Measurement history is returned in chronological order
- **WHEN** an authenticated user requests salinity measurement history from `GET /aquariums/{aquarium_id}/measurements/salinity` for an owned aquarium
- **THEN** the system returns the measurements sorted by measurement timestamp in ascending order

#### Scenario: Measurement history supports graph-friendly time filtering
- **WHEN** an authenticated user requests salinity measurement history from `GET /aquariums/{aquarium_id}/measurements/salinity` with an optional time window filter
- **THEN** the system returns only measurements within the requested time window

#### Scenario: History retrieval does not require server pagination in v1
- **WHEN** an authenticated user requests salinity measurement history from `GET /aquariums/{aquarium_id}/measurements/salinity` for an owned aquarium
- **THEN** the system returns the full filtered result set without server pagination metadata or page parameters

#### Scenario: Measurement history for non-owned aquarium is not accessible
- **WHEN** an authenticated user requests salinity measurement history from `GET /aquariums/{aquarium_id}/measurements/salinity` for an aquarium owned by another user
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
The system SHALL provide an authenticated operation to record a phosphate measurement for an aquarium owned by the requesting user using the parameterized endpoint path.

#### Scenario: Record phosphate measurement for owned aquarium
- **WHEN** an authenticated user submits a valid phosphate value, unit, and timestamp to `POST /aquariums/{aquarium_id}/measurements/phosphate` for an aquarium they own
- **THEN** the system persists the phosphate measurement associated with that aquarium and user

#### Scenario: Recording phosphate measurement for non-owned aquarium is rejected
- **WHEN** an authenticated user submits a phosphate measurement to `POST /aquariums/{aquarium_id}/measurements/phosphate` for an aquarium owned by another user
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
The system SHALL provide an authenticated operation to retrieve historical phosphate measurements for a user-owned aquarium in chronological order for graph rendering using the parameterized endpoint path.

#### Scenario: Phosphate history is returned in chronological order
- **WHEN** an authenticated user requests phosphate measurement history from `GET /aquariums/{aquarium_id}/measurements/phosphate` for an owned aquarium
- **THEN** the system returns the measurements sorted by measurement timestamp in ascending order

#### Scenario: Phosphate history supports graph-friendly time filtering
- **WHEN** an authenticated user requests phosphate measurement history from `GET /aquariums/{aquarium_id}/measurements/phosphate` with an optional time window filter
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
- **WHEN** an authenticated user requests phosphate measurement history from `GET /aquariums/{aquarium_id}/measurements/phosphate` for an aquarium owned by another user
- **THEN** the system returns a not-found or unauthorized result and does not expose measurement data

### Requirement: Phosphate measurements include canonical graph fields
The system SHALL store and return phosphate measurements with fields required for graphing: parameter name, canonical value, canonical unit, and measurement timestamp.

#### Scenario: Persisted phosphate measurement stores graph-required fields
- **WHEN** an authenticated user records a valid phosphate measurement
- **THEN** the persisted record includes parameter `phosphate`, numeric value in `ppm`, unit `ppm`, and measurement timestamp

#### Scenario: Retrieved phosphate measurement includes graph-required fields
- **WHEN** an authenticated user retrieves phosphate measurement history
- **THEN** each returned measurement item includes parameter `phosphate`, numeric value in `ppm`, unit `ppm`, and measurement timestamp

### Requirement: Users can record calcium measurements for owned aquariums
The system SHALL provide an authenticated operation to record a calcium measurement for an aquarium owned by the requesting user using the parameterized endpoint path.

#### Scenario: Record calcium measurement for owned aquarium
- **WHEN** an authenticated user submits a valid calcium value, unit, and timestamp to `POST /aquariums/{aquarium_id}/measurements/calcium` for an aquarium they own
- **THEN** the system persists the calcium measurement associated with that aquarium and user

#### Scenario: Recording calcium measurement for non-owned aquarium is rejected
- **WHEN** an authenticated user submits a calcium measurement to `POST /aquariums/{aquarium_id}/measurements/calcium` for an aquarium owned by another user
- **THEN** the system rejects the request with a not-found or unauthorized result and does not persist a measurement

### Requirement: Calcium measurement payload is validated and normalized
The system SHALL validate calcium payloads and MUST reject malformed or out-of-range values before persistence.

#### Scenario: Missing required calcium fields are rejected
- **WHEN** an authenticated user submits a calcium measurement request missing required fields (`value`, `unit`, or `measured_at`)
- **THEN** the system rejects the request with a validation error and does not persist a measurement

#### Scenario: Unsupported calcium unit is rejected
- **WHEN** an authenticated user submits a calcium measurement with a unit other than `ppm`
- **THEN** the system rejects the request with a validation error and does not persist a measurement

#### Scenario: Invalid calcium value is rejected
- **WHEN** an authenticated user submits a calcium measurement with a non-numeric or out-of-range value
- **THEN** the system rejects the request with a validation error and does not persist a measurement

#### Scenario: Valid calcium values are stored in canonical unit
- **WHEN** an authenticated user submits a valid calcium measurement in `ppm`
- **THEN** the system persists the measurement value in canonical `ppm` units

#### Scenario: Parameter name casing is normalized before persistence
- **WHEN** an authenticated user submits a calcium measurement using any synonymous casing of the parameter name (for example `Calcium` or `CALCIUM`)
- **THEN** the system normalizes the parameter name to lowercase `calcium` before persistence

#### Scenario: Whitespace-padded parameter name is trimmed before persistence
- **WHEN** an authenticated user submits a calcium measurement with leading or trailing whitespace in the parameter name (for example ` calcium `)
- **THEN** the system trims the whitespace and persists the normalized lowercase parameter name `calcium`

#### Scenario: Calcium timestamp is rounded down to whole-second resolution
- **WHEN** an authenticated user submits a calcium measurement with sub-second `measured_at` precision
- **THEN** the system truncates the timestamp to the nearest lower whole second before persistence

### Requirement: Duplicate calcium readings at the same timestamp are not allowed
The system SHALL prevent duplicate calcium records for the same aquarium and normalized measurement timestamp.

#### Scenario: Duplicate calcium reading at same aquarium and second is rejected
- **WHEN** an authenticated user submits a calcium reading for an aquarium where a `calcium` reading already exists at the same normalized `measured_at` second
- **THEN** the system rejects the request with a conflict or validation error and does not create a duplicate record

### Requirement: Users can retrieve calcium measurement history for graphing
The system SHALL provide an authenticated operation to retrieve historical calcium measurements for a user-owned aquarium in chronological order for graph rendering using the parameterized endpoint path.

#### Scenario: Calcium history is returned in chronological order
- **WHEN** an authenticated user requests calcium measurement history from `GET /aquariums/{aquarium_id}/measurements/calcium` for an owned aquarium
- **THEN** the system returns the measurements sorted by measurement timestamp in ascending order

#### Scenario: Calcium history supports graph-friendly time filtering
- **WHEN** an authenticated user requests calcium measurement history from `GET /aquariums/{aquarium_id}/measurements/calcium` with an optional time window filter
- **THEN** the system returns only calcium measurements within the requested time window

#### Scenario: History retrieval supports parameter filtering
- **WHEN** an authenticated user requests measurement history with a `parameter` filter set to `calcium`
- **THEN** the system returns only measurements matching the requested parameter

#### Scenario: History retrieval without parameter filter returns all results
- **WHEN** an authenticated user requests measurement history without a `parameter` filter
- **THEN** the system returns all matching measurements for the aquarium within any provided time window

#### Scenario: History retrieval accepts only a single parameter filter
- **WHEN** an authenticated user requests measurement history with more than one parameter value in the filter
- **THEN** the system rejects the request with a validation error

#### Scenario: Calcium history for non-owned aquarium is not accessible
- **WHEN** an authenticated user requests calcium measurement history from `GET /aquariums/{aquarium_id}/measurements/calcium` for an aquarium owned by another user
- **THEN** the system returns a not-found or unauthorized result and does not expose measurement data

### Requirement: Calcium measurements include canonical graph fields
The system SHALL store and return calcium measurements with fields required for graphing: parameter name, canonical value, canonical unit, and measurement timestamp.

#### Scenario: Persisted calcium measurement stores graph-required fields
- **WHEN** an authenticated user records a valid calcium measurement
- **THEN** the persisted record includes parameter `calcium`, numeric value in `ppm`, unit `ppm`, and measurement timestamp

#### Scenario: Retrieved calcium measurement includes graph-required fields
- **WHEN** an authenticated user retrieves calcium measurement history
- **THEN** each returned measurement item includes parameter `calcium`, numeric value in `ppm`, unit `ppm`, and measurement timestamp

### Requirement: Users can record ammonia measurements for owned aquariums
The system SHALL provide an authenticated operation to record an ammonia measurement for an aquarium owned by the requesting user using the parameterized endpoint path.

#### Scenario: Record ammonia measurement for owned aquarium
- **WHEN** an authenticated user submits a valid ammonia value, unit, and timestamp to `POST /aquariums/{aquarium_id}/measurements/ammonia` for an aquarium they own
- **THEN** the system persists the ammonia measurement associated with that aquarium and user

#### Scenario: Recording ammonia measurement for non-owned aquarium is rejected
- **WHEN** an authenticated user submits an ammonia measurement to `POST /aquariums/{aquarium_id}/measurements/ammonia` for an aquarium owned by another user
- **THEN** the system rejects the request with a not-found or unauthorized result and does not persist a measurement

### Requirement: Ammonia measurement payload is validated and normalized
The system SHALL validate ammonia payloads and MUST reject malformed or out-of-range values before persistence.

#### Scenario: Missing required ammonia fields are rejected
- **WHEN** an authenticated user submits an ammonia measurement request missing required fields (`value`, `unit`, or `measured_at`)
- **THEN** the system rejects the request with a validation error and does not persist a measurement

#### Scenario: Unsupported ammonia unit is rejected
- **WHEN** an authenticated user submits an ammonia measurement with a unit other than `mg/L`
- **THEN** the system rejects the request with a validation error and does not persist a measurement

#### Scenario: Invalid ammonia value is rejected
- **WHEN** an authenticated user submits an ammonia measurement with a non-numeric or out-of-range value
- **THEN** the system rejects the request with a validation error and does not persist a measurement

#### Scenario: Valid ammonia values are stored in canonical unit
- **WHEN** an authenticated user submits a valid ammonia measurement in `mg/L`
- **THEN** the system persists the measurement value in canonical `mg/L` units

#### Scenario: Parameter name casing is normalized before persistence
- **WHEN** an authenticated user submits an ammonia measurement using any synonymous casing of the parameter name (for example `Ammonia` or `AMMONIA`)
- **THEN** the system normalizes the parameter name to lowercase `ammonia` before persistence

#### Scenario: Whitespace-padded parameter name is trimmed before persistence
- **WHEN** an authenticated user submits an ammonia measurement with leading or trailing whitespace in the parameter name (for example ` ammonia `)
- **THEN** the system trims the whitespace and persists the normalized lowercase parameter name `ammonia`

#### Scenario: Ammonia timestamp is rounded down to whole-second resolution
- **WHEN** an authenticated user submits an ammonia measurement with sub-second `measured_at` precision
- **THEN** the system truncates the timestamp to the nearest lower whole second before persistence

### Requirement: Duplicate ammonia readings at the same timestamp are not allowed
The system SHALL prevent duplicate ammonia records for the same aquarium and normalized measurement timestamp.

#### Scenario: Duplicate ammonia reading at same aquarium and second is rejected
- **WHEN** an authenticated user submits an ammonia reading for an aquarium where an `ammonia` reading already exists at the same normalized `measured_at` second
- **THEN** the system rejects the request with a conflict or validation error and does not create a duplicate record

### Requirement: Users can retrieve ammonia measurement history for graphing
The system SHALL provide an authenticated operation to retrieve historical ammonia measurements for a user-owned aquarium in chronological order for graph rendering using the parameterized endpoint path.

#### Scenario: Ammonia history is returned in chronological order
- **WHEN** an authenticated user requests ammonia measurement history from `GET /aquariums/{aquarium_id}/measurements/ammonia` for an owned aquarium
- **THEN** the system returns the measurements sorted by measurement timestamp in ascending order

#### Scenario: Ammonia history supports graph-friendly time filtering
- **WHEN** an authenticated user requests ammonia measurement history from `GET /aquariums/{aquarium_id}/measurements/ammonia` with an optional time window filter
- **THEN** the system returns only ammonia measurements within the requested time window

#### Scenario: History retrieval supports parameter filtering
- **WHEN** an authenticated user requests measurement history with a `parameter` filter set to `ammonia`
- **THEN** the system returns only measurements matching the requested parameter

#### Scenario: History retrieval without parameter filter returns all results
- **WHEN** an authenticated user requests measurement history without a `parameter` filter
- **THEN** the system returns all matching measurements for the aquarium within any provided time window

#### Scenario: History retrieval accepts only a single parameter filter
- **WHEN** an authenticated user requests measurement history with more than one parameter value in the filter
- **THEN** the system rejects the request with a validation error

#### Scenario: Ammonia history for non-owned aquarium is not accessible
- **WHEN** an authenticated user requests ammonia measurement history from `GET /aquariums/{aquarium_id}/measurements/ammonia` for an aquarium owned by another user
- **THEN** the system returns a not-found or unauthorized result and does not expose measurement data

### Requirement: Ammonia measurements include canonical graph fields
The system SHALL store and return ammonia measurements with fields required for graphing: parameter name, canonical value, canonical unit, and measurement timestamp.

#### Scenario: Persisted ammonia measurement stores graph-required fields
- **WHEN** an authenticated user records a valid ammonia measurement
- **THEN** the persisted record includes parameter `ammonia`, numeric value in `mg/L`, unit `mg/L`, and measurement timestamp

#### Scenario: Retrieved ammonia measurement includes graph-required fields
- **WHEN** an authenticated user retrieves ammonia measurement history
- **THEN** each returned measurement item includes parameter `ammonia`, numeric value in `mg/L`, unit `mg/L`, and measurement timestamp

### Requirement: Users can record nitrite measurements for owned aquariums
The system SHALL provide an authenticated operation to record a nitrite measurement for an aquarium owned by the requesting user using the parameterized endpoint path.

#### Scenario: Record nitrite measurement for owned aquarium
- **WHEN** an authenticated user submits a valid nitrite value, unit, and timestamp to `POST /aquariums/{aquarium_id}/measurements/nitrite` for an aquarium they own
- **THEN** the system persists the nitrite measurement associated with that aquarium and user

#### Scenario: Recording nitrite measurement for non-owned aquarium is rejected
- **WHEN** an authenticated user submits a nitrite measurement to `POST /aquariums/{aquarium_id}/measurements/nitrite` for an aquarium owned by another user
- **THEN** the system rejects the request with a not-found or unauthorized result and does not persist a measurement

### Requirement: Nitrite measurement payload is validated and normalized
The system SHALL validate nitrite payloads and MUST reject malformed or out-of-range values before persistence.

#### Scenario: Missing required nitrite fields are rejected
- **WHEN** an authenticated user submits a nitrite measurement request missing required fields (`value`, `unit`, or `measured_at`)
- **THEN** the system rejects the request with a validation error and does not persist a measurement

#### Scenario: Unsupported nitrite unit is rejected
- **WHEN** an authenticated user submits a nitrite measurement with a unit other than `ppm`
- **THEN** the system rejects the request with a validation error and does not persist a measurement

#### Scenario: Invalid nitrite value is rejected
- **WHEN** an authenticated user submits a nitrite measurement with a non-numeric or out-of-range value
- **THEN** the system rejects the request with a validation error and does not persist a measurement

#### Scenario: Valid nitrite values are stored in canonical unit
- **WHEN** an authenticated user submits a valid nitrite measurement in `ppm`
- **THEN** the system persists the measurement value in canonical `ppm` units

#### Scenario: Parameter name casing is normalized before persistence
- **WHEN** an authenticated user submits a nitrite measurement using any synonymous casing of the parameter name (for example `Nitrite` or `NITRITE`)
- **THEN** the system normalizes the parameter name to lowercase `nitrite` before persistence

#### Scenario: Whitespace-padded parameter name is trimmed before persistence
- **WHEN** an authenticated user submits a nitrite measurement with leading or trailing whitespace in the parameter name (for example ` nitrite `)
- **THEN** the system trims the whitespace and persists the normalized lowercase parameter name `nitrite`

#### Scenario: Nitrite timestamp is rounded down to whole-second resolution
- **WHEN** an authenticated user submits a nitrite measurement with sub-second `measured_at` precision
- **THEN** the system truncates the timestamp to the nearest lower whole second before persistence

### Requirement: Duplicate nitrite readings at the same timestamp are not allowed
The system SHALL prevent duplicate nitrite records for the same aquarium and normalized measurement timestamp.

#### Scenario: Duplicate nitrite reading at same aquarium and second is rejected
- **WHEN** an authenticated user submits a nitrite reading for an aquarium where a `nitrite` reading already exists at the same normalized `measured_at` second
- **THEN** the system rejects the request with a conflict or validation error and does not create a duplicate record

### Requirement: Users can retrieve nitrite measurement history for graphing
The system SHALL provide an authenticated operation to retrieve historical nitrite measurements for a user-owned aquarium in chronological order for graph rendering using the parameterized endpoint path.

#### Scenario: Nitrite history is returned in chronological order
- **WHEN** an authenticated user requests nitrite measurement history from `GET /aquariums/{aquarium_id}/measurements/nitrite` for an owned aquarium
- **THEN** the system returns the measurements sorted by measurement timestamp in ascending order

#### Scenario: Nitrite history supports graph-friendly time filtering
- **WHEN** an authenticated user requests nitrite measurement history from `GET /aquariums/{aquarium_id}/measurements/nitrite` with an optional time window filter
- **THEN** the system returns only nitrite measurements within the requested time window

#### Scenario: History retrieval supports parameter filtering
- **WHEN** an authenticated user requests measurement history with a `parameter` filter set to `nitrite`
- **THEN** the system returns only measurements matching the requested parameter

#### Scenario: History retrieval without parameter filter returns all results
- **WHEN** an authenticated user requests measurement history without a `parameter` filter
- **THEN** the system returns all matching measurements for the aquarium within any provided time window

#### Scenario: History retrieval accepts only a single parameter filter
- **WHEN** an authenticated user requests measurement history with more than one parameter value in the filter
- **THEN** the system rejects the request with a validation error

#### Scenario: Nitrite history for non-owned aquarium is not accessible
- **WHEN** an authenticated user requests nitrite measurement history from `GET /aquariums/{aquarium_id}/measurements/nitrite` for an aquarium owned by another user
- **THEN** the system returns a not-found or unauthorized result and does not expose measurement data

### Requirement: Nitrite measurements include canonical graph fields
The system SHALL store and return nitrite measurements with fields required for graphing: parameter name, canonical value, canonical unit, and measurement timestamp.

#### Scenario: Persisted nitrite measurement stores graph-required fields
- **WHEN** an authenticated user records a valid nitrite measurement
- **THEN** the persisted record includes parameter `nitrite`, numeric value in `ppm`, unit `ppm`, and measurement timestamp

#### Scenario: Retrieved nitrite measurement includes graph-required fields
- **WHEN** an authenticated user retrieves nitrite measurement history
- **THEN** each returned measurement item includes parameter `nitrite`, numeric value in `ppm`, unit `ppm`, and measurement timestamp

### Requirement: Users can record nitrate measurements for owned aquariums
The system SHALL provide an authenticated operation to record a nitrate measurement for an aquarium owned by the requesting user using the parameterized endpoint path.

#### Scenario: Record nitrate measurement for owned aquarium
- **WHEN** an authenticated user submits a valid nitrate value, unit, and timestamp to `POST /aquariums/{aquarium_id}/measurements/nitrate` for an aquarium they own
- **THEN** the system persists the nitrate measurement associated with that aquarium and user

#### Scenario: Recording nitrate measurement for non-owned aquarium is rejected
- **WHEN** an authenticated user submits a nitrate measurement to `POST /aquariums/{aquarium_id}/measurements/nitrate` for an aquarium owned by another user
- **THEN** the system rejects the request with a not-found or unauthorized result and does not persist a measurement

### Requirement: Nitrate measurement payload is validated and normalized
The system SHALL validate nitrate payloads and MUST reject malformed or out-of-range values before persistence.

#### Scenario: Missing required nitrate fields are rejected
- **WHEN** an authenticated user submits a nitrate measurement request missing required fields (`value`, `unit`, or `measured_at`)
- **THEN** the system rejects the request with a validation error and does not persist a measurement

#### Scenario: Unsupported nitrate unit is rejected
- **WHEN** an authenticated user submits a nitrate measurement with a unit other than `ppm`
- **THEN** the system rejects the request with a validation error and does not persist a measurement

#### Scenario: Invalid nitrate value is rejected
- **WHEN** an authenticated user submits a nitrate measurement with a non-numeric or out-of-range value
- **THEN** the system rejects the request with a validation error and does not persist a measurement

#### Scenario: Valid nitrate values are stored in canonical unit
- **WHEN** an authenticated user submits a valid nitrate measurement in `ppm`
- **THEN** the system persists the measurement value in canonical `ppm` units

#### Scenario: Parameter name casing is normalized before persistence
- **WHEN** an authenticated user submits a nitrate measurement using any synonymous casing of the parameter name (for example `Nitrate` or `NITRATE`)
- **THEN** the system normalizes the parameter name to lowercase `nitrate` before persistence

#### Scenario: Whitespace-padded parameter name is trimmed before persistence
- **WHEN** an authenticated user submits a nitrate measurement with leading or trailing whitespace in the parameter name (for example ` nitrate `)
- **THEN** the system trims the whitespace and persists the normalized lowercase parameter name `nitrate`

#### Scenario: Nitrate timestamp is rounded down to whole-second resolution
- **WHEN** an authenticated user submits a nitrate measurement with sub-second `measured_at` precision
- **THEN** the system truncates the timestamp to the nearest lower whole second before persistence

### Requirement: Duplicate nitrate readings at the same timestamp are not allowed
The system SHALL prevent duplicate nitrate records for the same aquarium and normalized measurement timestamp.

#### Scenario: Duplicate nitrate reading at same aquarium and second is rejected
- **WHEN** an authenticated user submits a nitrate reading for an aquarium where a `nitrate` reading already exists at the same normalized `measured_at` second
- **THEN** the system rejects the request with a conflict or validation error and does not create a duplicate record

### Requirement: Users can retrieve nitrate measurement history for graphing
The system SHALL provide an authenticated operation to retrieve historical nitrate measurements for a user-owned aquarium in chronological order for graph rendering using the parameterized endpoint path.

#### Scenario: Nitrate history is returned in chronological order
- **WHEN** an authenticated user requests nitrate measurement history from `GET /aquariums/{aquarium_id}/measurements/nitrate` for an owned aquarium
- **THEN** the system returns the measurements sorted by measurement timestamp in ascending order

#### Scenario: Nitrate history supports graph-friendly time filtering
- **WHEN** an authenticated user requests nitrate measurement history from `GET /aquariums/{aquarium_id}/measurements/nitrate` with an optional time window filter
- **THEN** the system returns only nitrate measurements within the requested time window

#### Scenario: History retrieval supports parameter filtering
- **WHEN** an authenticated user requests measurement history with a `parameter` filter set to `nitrate`
- **THEN** the system returns only measurements matching the requested parameter

#### Scenario: History retrieval without parameter filter returns all results
- **WHEN** an authenticated user requests measurement history without a `parameter` filter
- **THEN** the system returns all matching measurements for the aquarium within any provided time window

#### Scenario: History retrieval accepts only a single parameter filter
- **WHEN** an authenticated user requests measurement history with more than one parameter value in the filter
- **THEN** the system rejects the request with a validation error

#### Scenario: Nitrate history for non-owned aquarium is not accessible
- **WHEN** an authenticated user requests nitrate measurement history from `GET /aquariums/{aquarium_id}/measurements/nitrate` for an aquarium owned by another user
- **THEN** the system returns a not-found or unauthorized result and does not expose measurement data

### Requirement: Nitrate measurements include canonical graph fields
The system SHALL store and return nitrate measurements with fields required for graphing: parameter name, canonical value, canonical unit, and measurement timestamp.

#### Scenario: Persisted nitrate measurement stores graph-required fields
- **WHEN** an authenticated user records a valid nitrate measurement
- **THEN** the persisted record includes parameter `nitrate`, numeric value in `ppm`, unit `ppm`, and measurement timestamp

#### Scenario: Retrieved nitrate measurement includes graph-required fields
- **WHEN** an authenticated user retrieves nitrate measurement history
- **THEN** each returned measurement item includes parameter `nitrate`, numeric value in `ppm`, unit `ppm`, and measurement timestamp

### Requirement: Users can record pH measurements for owned aquariums
The system SHALL provide an authenticated operation to record a pH measurement for an aquarium owned by the requesting user using the parameterized endpoint path.

#### Scenario: Record pH measurement for owned aquarium
- **WHEN** an authenticated user submits a valid pH value, unit, and timestamp to `POST /aquariums/{aquarium_id}/measurements/ph` for an aquarium they own
- **THEN** the system persists the pH measurement associated with that aquarium and user

#### Scenario: Recording pH measurement for non-owned aquarium is rejected
- **WHEN** an authenticated user submits a pH measurement to `POST /aquariums/{aquarium_id}/measurements/ph` for an aquarium owned by another user
- **THEN** the system rejects the request with a not-found or unauthorized result and does not persist a measurement

### Requirement: pH measurement payload is validated and normalized
The system SHALL validate pH payloads and MUST reject malformed or out-of-range values before persistence.

#### Scenario: Missing required pH fields are rejected
- **WHEN** an authenticated user submits a pH measurement request missing required fields (`value`, `unit`, or `measured_at`)
- **THEN** the system rejects the request with a validation error and does not persist a measurement

#### Scenario: Unsupported pH unit is rejected
- **WHEN** an authenticated user submits a pH measurement with a unit other than `pH`
- **THEN** the system rejects the request with a validation error and does not persist a measurement

#### Scenario: Invalid pH value is rejected
- **WHEN** an authenticated user submits a pH measurement with a non-numeric value or a value outside the 0-14 pH scale
- **THEN** the system rejects the request with a validation error and does not persist a measurement

#### Scenario: Valid pH values are stored in canonical unit
- **WHEN** an authenticated user submits a valid pH measurement in `pH`
- **THEN** the system persists the measurement value in canonical `pH` units

#### Scenario: Parameter name casing is normalized before persistence
- **WHEN** an authenticated user submits a pH measurement using any synonymous casing of the parameter name (for example `PH` or `Ph`)
- **THEN** the system normalizes the parameter name to lowercase `ph` before persistence

#### Scenario: Whitespace-padded parameter name is trimmed before persistence
- **WHEN** an authenticated user submits a pH measurement with leading or trailing whitespace in the parameter name (for example ` ph `)
- **THEN** the system trims the whitespace and persists the normalized lowercase parameter name `ph`

#### Scenario: pH timestamp is rounded down to whole-second resolution
- **WHEN** an authenticated user submits a pH measurement with sub-second `measured_at` precision
- **THEN** the system truncates the timestamp to the nearest lower whole second before persistence

### Requirement: Duplicate pH readings at the same timestamp are not allowed
The system SHALL prevent duplicate pH records for the same aquarium and normalized measurement timestamp.

#### Scenario: Duplicate pH reading at same aquarium and second is rejected
- **WHEN** an authenticated user submits a pH reading for an aquarium where a `ph` reading already exists at the same normalized `measured_at` second
- **THEN** the system rejects the request with a conflict or validation error and does not create a duplicate record

### Requirement: Users can retrieve pH measurement history for graphing
The system SHALL provide an authenticated operation to retrieve historical pH measurements for a user-owned aquarium in chronological order for graph rendering using the parameterized endpoint path.

#### Scenario: pH history is returned in chronological order
- **WHEN** an authenticated user requests pH measurement history from `GET /aquariums/{aquarium_id}/measurements/ph` for an owned aquarium
- **THEN** the system returns the measurements sorted by measurement timestamp in ascending order

#### Scenario: pH history supports graph-friendly time filtering
- **WHEN** an authenticated user requests pH measurement history from `GET /aquariums/{aquarium_id}/measurements/ph` with an optional time window filter
- **THEN** the system returns only pH measurements within the requested time window

#### Scenario: History retrieval supports parameter filtering
- **WHEN** an authenticated user requests measurement history with a `parameter` filter set to `ph`
- **THEN** the system returns only measurements matching the requested parameter

#### Scenario: History retrieval without parameter filter returns all results
- **WHEN** an authenticated user requests measurement history without a `parameter` filter
- **THEN** the system returns all matching measurements for the aquarium within any provided time window

#### Scenario: History retrieval accepts only a single parameter filter
- **WHEN** an authenticated user requests measurement history with more than one parameter value in the filter
- **THEN** the system rejects the request with a validation error

#### Scenario: pH history for non-owned aquarium is not accessible
- **WHEN** an authenticated user requests pH measurement history from `GET /aquariums/{aquarium_id}/measurements/ph` for an aquarium owned by another user
- **THEN** the system returns a not-found or unauthorized result and does not expose measurement data

### Requirement: pH measurements include canonical graph fields
The system SHALL store and return pH measurements with fields required for graphing: parameter name, canonical value, canonical unit, and measurement timestamp.

#### Scenario: Persisted pH measurement stores graph-required fields
- **WHEN** an authenticated user records a valid pH measurement
- **THEN** the persisted record includes parameter `ph`, numeric value in `pH`, unit `pH`, and measurement timestamp

#### Scenario: Retrieved pH measurement includes graph-required fields
- **WHEN** an authenticated user retrieves pH measurement history
- **THEN** each returned measurement item includes parameter `ph`, numeric value in `pH`, unit `pH`, and measurement timestamp

### Requirement: Users can record alkalinity measurements for owned aquariums
The system SHALL provide an authenticated operation to record an alkalinity measurement for an aquarium owned by the requesting user using the parameterized endpoint path.

#### Scenario: Record alkalinity measurement for owned aquarium
- **WHEN** an authenticated user submits a valid alkalinity value, unit, and timestamp to `POST /aquariums/{aquarium_id}/measurements/alkalinity` for an aquarium they own
- **THEN** the system persists the alkalinity measurement associated with that aquarium and user

#### Scenario: Recording alkalinity measurement for non-owned aquarium is rejected
- **WHEN** an authenticated user submits an alkalinity measurement to `POST /aquariums/{aquarium_id}/measurements/alkalinity` for an aquarium owned by another user
- **THEN** the system rejects the request with a not-found or unauthorized result and does not persist a measurement

### Requirement: Alkalinity measurement payload is validated and normalized
The system SHALL validate alkalinity payloads and MUST reject malformed or out-of-range values before persistence.

#### Scenario: Missing required alkalinity fields are rejected
- **WHEN** an authenticated user submits an alkalinity measurement request missing required fields (`value`, `unit`, or `measured_at`)
- **THEN** the system rejects the request with a validation error and does not persist a measurement

#### Scenario: Unsupported alkalinity unit is rejected
- **WHEN** an authenticated user submits an alkalinity measurement with a unit other than `dKH`
- **THEN** the system rejects the request with a validation error and does not persist a measurement

#### Scenario: Invalid alkalinity value is rejected
- **WHEN** an authenticated user submits an alkalinity measurement with a non-numeric or out-of-range value
- **THEN** the system rejects the request with a validation error and does not persist a measurement

#### Scenario: Valid alkalinity values are stored in canonical unit
- **WHEN** an authenticated user submits a valid alkalinity measurement in `dKH`
- **THEN** the system persists the measurement value in canonical `dKH` units

#### Scenario: Parameter name casing is normalized before persistence
- **WHEN** an authenticated user submits an alkalinity measurement using any synonymous casing of the parameter name (for example `Alkalinity` or `ALKALINITY`)
- **THEN** the system normalizes the parameter name to lowercase `alkalinity` before persistence

#### Scenario: Whitespace-padded parameter name is trimmed before persistence
- **WHEN** an authenticated user submits an alkalinity measurement with leading or trailing whitespace in the parameter name (for example ` alkalinity `)
- **THEN** the system trims the whitespace and persists the normalized lowercase parameter name `alkalinity`

#### Scenario: Alkalinity timestamp is rounded down to whole-second resolution
- **WHEN** an authenticated user submits an alkalinity measurement with sub-second `measured_at` precision
- **THEN** the system truncates the timestamp to the nearest lower whole second before persistence

### Requirement: Duplicate alkalinity readings at the same timestamp are not allowed
The system SHALL prevent duplicate alkalinity records for the same aquarium and normalized measurement timestamp.

#### Scenario: Duplicate alkalinity reading at same aquarium and second is rejected
- **WHEN** an authenticated user submits an alkalinity reading for an aquarium where an `alkalinity` reading already exists at the same normalized `measured_at` second
- **THEN** the system rejects the request with a conflict or validation error and does not create a duplicate record

### Requirement: Users can retrieve alkalinity measurement history for graphing
The system SHALL provide an authenticated operation to retrieve historical alkalinity measurements for a user-owned aquarium in chronological order for graph rendering using the parameterized endpoint path.

#### Scenario: Alkalinity history is returned in chronological order
- **WHEN** an authenticated user requests alkalinity measurement history from `GET /aquariums/{aquarium_id}/measurements/alkalinity` for an owned aquarium
- **THEN** the system returns the measurements sorted by measurement timestamp in ascending order

#### Scenario: Alkalinity history supports graph-friendly time filtering
- **WHEN** an authenticated user requests alkalinity measurement history from `GET /aquariums/{aquarium_id}/measurements/alkalinity` with an optional time window filter
- **THEN** the system returns only alkalinity measurements within the requested time window

#### Scenario: History retrieval supports parameter filtering
- **WHEN** an authenticated user requests measurement history with a `parameter` filter set to `alkalinity`
- **THEN** the system returns only measurements matching the requested parameter

#### Scenario: History retrieval without parameter filter returns all results
- **WHEN** an authenticated user requests measurement history without a `parameter` filter
- **THEN** the system returns all matching measurements for the aquarium within any provided time window

#### Scenario: History retrieval accepts only a single parameter filter
- **WHEN** an authenticated user requests measurement history with more than one parameter value in the filter
- **THEN** the system rejects the request with a validation error

#### Scenario: Alkalinity history for non-owned aquarium is not accessible
- **WHEN** an authenticated user requests alkalinity measurement history from `GET /aquariums/{aquarium_id}/measurements/alkalinity` for an aquarium owned by another user
- **THEN** the system returns a not-found or unauthorized result and does not expose measurement data

### Requirement: Alkalinity measurements include canonical graph fields
The system SHALL store and return alkalinity measurements with fields required for graphing: parameter name, canonical value, canonical unit, and measurement timestamp.

#### Scenario: Persisted alkalinity measurement stores graph-required fields
- **WHEN** an authenticated user records a valid alkalinity measurement
- **THEN** the persisted record includes parameter `alkalinity`, numeric value in `dKH`, unit `dKH`, and measurement timestamp

#### Scenario: Retrieved alkalinity measurement includes graph-required fields
- **WHEN** an authenticated user retrieves alkalinity measurement history
- **THEN** each returned measurement item includes parameter `alkalinity`, numeric value in `dKH`, unit `dKH`, and measurement timestamp

### Requirement: Users can record magnesium measurements for owned aquariums
The system SHALL provide an authenticated operation to record a magnesium measurement for an aquarium owned by the requesting user using the parameterized endpoint path.

#### Scenario: Record magnesium measurement for owned aquarium
- **WHEN** an authenticated user submits a valid magnesium value, unit, and timestamp to `POST /aquariums/{aquarium_id}/measurements/magnesium` for an aquarium they own
- **THEN** the system persists the magnesium measurement associated with that aquarium and user

#### Scenario: Recording magnesium measurement for non-owned aquarium is rejected
- **WHEN** an authenticated user submits a magnesium measurement to `POST /aquariums/{aquarium_id}/measurements/magnesium` for an aquarium owned by another user
- **THEN** the system rejects the request with a not-found or unauthorized result and does not persist a measurement

### Requirement: Magnesium measurement payload is validated and normalized
The system SHALL validate magnesium payloads and MUST reject malformed or out-of-range values before persistence.

#### Scenario: Missing required magnesium fields are rejected
- **WHEN** an authenticated user submits a magnesium measurement request missing required fields (`value`, `unit`, or `measured_at`)
- **THEN** the system rejects the request with a validation error and does not persist a measurement

#### Scenario: Unsupported magnesium unit is rejected
- **WHEN** an authenticated user submits a magnesium measurement with a unit other than `ppm`
- **THEN** the system rejects the request with a validation error and does not persist a measurement

#### Scenario: Invalid magnesium value is rejected
- **WHEN** an authenticated user submits a magnesium measurement with a non-numeric or out-of-range value
- **THEN** the system rejects the request with a validation error and does not persist a measurement

#### Scenario: Valid magnesium values are stored in canonical unit
- **WHEN** an authenticated user submits a valid magnesium measurement in `ppm`
- **THEN** the system persists the measurement value in canonical `ppm` units

#### Scenario: Parameter name casing is normalized before persistence
- **WHEN** an authenticated user submits a magnesium measurement using any synonymous casing of the parameter name (for example `Magnesium` or `MAGNESIUM`)
- **THEN** the system normalizes the parameter name to lowercase `magnesium` before persistence

#### Scenario: Whitespace-padded parameter name is trimmed before persistence
- **WHEN** an authenticated user submits a magnesium measurement with leading or trailing whitespace in the parameter name (for example ` magnesium `)
- **THEN** the system trims the whitespace and persists the normalized lowercase parameter name `magnesium`

#### Scenario: Magnesium timestamp is rounded down to whole-second resolution
- **WHEN** an authenticated user submits a magnesium measurement with sub-second `measured_at` precision
- **THEN** the system truncates the timestamp to the nearest lower whole second before persistence

### Requirement: Duplicate magnesium readings at the same timestamp are not allowed
The system SHALL prevent duplicate magnesium records for the same aquarium and normalized measurement timestamp.

#### Scenario: Duplicate magnesium reading at same aquarium and second is rejected
- **WHEN** an authenticated user submits a magnesium reading for an aquarium where a `magnesium` reading already exists at the same normalized `measured_at` second
- **THEN** the system rejects the request with a conflict or validation error and does not create a duplicate record

### Requirement: Users can retrieve magnesium measurement history for graphing
The system SHALL provide an authenticated operation to retrieve historical magnesium measurements for a user-owned aquarium in chronological order for graph rendering using the parameterized endpoint path.

#### Scenario: Magnesium history is returned in chronological order
- **WHEN** an authenticated user requests magnesium measurement history from `GET /aquariums/{aquarium_id}/measurements/magnesium` for an owned aquarium
- **THEN** the system returns the measurements sorted by measurement timestamp in ascending order

#### Scenario: Magnesium history supports graph-friendly time filtering
- **WHEN** an authenticated user requests magnesium measurement history from `GET /aquariums/{aquarium_id}/measurements/magnesium` with an optional time window filter
- **THEN** the system returns only magnesium measurements within the requested time window

#### Scenario: History retrieval supports parameter filtering
- **WHEN** an authenticated user requests measurement history with a `parameter` filter set to `magnesium`
- **THEN** the system returns only measurements matching the requested parameter

#### Scenario: History retrieval without parameter filter returns all results
- **WHEN** an authenticated user requests measurement history without a `parameter` filter
- **THEN** the system returns all matching measurements for the aquarium within any provided time window

#### Scenario: History retrieval accepts only a single parameter filter
- **WHEN** an authenticated user requests measurement history with more than one parameter value in the filter
- **THEN** the system rejects the request with a validation error

#### Scenario: Magnesium history for non-owned aquarium is not accessible
- **WHEN** an authenticated user requests magnesium measurement history from `GET /aquariums/{aquarium_id}/measurements/magnesium` for an aquarium owned by another user
- **THEN** the system returns a not-found or unauthorized result and does not expose measurement data

### Requirement: Magnesium measurements include canonical graph fields
The system SHALL store and return magnesium measurements with fields required for graphing: parameter name, canonical value, canonical unit, and measurement timestamp.

#### Scenario: Persisted magnesium measurement stores graph-required fields
- **WHEN** an authenticated user records a valid magnesium measurement
- **THEN** the persisted record includes parameter `magnesium`, numeric value in `ppm`, unit `ppm`, and measurement timestamp

#### Scenario: Retrieved magnesium measurement includes graph-required fields
- **WHEN** an authenticated user retrieves magnesium measurement history
- **THEN** each returned measurement item includes parameter `magnesium`, numeric value in `ppm`, unit `ppm`, and measurement timestamp

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
