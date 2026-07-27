## 1. Declarative parameter config

- [x] 1.1 Introduce a per-parameter config structure in `src/aquarium_measurements.py` (accepted unit(s), canonical unit, sanity value range) covering the three existing parameters (salinity, temperature, phosphate) with unchanged behavior.
- [x] 1.2 Rewrite `_validate_measurement_payload`, `_canonicalize_measurement`, and the `_normalize_parameter` error message to read from the config structure instead of the `if`/`elif` chain.
- [x] 1.3 Run the existing test suite to confirm salinity/temperature/phosphate behavior is unchanged after the refactor.

## 2. Add new measurement parameters

- [x] 2.1 Add `calcium` (`ppm`, range 0-1000) to the parameter config and `SUPPORTED_PARAMETERS`.
- [x] 2.2 Add `ammonia` (`mg/L`, range 0-50) to the parameter config and `SUPPORTED_PARAMETERS`.
- [x] 2.3 Add `nitrite` (`ppm`, range 0-50) to the parameter config and `SUPPORTED_PARAMETERS`.
- [x] 2.4 Add `nitrate` (`ppm`, range 0-500) to the parameter config and `SUPPORTED_PARAMETERS`.
- [x] 2.5 Add `ph` (`pH`, range 0-14) to the parameter config and `SUPPORTED_PARAMETERS`.
- [x] 2.6 Add `alkalinity` (`dKH`, range 0-30) to the parameter config and `SUPPORTED_PARAMETERS`.
- [x] 2.7 Add `magnesium` (`ppm`, range 0-2000) to the parameter config and `SUPPORTED_PARAMETERS`.
- [x] 2.8 Update the "Parameter must be one of: ..." validation error message to enumerate all ten supported parameters.

## 3. Threshold config parity

- [x] 3.1 Add the seven new parameters to `THRESHOLD_UNITS` in `src/aquarium_parameter_thresholds.py` using the same canonical units as measurements.
- [x] 3.2 Add the seven new parameters to `THRESHOLD_SANITY_RANGES` in `src/aquarium_parameter_thresholds.py` using the same sanity ranges as measurements.

## 4. Tests

- [x] 4.1 Add API tests (`tests/test_aquarium_measurements.py`) per new parameter for: create success, missing fields, unsupported unit, out-of-range value, correct canonical value/unit persisted, parameter-name casing normalization, whitespace trimming, duplicate-timestamp rejection, and non-owned-aquarium rejection.
- [x] 4.2 Add history retrieval tests per new parameter: chronological ordering, time-window filtering, single-parameter filtering, no-filter-returns-all, and non-owned-aquarium rejection.
- [x] 4.3 Add repository-level tests covering persistence/query behavior for the new parameters where existing repository tests are parametrized by parameter.
- [x] 4.4 Add threshold tests confirming target/min/max can be set and retrieved for each new parameter within its sanity range, and rejected outside it.
- [x] 4.5 Run `task test` and confirm coverage remains at or above project target.
