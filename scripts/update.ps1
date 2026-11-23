# Обновление до последней версии из GitHub
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
git pull
uv sync --frozen --no-dev
Write-Host "Обновлено." -ForegroundColor Green
