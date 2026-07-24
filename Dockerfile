FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AQUALOG_APP_ENV=prod \
    AQUALOG_API_VERSION=v1 \
    AQUALOG_LOG_LEVEL=INFO

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --only main --no-interaction --no-ansi

COPY tools/entrypoint.sh /app/entrypoint.sh
COPY alembic.ini /app/alembic.ini
COPY alembic /app/alembic
COPY src ./src

EXPOSE 8000

CMD ["/app/entrypoint.sh"]
