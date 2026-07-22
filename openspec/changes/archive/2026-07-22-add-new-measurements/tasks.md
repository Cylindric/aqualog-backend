## 1. Parameter Rules and Data Model

- [x] 1.1 Define phosphate parameter constraints (ppm-only unit and valid range) in shared measurement validation logic.
- [x] 1.2 Add parameter-name normalization logic to trim whitespace, accept synonymous casing, and store lowercase canonical parameter values.
- [x] 1.3 Update measurement domain models/schemas to represent phosphate records consistently with existing measurement fields.
- [x] 1.4 Add or adjust database constraints/indexes needed to enforce duplicate prevention for phosphate at aquarium + parameter + normalized timestamp.

## 2. API and Repository Implementation

- [x] 2.1 Extend measurement create endpoint to accept phosphate payloads and apply parameter-aware validation.
- [x] 2.2 Extend measurement persistence flow to store phosphate values in canonical `ppm` units with normalized timestamps.
- [x] 2.3 Extend measurement history retrieval to return results in chronological order with existing ownership checks, where no parameter filter returns all results and a single parameter filter narrows results.
- [x] 2.4 Validate history filter shape so multi-value or compound parameter filters are rejected.

## 3. Tests and Verification

- [x] 3.1 Add API tests for phosphate create success/failure scenarios (ownership, missing fields, unsupported unit, invalid values, duplicate timestamp, ppm-only validation, parameter-casing normalization, and whitespace trimming).
- [x] 3.2 Add repository tests for phosphate storage and retrieval semantics, including timestamp truncation, duplicate rejection, and no-filter vs single-parameter-filter history behavior.
- [x] 3.3 Add validation tests confirming multi-parameter/compound filter requests are rejected.
- [x] 3.4 Run full test suite and confirm coverage remains at or above project target.
