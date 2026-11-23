# Установка Златоуста одной командой. Запуск из папки проекта:
#   powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "1/4 Проверяю uv (менеджер Python-окружения)..." -ForegroundColor Cyan
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}

Write-Host "2/4 Ставлю Python 3.12 и зависимости по lock-файлу (первый раз ~2 ГБ, 5-15 минут)..." -ForegroundColor Cyan
uv sync --frozen --no-dev
if ($LASTEXITCODE -ne 0) { throw "Не удалось установить зависимости" }

Write-Host "3/4 Скачиваю модели распознавания речи и видео..." -ForegroundColor Cyan
uv run --no-dev python -m zlatoust.setup_models
if ($LASTEXITCODE -ne 0) { throw "Не удалось скачать модели" }

Write-Host "4/4 Создаю ярлык на рабочем столе..." -ForegroundColor Cyan
$shell = New-Object -ComObject WScript.Shell
$lnk = $shell.CreateShortcut([Environment]::GetFolderPath("Desktop") + "\Златоуст.lnk")
$lnk.TargetPath = "$root\.venv\Scripts\pythonw.exe"
$lnk.Arguments = "-m zlatoust"
$lnk.WorkingDirectory = $root
$lnk.Description = "Тренажёр публичных выступлений"
$lnk.IconLocation = "$root\assets\icon.ico,0"
$lnk.Save()

Write-Host "Готово. Запускайте ярлык «Златоуст» на рабочем столе." -ForegroundColor Green
