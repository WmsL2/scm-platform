$ErrorActionPreference = "Stop"
Push-Location "$PSScriptRoot/../apps/api-server"
& .\.venv\Scripts\python -m alembic upgrade head
& .\.venv\Scripts\python -m uvicorn app.main:app --reload

