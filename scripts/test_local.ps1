Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "L'environnement .venv est absent. Lancez d'abord : .\scripts\install.ps1" -ForegroundColor Red
    exit 1
}

Write-Host "Validation de la configuration locale..."
& ".\.venv\Scripts\python.exe" "src\main.py" --check-config --dry-run

Write-Host ""
Write-Host "Dry-run et generation de preview.html..."
& ".\.venv\Scripts\python.exe" "src\main.py" --dry-run --render-output preview.html

Write-Host ""
Write-Host "Test local termine. Ouvrez preview.html pour verifier le mail." -ForegroundColor Green
