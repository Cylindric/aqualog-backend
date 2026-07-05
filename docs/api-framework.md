# API Framework Conventions

This project exposes versioned HTTP routes under `/api/v1`.

## Runtime and Startup

- Mandatory environment variable: `AQUALOG_APP_ENV`
- Optional environment variables:
  - `AQUALOG_API_VERSION` (default: `v1`)
  - `AQUALOG_LOG_LEVEL` (default: `INFO`)
- App startup initializes readiness dependencies before reporting ready.

## Container Defaults

The Docker image bakes these runtime defaults:

- `AQUALOG_APP_ENV=prod`
- `AQUALOG_API_VERSION=v1`
- `AQUALOG_LOG_LEVEL=INFO`

Runtime values can override baked defaults using container environment arguments, for example:

`docker run -e AQUALOG_APP_ENV=test -e AQUALOG_LOG_LEVEL=DEBUG <image>`

## Compose Bootstrap

- A repository-root compose file is provided at `docker-compose.yml`.
- The compose API service builds from the local Dockerfile and reuses its startup contract.
- Host port mapping defaults to `8000:8000` and can be overridden with `AQUALOG_HOST_PORT`.
- Compose defaults prioritize local workflow startup values:
  - `AQUALOG_APP_ENV=dev`
  - `AQUALOG_API_VERSION=v1`
  - `AQUALOG_LOG_LEVEL=INFO`

Example startup with defaults:

`docker compose up --build`

Example with overrides:

`AQUALOG_APP_ENV=test AQUALOG_HOST_PORT=8080 docker compose up --build`

## Operational Endpoints

- `GET /api/v1/live`
  - Purpose: process liveness only
  - Response body includes machine-readable status field
- `GET /api/v1/ready`
  - Purpose: traffic readiness
  - Returns `503` with `not_ready` status before readiness is complete
  - Returns `200` with `ready` status when initialized

## Response Envelopes

All successful responses follow:

```json
{
  "success": true,
  "request_id": "<id>",
  "data": {}
}
```

All error responses follow:

```json
{
  "success": false,
  "request_id": "<id>",
  "error": {
    "code": "<machine_code>",
    "message": "<safe_message>"
  }
}
```

## Correlation and Logging

- Request correlation ID is read from `x-request-id` if provided, otherwise generated.
- `x-request-id` is returned on responses.
- Structured request start/completion events are logged with method, path, status, and duration.
