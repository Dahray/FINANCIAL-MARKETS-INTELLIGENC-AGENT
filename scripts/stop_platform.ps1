# ==============================================================================
# SOHCAHTOA FMIP - ONE-COMMAND PLATFORM SHUTDOWN (PowerShell)
# ==============================================================================
# Cleanly stops:
# 1. Next.js Frontend (port 3000)
# 2. FastAPI Backend + Uvicorn reloader/worker children (port 8000)
# 3. Optional: Docker containers (pass -IncludeDocker to also stop db/redis/n8n)

param(
    [switch]$IncludeDocker
)

$ErrorActionPreference = "Continue"
$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir

Write-Output "=============================================================================="
Write-Output "SOHCAHTOA FINANCIAL MARKETS INTELLIGENCE PLATFORM - SHUTDOWN"
Write-Output "=============================================================================="

# 1. Stop any process listening on ports 3000 or 8000 (and their parent/child trees)
foreach ($p in @(3000, 8000)) {
    $conns = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
    if ($conns) {
        $conns | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object {
            $procId = $_
            $proc = Get-CimInstance Win32_Process -Filter "ProcessId = $procId" -ErrorAction SilentlyContinue
            if ($proc -and $proc.ParentProcessId -and $proc.ParentProcessId -ne $PID) {
                $parent = Get-CimInstance Win32_Process -Filter "ProcessId = $($proc.ParentProcessId)" -ErrorAction SilentlyContinue
                if ($parent -and ($parent.Name -match 'python|node')) {
                    Write-Output "Stopping parent PID $($parent.ProcessId) ($($parent.Name))..."
                    Stop-Process -Id $parent.ProcessId -Force -ErrorAction SilentlyContinue
                }
            }
            Write-Output "Stopping PID $procId on port $p..."
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        }
    }
}

# 2. Stop any lingering uvicorn multiprocessing worker children or next dev processes
Get-CimInstance Win32_Process | Where-Object {
    ($_.ProcessId -ne $PID) -and (
        ($_.Name -match '^python' -and $_.CommandLine -match 'uvicorn\s+app\.main:app|multiprocessing\.spawn') -or
        ($_.Name -match '^node' -and $_.CommandLine -match 'next(\.cmd|\s+dev|\\next\\dist)')
    )
} | ForEach-Object {
    Write-Output "Stopping lingering PID $($_.ProcessId) ($($_.Name))..."
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}

# 3. Optionally stop Docker containers
if ($IncludeDocker) {
    docker info > $null 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Output "Stopping Docker containers (TimescaleDB, Redis, n8n)..."
        docker compose --profile automation stop db redis n8n
    }
}

Start-Sleep -Seconds 1
foreach ($p in @(3000, 8000)) {
    $still = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
    Write-Output "Port ${p}: $(if ($still) {'STILL LISTENING'} else {'CLOSED / FREE'})"
}
Write-Output "=============================================================================="
