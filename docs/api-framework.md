# API Framework Conventions

This project exposes versioned HTTP routes under `/api/v1`.

## Runtime and Startup

- Mandatory environment variable: `AQUALOG_APP_ENV`
- Optional environment variables:
  - `AQUALOG_API_VERSION` (default: `v1`)
  - `AQUALOG_LOG_LEVEL` (default: `INFO`)
- App startup initializes readiness dependencies before reporting ready.

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
