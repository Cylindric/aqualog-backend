## ADDED Requirements

### Requirement: Aquarium records are owned by a single authenticated user
The system SHALL persist each aquarium with exactly one owning user and MUST reject operations that would create an ownerless aquarium.

#### Scenario: Aquarium is created with authenticated owner association
- **WHEN** an authenticated user creates a new aquarium
- **THEN** the persisted aquarium record is stored with that user's identifier as the owner

#### Scenario: Owner association is required
- **WHEN** an aquarium create operation is attempted without an authenticated user context
- **THEN** the system rejects the operation and no aquarium is persisted

### Requirement: Users can only access their own aquariums
The system SHALL scope aquarium queries and resource access to the authenticated user so that users cannot see or operate on aquariums owned by other users.

#### Scenario: Listing aquariums returns only owned records
- **WHEN** an authenticated user requests their aquarium list
- **THEN** the response includes only aquariums whose owner matches the authenticated user

#### Scenario: Access to another user's aquarium is blocked
- **WHEN** an authenticated user requests, updates, or deletes an aquarium owned by another user
- **THEN** the system returns a not-found or unauthorized result and does not expose foreign aquarium data

### Requirement: Users can add aquariums with initial properties
The system SHALL provide an authenticated create operation for aquariums that accepts initial properties: name, type, and volume. The `type` field SHALL be treated as an open string value and SHALL be trimmed before validation and persistence. The `volume` field SHALL include explicit unit metadata in requests, SHALL allow only `L` and `gal_us` units in v1, and SHALL be converted to liters before internal storage.

#### Scenario: Create aquarium with valid properties succeeds
- **WHEN** an authenticated user submits valid name, type, and volume values
- **THEN** the system persists the aquarium and returns the created aquarium resource

#### Scenario: Create aquarium with invalid properties is rejected
- **WHEN** an authenticated user submits invalid or missing name, type, or volume values
- **THEN** the system rejects the request with a validation error and does not persist the aquarium

#### Scenario: Aquarium volume is persisted in liters
- **WHEN** an authenticated user creates an aquarium with a valid `volume` value
- **THEN** the system persists the aquarium volume in liters as the internal storage unit

#### Scenario: Aquarium volume is converted from submitted unit metadata
- **WHEN** an authenticated user submits a valid `volume` value with supported unit metadata
- **THEN** the system converts the submitted value to liters before persisting the aquarium

#### Scenario: Supported volume units in v1 are enforced
- **WHEN** an authenticated user submits `volume` unit metadata other than `L` or `gal_us`
- **THEN** the system rejects the request with a validation error and does not persist the aquarium

#### Scenario: Unsupported volume unit metadata is rejected
- **WHEN** an authenticated user submits `volume` with unsupported or missing unit metadata
- **THEN** the system rejects the request with a validation error and does not persist the aquarium

#### Scenario: Aquarium type is normalized by trimming whitespace
- **WHEN** an authenticated user submits a `type` value with leading or trailing spaces
- **THEN** the system trims the `type` value before validating and persisting the aquarium

#### Scenario: Aquarium type length constraints are enforced
- **WHEN** an authenticated user submits a `type` value shorter than 3 characters or longer than 24 characters after trimming
- **THEN** the system rejects the request with a validation error and does not persist the aquarium

### Requirement: Users can edit their own aquariums
The system SHALL provide an authenticated update operation that allows the owning user to modify allowed aquarium properties. The `type` field SHALL be treated as an open string value and SHALL be trimmed before validation and persistence. The `volume` field SHALL include explicit unit metadata in requests, SHALL allow only `L` and `gal_us` units in v1, and SHALL be converted to liters before internal storage.

#### Scenario: Owner updates aquarium properties successfully
- **WHEN** an owning user submits valid updates to name, type, or volume
- **THEN** the system persists the changes and returns the updated aquarium resource

#### Scenario: Update preserves ownership and blocks cross-user edits
- **WHEN** a non-owning user attempts to update an aquarium
- **THEN** the system does not modify the aquarium and returns a not-found or unauthorized result

#### Scenario: Aquarium type update enforces trim and length constraints
- **WHEN** an owning user updates `type` with leading/trailing spaces or with a value outside 3..24 characters after trimming
- **THEN** the system trims before validation, accepts only values within 3..24 characters, and rejects invalid values with a validation error

#### Scenario: Aquarium volume update preserves liters as internal unit
- **WHEN** an owning user updates `volume` with a valid value
- **THEN** the system persists the updated volume in liters as the internal storage unit

#### Scenario: Aquarium volume update converts submitted unit metadata
- **WHEN** an owning user updates `volume` with a valid value and supported unit metadata
- **THEN** the system converts the submitted value to liters before persisting the update

#### Scenario: Aquarium volume update rejects unsupported unit metadata
- **WHEN** an owning user updates `volume` with unsupported or missing unit metadata
- **THEN** the system rejects the request with a validation error and does not persist invalid volume input

### Requirement: Aquarium names are unique per user
The system SHALL enforce aquarium name uniqueness within each owning user scope.

#### Scenario: Duplicate aquarium name for same user is rejected on create
- **WHEN** an authenticated user creates an aquarium using a name that already exists for that same user
- **THEN** the system rejects the request with a conflict or validation error and does not create a duplicate aquarium name for that user

#### Scenario: Duplicate aquarium name for same user is rejected on update
- **WHEN** an owning user updates an aquarium name to one that already exists on another aquarium they own
- **THEN** the system rejects the request with a conflict or validation error and does not persist the duplicate name

#### Scenario: Different users may reuse the same aquarium name
- **WHEN** two different users each create an aquarium with the same name
- **THEN** both creations succeed because uniqueness is enforced per user, not globally

### Requirement: Users can delete their own aquariums
The system SHALL provide an authenticated delete operation that allows the owning user to remove an aquarium.

#### Scenario: Owner deletes aquarium successfully
- **WHEN** an owning user requests deletion of their aquarium
- **THEN** the system removes the aquarium record and indicates successful deletion

#### Scenario: Non-owner delete request is rejected
- **WHEN** a non-owning user requests deletion of an aquarium
- **THEN** the system does not delete the aquarium and returns a not-found or unauthorized result
