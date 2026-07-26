FROM python:3-slim AS builder

WORKDIR /app

# Install Poetry
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && curl -sSL https://install.python-poetry.org | python3 - \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Configure Poetry
ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_CREATE=false
ENV PATH="${PATH}:/root/.local/bin"

# Copy dependency mappings first to utilise Docker build caching
COPY pyproject.toml poetry.lock ./

# Install dependencies (from poetry.lock)
RUN poetry install --only main

# # Resolve the locked dependency set to a plain requirements file so the
# # final image only ever needs pip, not poetry itself.
RUN pip install --no-cache-dir poetry poetry-plugin-export && \
    poetry export --without-hashes --only main -f requirements.txt -o requirements.txt

FROM python:3-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AQUALOG_APP_ENV=prod \
    AQUALOG_API_VERSION=v1 \
    AQUALOG_LOG_LEVEL=INFO

# Update system packages
RUN apt update && apt install -y --no-install-recommends curl && \
    apt clean && \
    rm -rf /var/lib/apt/lists/*

# Setup the working directory
RUN useradd -m -u 1000 aqualog
WORKDIR /app

# Read the current version from pyproject.toml and write it to a file for later use
COPY pyproject.toml ./
RUN python -c "import tomllib; from pathlib import Path; version = tomllib.loads(Path('pyproject.toml').read_text(encoding='utf-8'))['project']['version']; Path('/app/.container-env').write_text(f'AQUALOG_APP_VERSION={version}\\n', encoding='utf-8')"

COPY --from=builder /app/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy over the source code and other necessary files
COPY tools/entrypoint.sh /app/entrypoint.sh
COPY alembic.ini /app/alembic.ini
COPY alembic /app/alembic
COPY src ./src

# Install the project (now that code is copied)
# RUN poetry install --only mai'n
RUN chown -R aqualog:aqualog /app

# Expose the internal application port
EXPOSE 8000

# HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
#   CMD curl -f http://localhost:8000/api/v1/ready || exit 1

# Run the application via the entrypoint script
USER aqualog
CMD ["/app/entrypoint.sh"]
