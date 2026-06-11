Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "Installation de Veille Asso Jeunesse..." -ForegroundColor Cyan

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python n'est pas trouve. Installez Python depuis https://www.python.org/downloads/windows/ puis cochez Add python.exe to PATH." -ForegroundColor Red
    exit 1
}

python -c "import tkinter" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Tkinter n'est pas disponible. Reinstallez Python depuis python.org avec Tcl/Tk active." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path ".venv")) {
    Write-Host "Creation de l'environnement Python local..."
    python -m venv .venv
}

Write-Host "Installation des dependances..."
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install --no-cache-dir -r requirements.txt

Write-Host ""
Write-Host "Installation terminee." -ForegroundColor Green
Write-Host "Lancez ensuite : .\scripts\launch_gui.ps1"
