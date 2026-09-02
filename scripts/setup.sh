#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../apps/api-server"
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
[ -f .env ] || cp .env.example .env
cd ../web-admin
npm install
[ -f .env ] || cp .env.example .env
