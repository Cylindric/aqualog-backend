## Why

Aquarium keepers track a standard set of water-quality parameters beyond salinity, phosphate, and temperature (e.g. calcium, ammonia, nitrite, nitrate, pH, alkalinity, magnesium) to assess tank health. The measurement API currently rejects these, forcing users to track them elsewhere and fragmenting their water-quality history.

## What Changes

- Extend measurement recording and retrieval to accept seven additional water parameters: `calcium` (`ppm`), `ammonia` (`mg/L`), `nitrite` (`ppm`), `nitrate` (`ppm`), `ph` (`pH`), `alkalinity` (`dKH`), and `magnesium` (`ppm`).
- Add parameter-specific validation (single supported unit and a sanity value range) for each new parameter, following the existing phosphate pattern of one canonical unit per parameter.
- Refactor the per-parameter unit/range/canonicalization rules in `src/aquarium_measurements.py` from an `if`/`elif` chain into a declarative per-parameter config table, since the current fallback branch (anything not salinity/temperature) implicitly assumes phosphate's rules — that assumption breaks once more single-unit parameters are added.
- Extend the parameter threshold feature's unit/sanity-range tables (`src/aquarium_parameter_thresholds.py`) so target/min/max thresholds can be set for the new parameters too.
- Preserve existing ownership, timestamp normalization, duplicate-prevention, and parameter name casing/whitespace normalization behavior for the new parameters.
- Add tests for validation, persistence, and retrieval behavior of each newly supported measurement parameter.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `api-aquarium-water-parameter-measurements`: Extend requirements from salinity/phosphate/temperature to include seven additional supported water parameters (calcium, ammonia, nitrite, nitrate, pH, alkalinity, magnesium), each with its own unit and validation range.

## Impact

- Affected validation/canonicalization logic in `src/aquarium_measurements.py` (`SUPPORTED_PARAMETERS`, per-parameter unit sets, sanity ranges, `_canonicalize_measurement`, `_validate_measurement_payload`, `_normalize_parameter`).
- Affected threshold configuration in `src/aquarium_parameter_thresholds.py` (`THRESHOLD_UNITS`, `THRESHOLD_SANITY_RANGES`) so the new parameters are settable as thresholds, consistent with existing parameters.
- No persistence/schema changes expected — `AquariumMeasurement.parameter`/`unit` are already free-form `String` columns.
- New and updated tests under `tests/test_aquarium_measurements.py`, measurement repository tests, and threshold tests covering unit validation, range validation, and casing/whitespace normalization for each new parameter.
