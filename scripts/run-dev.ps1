# Roda backend + index com uv. Uso: powershell -ExecutionPolicy Bypass -File scripts/run-dev.ps1
$ErrorActionPreference = "Stop"
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
  # uv instalado via instalador oficial cai aqui; recarrega PATH sem reabrir o terminal
  $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
}
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
  throw "uv nao encontrado. Reabra o PowerShell (instalacao nova) ou use '$env:USERPROFILE\.local\bin\uv.exe' no PATH."
}
$root = Split-Path $PSScriptRoot -Parent
Set-Location "$root\backend"
if (-not (Test-Path ".venv")) { uv venv }
.\.venv\Scripts\Activate.ps1
uv pip install -r requirements.txt
python ..\scripts\build-index.py
python -m uvicorn app.main:app --reload --port 8000
