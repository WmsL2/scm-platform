param(
    [switch]$MultiUser
)

$ErrorActionPreference = "Stop"
Push-Location "$PSScriptRoot/../apps/api-server"
try {
    & .\.venv\Scripts\python -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) { throw "Database migration failed; backend was not started." }
    if ($MultiUser) {
        & .\.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
    }
    else {
        & .\.venv\Scripts\python -m uvicorn app.main:app --reload
    }
}
finally {
    Pop-Location
}

