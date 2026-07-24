#!/bin/bash

# List all Env vars starting with AQUALOG_
# env | grep ^AQUALOG_

alembic upgrade head
uvicorn src.app:create_app --factory --reload --host 0.0.0.0 --port 8000
