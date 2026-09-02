$ErrorActionPreference = "Stop"
Push-Location "$PSScriptRoot/../apps/api-server"
python -m venv .venv
& .\.venv\Scripts\python -m pip install --upgrade pip
& .\.venv\Scripts\python -m pip install -e ".[dev]"
if (!(Test-Path .env)) { Copy-Item .env.example .env }
Pop-Location
Push-Location "$PSScriptRoot/../apps/web-admin"
npm install
if (!(Test-Path .env)) { Copy-Item .env.example .env }
Pop-Location

