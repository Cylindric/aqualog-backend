FROM python:3-slim AS builder

# Install Poetry
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && curl -sSL https://install.python-poetry.org | python3 - \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Configure Poetry
ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_CREATE=false
ENV PATH="${PATH}:/root/.local/bin"

WORKDIR /app

# Copy dependency mappings first to utilise Docker build caching
COPY pyproject.toml poetry.lock ./

# Install dependencies (from poetry.lock)
RUN poetry install --only main --no-root

# -----------------------------------------------------------------------------
# OUTPUT STAGE
# -----------------------------------------------------------------------------
FROM python:3-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AQUALOG_APP_ENV=prod \
    AQUALOG_API_VERSION=v1 \
    AQUALOG_LOG_LEVEL=INFO

RUN useradd -m -u 1000 aqualog
USER aqualog
WORKDIR /app

COPY --from=builder --chown=aqualog:aqualog /usr/local/lib/python3.14/site-packages/ /usr/local/lib/python3.14/site-packages/
COPY --from=builder --chown=root:root /usr/local/bin/uvicorn /usr/local/bin/uvicorn
COPY --from=builder --chown=root:root /usr/local/bin/alembic /usr/local/bin/alembic
COPY --from=builder --chown=aqualog:aqualog /app /app

# Read the current version from pyproject.toml and write it to a file for later use
RUN python -c "import tomllib; from pathlib import Path; version = tomllib.loads(Path('pyproject.toml').read_text(encoding='utf-8'))['project']['version']; Path('/app/.container-env').write_text(f'AQUALOG_APP_VERSION={version}\\n', encoding='utf-8')"

# Copy over the source code and other necessary files
COPY --chown=aqualog:aqualog tools/entrypoint.sh /app/entrypoint.sh
COPY --chown=aqualog:aqualog alembic.ini /app/alembic.ini
COPY --chown=aqualog:aqualog alembic /app/alembic
COPY --chown=aqualog:aqualog src ./src

# Expose the internal application port
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/ready', timeout=3)"

# Run the application via the entrypoint script
USER aqualog
CMD ["/app/entrypoint.sh"]
