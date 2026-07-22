## Why

The current measurements API mixes two path patterns for the same resource shape, which increases client complexity and fragments behavior between generic and salinity-specific routes. Consolidating on a parameterized endpoint now simplifies contract clarity and prepares the API for parameter growth while removing obsolete salinity-only paths.

## What Changes

- **BREAKING** Refactor measurement read/write routes from `/aquariums/{aquarium_id}/measurements` to `/aquariums/{aquarium_id}/measurements/{parameter}` for both `GET` and `POST`.
- Preserve authenticated ownership checks and validation semantics on the new parameterized path.
- Define behavior for supported parameters (including `salinity`) through path-based parameter selection rather than payload/query-only selection.
- Accept mixed-case path-parameter aliases (for example `Salinity`, `PHOSPHATE`) and normalize them to lowercase before validation and downstream processing.
- Mark `/aquariums/{aquarium_id}/measurements/salinity` behavior as obsolete where it duplicates prior special-case handling, and remove compatibility paths as part of this change.
- Update tests and docs to reflect the new canonical endpoint contract.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `api-aquarium-water-parameter-measurements`: Change measurement create/list API contract to use `{parameter}` in the route path and retire obsolete salinity-specific endpoint behavior.

## Impact

- Affected API surface: measurement `GET`/`POST` routes and routing precedence in `src/aquarium_measurements.py`.
- Affected request handling: parameter extraction/normalization from path plus validation alignment with existing parameter rules.
- Affected tests: endpoint behavior and route-contract updates in `tests/test_aquarium_measurements.py` and related repository/api tests.
- Affected docs/specs: OpenSpec delta for measurement capability and any API docs referencing legacy measurement routes.
