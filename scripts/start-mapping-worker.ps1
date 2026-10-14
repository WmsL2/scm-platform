param()

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Push-Location "$root\apps\api-server"
try {
    & .\.venv\Scripts\python.exe -m app.jobs.task_worker --queue mapping
}
finally {
    Pop-Location
}
