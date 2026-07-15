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

COPY aqualog_api ./aqualog_api

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "aqualog_api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]