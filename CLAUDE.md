# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository context

This is the `aqualog-backend` repo — a FastAPI Python API. It is normally checked out as a **git submodule** inside a parent orchestration repo (`aqualog/`) alongside a sibling `frontend/` submodule and deployment infra (docker-compose, Authentik, Terraform/Kubernetes). Commits/branches here are made and pushed independently of the parent repo, which only tracks a pinned submodule commit.

This repo uses an **OpenSpec spec-driven workflow** (`openspec/specs`, `openspec/changes`, `openspec/config.yaml`), driven by `opsx-*` slash commands defined in both `.github/prompts/*.prompt.md` and mirrored `.github/skills/openspec-*` skill packages. Workflow stages: `explore` (investigation only) → `propose` (creates proposal/design/tasks artifacts) → `apply` (implements tasks, checks off `tasks.md`) → `sync` (merges delta specs into main specs) → `archive` (archives a completed change dir). When editing this workflow, keep the paired prompt and skill files behaviorally in sync.

Versioning uses `commitizen` (conventional commits, `cz_conventional_commits`, `tag_format = v$version`, `version_provider = pep621` off `pyproject.toml`) — commit messages should follow Conventional Commits so version bumps/changelogs stay automatable.

## Commands

All commands run via [Task](https://taskfile.dev) (`Taskfile.yml`) with Poetry underneath:

```bash
task init                          # one-time env setup (./tools/setup.sh)
task server                        # poetry lock/sync + alembic upgrade head + uvicorn --reload on :8001
task test                          # pytest -q --cov=src --cov-report=term-missing --html=artifacts/tests/index.html
task coverage                      # same, plus HTML/XML coverage under artifacts/coverage
task db-migrate                    # alembic upgrade head
task db-migration-new NAME="..."   # alembic revision --autogenerate -m NAME
task up / task down                # docker-compose up/down for this service's own compose stack
task token                         # get a dev Authentik token (./tools/get_token-dev.sh)
task auth-check                    # end-to-end Authentik token issuance + API auth check (./tools/spa)
task build / task publish          # build/push the docker image (also builds mail_proxy image)
```

Run a single test directly with poetry/pytest:

```bash
poetry run pytest tests/test_aquariums.py -k create_aquarium -q
```

Tests require `AQUALOG_APP_ENV=test` (set automatically by `task test`/`task coverage`), which makes `src/db.py` use an in-memory SQLite DB created via `Base.metadata.create_all` (not Alembic). The autouse `reset_db_state` fixture in `tests/conftest.py` disposes and reconfigures the engine before/after every test, so tests never leak state through the module-level engine/session singletons.

There is no configured linter/formatter (no ruff/black/mypy in `pyproject.toml`) — don't invent lint commands.

## Architecture

- **App factory**: `src/app.py::create_app(settings)` builds the FastAPI app — configures JSON-file + console logging, mounts `CORSMiddleware` and `RequestLoggingMiddleware` (stamps `request.state.request_id`), registers global exception handlers (`ValidationError`, `RequestValidationError`, generic `Exception`, `HTTPException`) that all funnel into `error_response`, and includes routers under `/api/{settings.api_version}`. In `dev`/`test` env only, it also mounts `/tests` and `/coverage` as static dirs serving `artifacts/tests` and `artifacts/coverage`. DB initialization happens in the FastAPI `lifespan` handler (`init_database`), which also flips `app.state.readiness.is_ready = True`.
- **Router-per-resource, factory pattern**: each resource module exposes a `build_x_router() -> APIRouter` function (`build_health_router`, `build_calculation_router`, `build_profile_router`, `build_aquarium_router`, `build_aquarium_measurement_router`) that `create_app` includes. New resources should follow this same factory shape rather than a module-level `router` singleton.
- **Repository pattern**: DB access is isolated behind `*Repository` classes (`AquariumRepository`, `AquariumMeasurementRepository`, `UserRepository`), each constructed from an injected `Session` (via `Depends(get_session)`). Route handlers never touch SQLAlchemy queries directly. Repositories commit their own transactions and translate `IntegrityError` into domain errors (e.g. `DuplicateAquariumNameError`), which routers catch and turn into `HTTPException`s.
- **Response envelope**: every endpoint response goes through `src/responses.py::success_response`/`error_response`, producing `{"success": bool, "request_id": ..., "data" | "error": {"code", "message"}}`. The global exception handlers in `app.py` produce the same shape for unhandled errors. Preserve this envelope for any new endpoint — including validation-error and 401/500 paths.
- **Auth**: `src/auth.py` implements OAuth2/OIDC bearer-token auth against Authentik. `get_jwks_keys` fetches the issuer's `.well-known/openid-configuration` then its `jwks_uri`, caching the key set for 1 hour in module-level globals. `validate_token` decodes with `joserfc`, then manually checks issuer (trailing-slash-normalized), audience (string or list), and expiry. The `get_current_user` FastAPI dependency wraps this, then resolves/creates a local `User` row via `user_service.resolve_or_create_authenticated_user`, returning an `AuthenticatedUser` (wraps the local `User` + token claims). Protected routes depend on `get_current_user`; health endpoints (`/api/v1/live`, `/api/v1/ready`) are intentionally unprotected.
- **Settings**: `src/config.py::Settings` (pydantic-settings) reads env vars prefixed `AQUALOG_` (e.g. `AQUALOG_OAUTH_ISSUER_URL`, `AQUALOG_DATABASE_URL`, `AQUALOG_APP_ENV`). `oauth_audience` falls back to `oauth_client_id` for compatibility with older env files. `app_env` (`dev`/`test`/prod-like) gates dev-only behavior (docs mounts, test/coverage static mounts, sqlite test DB).
- **DB**: `src/db.py` holds the SQLAlchemy engine/session-factory as module-level singletons, configured lazily via `configure_database`/`init_database` (idempotent — a no-op if already configured). Postgres in real deployments (`postgresql://` URLs are rewritten to `postgresql+psycopg://`), migrated via Alembic under `alembic/`; SQLite in-memory for tests, created directly from model metadata. `reset_database()` disposes the engine and clears the singletons — this is what test isolation relies on.
- **Domain models** (`src/models.py`): `User` (unique per `oauth_issuer` + `oauth_subject`), `Aquarium` (unique `owner_user_id` + `name`, cascade-deletes on user delete), `AquariumMeasurement` (unique `aquarium_id` + `parameter` + `measured_at`, cascade-deletes on aquarium delete, stores both normalized `value`/`unit` and original `raw_value`/`raw_unit`). All PKs are UUID strings generated app-side (`uuid4()`), not DB-generated.
- **Mail sending** (e.g. signup confirmation) goes through `mail_proxy/` — a small standalone Node service, built/deployed as its own Docker image alongside the backend (`task build` builds both).

## Testing conventions

- `tests/conftest.py` provides JWT/JWKS test fixtures (`mock_rsa_keys`, `mock_jwks`, `mock_oidc_config`, `create_valid_token`) for exercising the Authentik-backed auth flow without a real IdP — reuse these rather than hand-rolling tokens.
- Repository and router tests are split per resource (e.g. `test_aquarium_repository.py` vs `test_aquariums.py`) — keep that separation for new resources (repository-level tests for query/constraint behavior, router-level tests for HTTP/auth/envelope behavior).
