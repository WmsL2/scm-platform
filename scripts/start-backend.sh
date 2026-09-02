#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../apps/api-server"
. .venv/bin/activate
alembic upgrade head
uvicorn app.main:app --reload
