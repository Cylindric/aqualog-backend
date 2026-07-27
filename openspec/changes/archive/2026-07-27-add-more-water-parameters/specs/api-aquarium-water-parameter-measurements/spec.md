## ADDED Requirements

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
