#!/usr/bin/env bash
# ==============================================================================
# FMIP Automated PostgreSQL 16 + TimescaleDB + pgvector Backup Script (Linux/AWS)
# ==============================================================================
set -euo pipefail

TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")
BACKUP_DIR="${BACKUP_DIR:-./storage/backups}"
CONTAINER_NAME="${POSTGRES_CONTAINER:-fmip_timescaledb}"
DB_USER="${POSTGRES_USER:-fmip_user}"
DB_NAME="${POSTGRES_DB:-fmip_intelligence}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

mkdir -p "${BACKUP_DIR}"
BACKUP_FILE="${BACKUP_DIR}/fmip_db_${TIMESTAMP}.sql.gz"
CHECKSUM_FILE="${BACKUP_FILE}.sha256"

echo "[FMIP-BACKUP] Starting PostgreSQL/TimescaleDB backup at ${TIMESTAMP}..."
docker exec "${CONTAINER_NAME}" pg_dump -U "${DB_USER}" -d "${DB_NAME}" --clean --if-exists | gzip -9 > "${BACKUP_FILE}"
sha256sum "${BACKUP_FILE}" > "${CHECKSUM_FILE}"

echo "[FMIP-BACKUP] Backup created: ${BACKUP_FILE}"

# Optional AWS S3 Encrypted Upload (when AWS_BACKUP_BUCKET is configured)
if [[ -n "${AWS_BACKUP_BUCKET:-}" ]]; then
    aws s3 cp "${BACKUP_FILE}" "s3://${AWS_BACKUP_BUCKET}/database-backups/" --sse AES256
    aws s3 cp "${CHECKSUM_FILE}" "s3://${AWS_BACKUP_BUCKET}/database-backups/" --sse AES256
    echo "[FMIP-BACKUP] Uploaded encrypted backup to s3://${AWS_BACKUP_BUCKET}/database-backups/"
fi

# Prune local backups older than RETENTION_DAYS
find "${BACKUP_DIR}" -name "fmip_db_*.sql.gz*" -type f -mtime +"${RETENTION_DAYS}" -delete
echo "[FMIP-BACKUP] Backup cycle completed successfully."
