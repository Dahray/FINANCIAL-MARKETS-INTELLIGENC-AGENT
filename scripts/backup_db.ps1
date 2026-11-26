# ==============================================================================
# FMIP Automated PostgreSQL 16 + TimescaleDB + pgvector Backup Script (PowerShell)
# ==============================================================================
$ErrorActionPreference = "Stop"

$Timestamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$BackupDir = Join-Path $PSScriptRoot "..\storage\backups"
New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null

$ContainerName = if ($env:POSTGRES_CONTAINER) { $env:POSTGRES_CONTAINER } else { "fmip_timescaledb" }
$DbUser = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "fmip_user" }
$DbName = if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { "fmip_intelligence" }

$BackupFile = Join-Path $BackupDir "fmip_db_$Timestamp.sql"

Write-Output "[FMIP-BACKUP] Executing pg_dump from container '$ContainerName'..."
docker exec $ContainerName pg_dump -U $DbUser -d $DbName --clean --if-exists > $BackupFile

$Hash = (Get-FileHash -Path $BackupFile -Algorithm SHA256).Hash
"$Hash  fmip_db_$Timestamp.sql" | Out-File -FilePath "$BackupFile.sha256" -Encoding utf8

Write-Output "[FMIP-BACKUP] Backup saved to: $BackupFile (SHA-256: $Hash)"
