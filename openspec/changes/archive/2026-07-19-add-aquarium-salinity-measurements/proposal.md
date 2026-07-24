## Why

Aquarium users need to record water parameter measurements over time so they can observe trends and make better husbandry decisions. Supporting salinity first delivers immediate value for marine keepers and establishes a reusable pattern for future parameters.

## What Changes

- Add authenticated API support for recording salinity measurements for a user-owned aquarium.
- Add authenticated API support for listing historical salinity measurements for a user-owned aquarium in time order.
- Persist salinity measurements with timestamp metadata suitable for graphing and trend analysis.
- Validate measurement payloads (value, unit, timestamp) and reject invalid or cross-user operations.

## Capabilities

### New Capabilities
- `api-aquarium-water-parameter-measurements`: Capture and retrieve aquarium water parameter measurements over time, initially scoped to salinity.

### Modified Capabilities
- None.

## Impact

- Affected API surface: new aquarium measurement endpoints for create/list salinity entries.
- Affected persistence layer: new measurement storage model, migration, and repository/query paths.
- Affected application logic: validation, ownership authorization, and response shaping for graph-friendly time-series output.
- Affected tests: new unit/integration tests for endpoint behavior, persistence, validation, and authorization.
