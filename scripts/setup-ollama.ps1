# Instala Ollama + Gemma 4 (Windows). Rode 1x antes do hackathon E no dia.
# Uso: powershell -ExecutionPolicy Bypass -File scripts/setup-ollama.ps1
$ErrorActionPreference = "Stop"
Write-Host "== Setup Ollama + Gemma 4 ==" -ForegroundColor Green

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
  Write-Host "Instalando Ollama via winget..." -ForegroundColor Yellow
  winget install -e --id Ollama.Ollama
  $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}

Write-Host "Puxando modelos (isso demora so na 1a vez)..." -ForegroundColor Yellow
ollama pull gemma4:e4b
ollama pull nomic-embed-text

Write-Host "OK. Teste: ollama run gemma4:e4b 'ola, responda em portugues'" -ForegroundColor Green
ollama list
