#!/bin/bash

set -a
export AQUALOG_APP_VERSION=0.0.0
if [ -f .container-env ]; then
    source .container-env
fi
set +a

alembic upgrade head
uvicorn src.app:create_app --factory --reload --host 0.0.0.0 --port 8000
