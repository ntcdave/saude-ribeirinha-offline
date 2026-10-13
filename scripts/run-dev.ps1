# Roda backend + index. Uso: powershell -ExecutionPolicy Bypass -File scripts/run-dev.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location "$root\backend"
if (-not (Test-Path ".venv")) { python -m venv .venv }
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts/build-index.py
python -m uvicorn app.main:app --reload --port 8000
