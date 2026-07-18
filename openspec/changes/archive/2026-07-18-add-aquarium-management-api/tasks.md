## 1. Database and Schema Foundation

- [x] 1.1 Add an Alembic migration to create the `aquariums` table with `id`, `owner_user_id`, `name`, `type`, `volume`, and timestamps.
- [x] 1.2 Add foreign key, owner index, and a unique constraint on (`owner_user_id`, `name`) to enforce per-user aquarium name uniqueness.
- [x] 1.3 Update persistence models/types to represent aquarium records and ownership constraints.

## 2. Repository and Validation Logic

- [x] 2.1 Implement aquarium repository methods for create, list-by-owner, get-by-id-and-owner, update-by-id-and-owner, and delete-by-id-and-owner.
- [x] 2.2 Implement validation rules for aquarium input fields (`name`, `type`, `volume`) and shared request/response schemas, including trimming `type`, enforcing length 3..24, requiring explicit `volume` unit metadata, allowing only `L` and `gal_us`, and converting to liters for storage.
- [x] 2.3 Ensure repository methods require authenticated owner context and cannot operate without owner scoping.

## 3. Authenticated Aquarium API Endpoints

- [x] 3.1 Add authenticated endpoints for aquarium list/read and wire them to owner-scoped repository calls.
- [x] 3.2 Add authenticated create endpoint for aquariums with required initial properties.
- [x] 3.3 Add authenticated update and delete endpoints with owner-only behavior.
- [x] 3.4 Standardize endpoint responses and error handling to existing API response conventions.

## 4. Authorization and Security Hardening

- [x] 4.1 Add cross-user access protections so read/update/delete attempts on foreign aquariums return not-found or unauthorized without data leakage.
- [x] 4.2 Add guardrails preventing owner reassignment via update payloads.
- [x] 4.3 Verify unauthorized requests still return 401 behavior consistent with existing OAuth endpoint protection.

## 5. Tests and Verification

- [x] 5.1 Add unit tests for aquarium repository CRUD operations and owner-scoped filtering.
- [x] 5.2 Add tests for per-user aquarium name uniqueness on create and update, including concurrent conflict behavior.
- [x] 5.3 Add endpoint tests for create/list/read/update/delete success paths for the owning user.
- [x] 5.4 Add negative tests for validation failures, cross-user access attempts, and `type` trim/length constraints.
- [x] 5.5 Add tests verifying `volume` unit metadata is required, `L` and `gal_us` are converted correctly to liters, all other units are rejected, and liters are persisted internally for create/update paths.
- [ ] 5.6 Run full test suite and confirm coverage remains at or above project target.
