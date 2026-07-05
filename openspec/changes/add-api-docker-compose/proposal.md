## Why

The API can run in a container image, but there is no docker-compose definition for quickly bringing up the service with consistent runtime settings. Adding a compose file now reduces startup friction for local development and operational smoke testing.

## What Changes

- Add a `docker-compose.yml` file to bring up the API server service.
- Configure compose service build/run settings to use the project Dockerfile.
- Define environment and port mappings needed to access the API locally.
- Ensure compose startup path remains aligned with the container image entrypoint.

## Capabilities

### New Capabilities
- `api-compose-bootstrap`: Provides a docker-compose workflow for bringing up the API server.

### Modified Capabilities
- `api-container-image`: Clarify that the Dockerfile-based image is consumable by compose service startup.

## Impact

- Developer workflow: adds compose-based startup command path.
- Container orchestration baseline: introduces compose service definition for the API.
- Runtime behavior: environment and networking defaults are codified for local bring-up.
