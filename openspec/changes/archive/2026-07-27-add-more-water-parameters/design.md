## Context

`src/aquarium_measurements.py` currently supports three parameters: `salinity` (multi-unit, converted to canonical `ppt`), `temperature` (multi-unit, converted to canonical `celsius`), and `phosphate` (single-unit `ppm`, no conversion). Validation and canonicalization are implemented as an explicit `if`/`elif` chain in `_validate_measurement_payload` and `_canonicalize_measurement`, where anything that isn't salinity or temperature falls through to phosphate's rules (single `ppm` unit, `0 <= value <= 100`). That fallback branch is only correct because phosphate is currently the only other parameter — it is not a real "default" case.

This change adds seven more single-unit parameters (calcium, ammonia, nitrite, nitrate, pH, alkalinity, magnesium), each following the same shape as phosphate: one accepted unit, no conversion, and a sanity value range. Reusing the current fallback branch as-is would silently apply phosphate's `ppm`/0-100 rule to all of them, which is wrong (e.g. pH values are 0-14, not ppm at all).

## Goals / Non-Goals

**Goals:**
- Add calcium (`ppm`), ammonia (`mg/L`), nitrite (`ppm`), nitrate (`ppm`), pH (`pH`), alkalinity (`dKH`), and magnesium (`ppm`) as supported measurement parameters, each with exactly one accepted unit and a sanity value range.
- Replace the `if`/`elif` fallback in `_validate_measurement_payload`/`_canonicalize_measurement` with a declarative per-parameter config table (unit set, canonical unit, value range), so adding a parameter means adding a table row, not a new branch.
- Extend `src/aquarium_parameter_thresholds.py`'s `THRESHOLD_UNITS`/`THRESHOLD_SANITY_RANGES` maps so target/min/max thresholds can be set for the new parameters, consistent with existing ones.
- Reuse the existing ingestion pipeline: ownership checks, timestamp truncation, duplicate prevention, and parameter name casing/whitespace normalization apply unchanged to the new parameters.

**Non-Goals:**
- Unit conversion for the new parameters — each ships with a single accepted unit, matching the phosphate precedent. Multi-unit support (e.g. alkalinity in `meq/L` as well as `dKH`) is deferred until requested.
- Retroactively writing a spec for `temperature`, which was implemented previously but was never captured as an OpenSpec requirement. Left as pre-existing drift, out of scope here.
- Changing threshold requirements/spec — `api-aquarium-parameter-thresholds` is mid-flight in another change and not yet synced into `openspec/specs/`; this change only extends its config tables so the new parameters behave consistently, without asserting new threshold-level requirements.

## Decisions

1. Represent per-parameter rules as a declarative table keyed by parameter name (accepted units, canonical unit, min/max sanity range), and rewrite `_validate_measurement_payload`/`_canonicalize_measurement`/`_normalize_parameter`'s error message to iterate over it.
   - Rationale: this was flagged as a risk in the original phosphate/temperature change ("Future parameter additions may create branching complexity") and adding 7 parameters at once is exactly the trigger for paying that down now.
   - Alternative considered: keep appending `if parameter == X` branches for each new parameter — rejected, since it was already producing an incorrect implicit default and would only get harder to reason about at 10 parameters.

2. Give each new parameter exactly one accepted unit, no conversion path, matching phosphate's precedent (`ppm`, `mg/L`, `ppm`, `ppm`, `pH`, `dKH`, `ppm` respectively).
   - Rationale: matches the units requested and keeps validation simple and testable; avoids inventing conversion factors (e.g. dKH↔ppm CaCO3) that weren't asked for.
   - Alternative considered: canonical SI-style units with conversion (e.g. store alkalinity in mg/L CaCO3) — rejected as unnecessary complexity for this change.

3. Sanity value ranges are generous upper/lower bounds to catch obviously-wrong sensor/typo input, not tank-health target ranges (those remain user-configurable per-aquarium via thresholds):
   - Calcium: 0–1000 ppm
   - Ammonia: 0–50 mg/L
   - Nitrite: 0–50 ppm
   - Nitrate: 0–500 ppm
   - pH: 0–14
   - Alkalinity: 0–30 dKH
   - Magnesium: 0–2000 ppm
   - Rationale: mirrors how `MAX_PHOSPHATE_PPM`/salinity/temperature ranges are used today — as coarse validity bounds, not ideal-range enforcement.
   - Alternative considered: no range validation for new parameters — rejected for consistency with existing parameters and to reject obviously bad values (e.g. negative pH).

4. Extend threshold config tables (`THRESHOLD_UNITS`, `THRESHOLD_SANITY_RANGES`) for the new parameters using the same canonical units/ranges as measurements.
   - Rationale: `SUPPORTED_THRESHOLD_PARAMETERS` is imported directly from `SUPPORTED_PARAMETERS`, so once a parameter is measurement-supported it is already threshold-addressable; leaving its threshold config table entries out would cause a `KeyError` at runtime instead of a clean validation error.
   - Alternative considered: gate new parameters out of thresholds — rejected, no behavioral reason to treat them differently from phosphate.

## Risks / Trade-offs

- Refactoring shared validation/canonicalization logic touches all existing parameters (salinity, phosphate, temperature), not just the new ones -> Mitigation: keep exact existing behavior/error messages for current parameters, add full regression test coverage before touching new parameters.
- Ten total parameters increase the length of the "Parameter must be one of: ..." validation error message -> Mitigation: acceptable; message stays a plain enumeration, no truncation needed at this scale.
- Sanity ranges chosen here are estimates, not values requested explicitly by the user -> Mitigation: ranges are documented in this design for easy adjustment; they only reject grossly invalid values, not narrow real-world tank conditions.

## Migration Plan

- No schema/migration changes required — `parameter` and `unit` are already free-form `String` columns.
- Deploy with all seven parameters enabled by default; existing salinity/phosphate/temperature behavior is unchanged.
- Rollback strategy: revert the API code change; no data migration to undo since no new columns/tables are introduced.

## Open Questions

- None for this phase.
