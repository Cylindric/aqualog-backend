## Why

The measurement API currently focuses on salinity, which limits users who also track other water parameters for aquarium health. Expanding supported measurements now enables more complete water-quality tracking in the same workflow and data model.

## What Changes

- Extend measurement recording to accept additional water parameters beyond salinity, starting with phosphate.
- Add parameter-specific validation and normalization rules for each newly supported measurement type, with phosphate limited to `ppm` for now.
- Accept parameter names in synonymous casing (for example `Phosphate`, `PHOSPHATE`), trim surrounding whitespace, and normalize to lowercase before persistence.
- Preserve ownership and access-control semantics for creating and retrieving measurements.
- Expand measurement history retrieval to return the new parameter data in the same graph-friendly format, with either no filter (all results) or a single `parameter` filter.
- Add tests for validation, persistence, and retrieval behavior of newly supported measurements.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `api-aquarium-water-parameter-measurements`: Extend requirements from salinity-only behavior to include additional supported water parameters (starting with phosphate), including validation and history retrieval semantics.

## Impact

- Affected API routes and request/response schemas in `src/aquarium_measurements.py`.
- Affected persistence and query logic in `src/aquarium_measurement_repository.py` and related models/migrations.
- Potential updates to canonical measurement conversion/validation logic in `src/calculation.py` or equivalent parameter utility modules.
- New and updated tests under `tests/test_aquarium_measurements.py` and repository-level measurement tests, including ppm-only validation, parameter-casing normalization, and single-parameter history filtering behavior.
