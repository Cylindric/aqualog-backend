## MODIFIED Requirements

### Requirement: API container image can be built from a Dockerfile
The system SHALL provide a Dockerfile that can be used to build a container image for the API server and SHALL remain consumable by docker-compose bootstrap.

#### Scenario: Dockerfile is present at the repository root
- **WHEN** a user inspects the repository for container build configuration
- **THEN** a Dockerfile is available for building the API image

#### Scenario: Image build produces runnable container artifacts
- **WHEN** the Dockerfile is built successfully
- **THEN** the resulting image contains the application runtime needed to start the API server

#### Scenario: Compose service can use the Dockerfile-based image
- **WHEN** docker-compose starts the API service from project source
- **THEN** compose can build and run the API service using the same Dockerfile contract
