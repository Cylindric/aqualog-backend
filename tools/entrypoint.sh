#!/bin/bash

# Resolve AQUALOG_DATA_URL nested variables
export AQUALOG_DATABASE_URL=$(eval echo "$AQUALOG_DATABASE_URL")

# List all Env vars starting with AQUALOG_
# env | grep ^AQUALOG_

alembic upgrade head
uvicorn aqualog_api.app:create_app --factory --reload --host 0.0.0.0 --port 8000
