# AquaLog

## Dev Environment Setup

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source .venv/bin/activate
uv venv .venv

curl -1sLf 'https://dl.cloudsmith.io/public/task/task/setup.deb.sh' | sudo -E bash
sudo apt install task

npm install -g npm@11.18.0
npm install
```

## Useful Commands

### Authentik

* Password reset

    ```bash
    docker compose exec authentikserver ak changepassword akadmin
    ```

## OAuth2 Authentication

The API uses OAuth2/OIDC authentication via Authentik. Protected endpoints require a valid JWT token issued by Authentik.

### Configuration

Set the following environment variables to enable OAuth2:

- **AQUALOG_OAUTH_ISSUER_URL**: OIDC issuer URL (default: `https://authentikserver:9443/application/o/aqualog/`)
- **AQUALOG_OAUTH_AUDIENCE**: OAuth2 audience claim (default: `aqualog-api`)

### Getting Tokens for Testing

1. Start Authentik and create an OAuth2 application named "aqualog"
2. Create a service account or user in Authentik
3. Use the client credentials or resource owner password flow to get a token:

```bash
curl -X POST https://authentikserver:9443/application/o/token/ \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password&username=<user>&password=<pass>&client_id=<client_id>&client_secret=<secret>&audience=aqualog-api"
```

4. Use the returned token in requests:

```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/calculate/dose/salinity?volume=100&current=30&target=35
```

### Endpoint Authentication

- **Protected**: `/api/v1/calculate/dose/salinity` - Requires valid OAuth2 token
- **Unprotected**: `/api/v1/live`, `/api/v1/ready` - Health checks, no authentication required

### Testing

Run tests with:

```bash
pytest -q --cov=aqualog_api --cov-report=term-missing
```

All endpoints are tested with mock OAuth2 tokens. The test suite includes:
- Valid token scenarios
- Invalid/expired token rejection
- Unauthenticated health endpoint access
