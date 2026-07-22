## ADDED Requirements

### Requirement: Measurement routes are parameterized by path
The system SHALL expose canonical authenticated measurement create and retrieval operations at `/aquariums/{aquarium_id}/measurements/{parameter}` for supported parameters.

#### Scenario: Create measurement uses parameterized path
- **WHEN** an authenticated user submits a measurement create request to `/aquariums/{aquarium_id}/measurements/{parameter}` with a supported parameter value
- **THEN** the system uses the `{parameter}` path segment as the measurement parameter selector for validation and persistence

#### Scenario: Retrieve measurement history uses parameterized path
- **WHEN** an authenticated user submits a history request to `/aquariums/{aquarium_id}/measurements/{parameter}` with a supported parameter value
- **THEN** the system returns only history entries matching the requested path parameter

#### Scenario: Unsupported path parameter is rejected
- **WHEN** an authenticated user submits create or history requests to `/aquariums/{aquarium_id}/measurements/{parameter}` with an unsupported parameter value
- **THEN** the system rejects the request with a validation error and does not create or expose measurement data

#### Scenario: Mixed-case path parameter aliases are normalized
- **WHEN** an authenticated user submits create or history requests with a supported parameter alias using mixed case in `{parameter}` (for example `Salinity` or `PHOSPHATE`)
- **THEN** the system normalizes `{parameter}` to lowercase before validation and processing, and applies behavior for the normalized supported parameter

## MODIFIED Requirements

### Requirement: Users can record salinity measurements for owned aquariums
The system SHALL provide an authenticated operation to record a salinity measurement for an aquarium owned by the requesting user using the parameterized endpoint path.

#### Scenario: Record salinity measurement for owned aquarium
- **WHEN** an authenticated user submits a valid salinity value and timestamp to `POST /aquariums/{aquarium_id}/measurements/salinity` for an aquarium they own
- **THEN** the system persists the salinity measurement associated with that aquarium and user

#### Scenario: Recording measurement for non-owned aquarium is rejected
- **WHEN** an authenticated user submits a salinity measurement to `POST /aquariums/{aquarium_id}/measurements/salinity` for an aquarium owned by another user
- **THEN** the system rejects the request with a not-found or unauthorized result and does not persist a measurement

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

### Requirement: Users can record phosphate measurements for owned aquariums
The system SHALL provide an authenticated operation to record a phosphate measurement for an aquarium owned by the requesting user using the parameterized endpoint path.

#### Scenario: Record phosphate measurement for owned aquarium
- **WHEN** an authenticated user submits a valid phosphate value, unit, and timestamp to `POST /aquariums/{aquarium_id}/measurements/phosphate` for an aquarium they own
- **THEN** the system persists the phosphate measurement associated with that aquarium and user

#### Scenario: Recording phosphate measurement for non-owned aquarium is rejected
- **WHEN** an authenticated user submits a phosphate measurement to `POST /aquariums/{aquarium_id}/measurements/phosphate` for an aquarium owned by another user
- **THEN** the system rejects the request with a not-found or unauthorized result and does not persist a measurement

### Requirement: Users can retrieve phosphate measurement history for graphing
The system SHALL provide an authenticated operation to retrieve historical phosphate measurements for a user-owned aquarium in chronological order for graph rendering using the parameterized endpoint path.

#### Scenario: Phosphate history is returned in chronological order
- **WHEN** an authenticated user requests phosphate measurement history from `GET /aquariums/{aquarium_id}/measurements/phosphate` for an owned aquarium
- **THEN** the system returns the measurements sorted by measurement timestamp in ascending order

#### Scenario: Phosphate history supports graph-friendly time filtering
- **WHEN** an authenticated user requests phosphate measurement history from `GET /aquariums/{aquarium_id}/measurements/phosphate` with an optional time window filter
- **THEN** the system returns only phosphate measurements within the requested time window

#### Scenario: Phosphate history for non-owned aquarium is not accessible
- **WHEN** an authenticated user requests phosphate measurement history from `GET /aquariums/{aquarium_id}/measurements/phosphate` for an aquarium owned by another user
- **THEN** the system returns a not-found or unauthorized result and does not expose measurement data

## REMOVED Requirements

### Requirement: Legacy salinity-specific endpoint aliases remain supported
**Reason**: The API contract is standardized on `/aquariums/{aquarium_id}/measurements/{parameter}` for both write and read operations.
**Migration**: Clients MUST call `POST`/`GET` at `/aquariums/{aquarium_id}/measurements/salinity` for salinity and use the same path pattern for other supported parameters.
