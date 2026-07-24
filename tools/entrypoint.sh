#!/bin/bash

alembic upgrade head
uvicorn src.app:create_app --factory --reload --host 0.0.0.0 --port 8000
