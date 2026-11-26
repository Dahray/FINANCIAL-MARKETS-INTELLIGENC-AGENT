# ==============================================================================
# SOHCAHTOA FMIP - ONE-COMMAND PLATFORM LAUNCHER (PowerShell)
# ==============================================================================
# Starts:
# 1. Docker Services (TimescaleDB + pgvector, Redis 7, and n8n Workflow Engine)
# 2. FastAPI Backend & 8-Agent Intelligence Engine (http://localhost:8000)
# 3. Next.js 8-Page Institutional Dashboard (http://localhost:3000)

$ErrorActionPreference = "Continue"
$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir

Write-Output "=============================================================================="
Write-Output "SOHCAHTOA FINANCIAL MARKETS INTELLIGENCE PLATFORM - STARTUP"
Write-Output "=============================================================================="

# 1. Start Docker Database, Redis & n8n if Docker Desktop is running
docker info > $null 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Output "[1/3] Starting PostgreSQL (TimescaleDB + pgvector), Redis, and n8n containers..."
    docker compose --profile automation up -d db redis n8n
} else {
    Write-Output "[1/3] Note: Docker Desktop daemon is not running (using local persistent SQL database storage/fmip_local.db)."
}

# 2. Launch FastAPI Backend in a new PowerShell window on port 8000
Write-Output "[2/3] Launching FastAPI Backend & 8-Agent Engine on http://localhost:8000 ..."
$BackendCmd = "Set-Location '$RootDir'; `$env:PYTHONPATH='backend'; python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $BackendCmd

# 3. Install Frontend Dependencies (if needed) and Launch Next.js Dashboard on port 3000
if (-not (Test-Path "$RootDir\node_modules") -and -not (Test-Path "$RootDir\frontend\node_modules")) {
    Write-Output "[3/3] Installing Next.js Frontend packages (first-time setup)..."
    npm install
}

Write-Output "[3/3] Launching Next.js 8-Page Institutional Dashboard on http://localhost:3000 ..."
Write-Output "=============================================================================="
Write-Output "  - Intelligence Dashboard : http://localhost:3000"
Write-Output "  - FastAPI Swagger Docs   : http://localhost:8000/docs"
Write-Output "  - n8n Workflow Console   : http://localhost:5678"
Write-Output "  - Login Email            : Afolabi.azeez@sohcahtoaholdings.com"
Write-Output "  - Login Password         : SohCahToa@Admin2026!"
Write-Output "=============================================================================="

npm run dev
