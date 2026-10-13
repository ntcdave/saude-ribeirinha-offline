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
# IP da rede local p/ abrir no celular (mesmo Wi-Fi)
# Ignora VirtualBox host-only (192.168.56.*), WSL, vEthernet e VMware
$ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
  $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" -and $_.IPAddress -notlike "192.168.56.*" -and
  $_.InterfaceAlias -notlike "*VirtualBox*" -and $_.InterfaceAlias -notlike "*vEthernet*" -and
  $_.InterfaceAlias -notlike "*WSL*" -and $_.InterfaceAlias -notlike "*VMware*" -and $_.InterfaceAlias -notlike "*Loopback*"
} | Sort-Object { if ($_.IPAddress -like "192.168.1.*") { 0 } elseif ($_.IPAddress -like "192.168.0.*") { 1 } else { 2 } } | Select-Object -First 1 -ExpandProperty IPAddress)
if (-not $ip) { $ip = "localhost" }
Write-Host ""
Write-Host "=== Saude Ribeirinha Offline ===" -ForegroundColor Green
Write-Host "PC:      http://localhost:8000" -ForegroundColor Cyan
Write-Host "Celular: http://${ip}:8000  (aponte a camera p/ o QR no canto da tela / frontend/qr.png)" -ForegroundColor Yellow
Write-Host "Se o celular nao abrir, libere o firewall uma vez: Allow inbound TCP 8000" -ForegroundColor DarkYellow
Write-Host ""
# 0.0.0.0 = acessivel pelo celular na mesma rede
# --reload-dir app: observa so o codigo, ignora .venv (evita loop infinito de restart do WatchFiles)
python -m uvicorn app.main:app --reload --reload-dir app --port 8000 --host 0.0.0.0
