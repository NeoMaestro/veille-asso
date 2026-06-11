Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "L'environnement .venv est absent. Lancez d'abord : .\scripts\install.ps1" -ForegroundColor Red
    exit 1
}

& ".\.venv\Scripts\python.exe" "src\gui.py"
