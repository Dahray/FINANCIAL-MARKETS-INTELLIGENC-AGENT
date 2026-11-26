# Deployment, Database Backup, n8n Automation & Maintenance Runbook

## 1. Local Development & Full-Stack Execution

### 1.1 Start Database & Cache Containers
```powershell
docker compose up -d db redis
```

### 1.2 Start FastAPI Backend (Terminal 1)
```powershell
$env:PYTHONPATH="backend"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- FastAPI REST API: `http://localhost:8000/api/v1`
- Interactive Swagger Docs: `http://localhost:8000/docs`

### 1.3 Start Next.js 8-Page Dashboard (Terminal 2)
```powershell
npm install
npm run dev
```
- Institutional Intelligence Dashboard: `http://localhost:3000`

### 1.4 Run Complete 20-Suite Verification & Security Audit
```powershell
python scripts/run_all_tests.py
```

---

## 2. Full Containerized Stack Deployment (Docker Compose)

To run all 6 services (`db`, `redis`, `backend`, `worker`, `frontend`, `n8n`) in containers:
```powershell
docker compose --profile full up -d --build
```

Service Endpoints:
- **Next.js Frontend**: `http://localhost:3000`
- **FastAPI Backend**: `http://localhost:8000`
- **n8n Automation Console**: `http://localhost:5678`
- **PostgreSQL 16 + TimescaleDB + pgvector**: `localhost:5432`
- **Redis 7**: `localhost:6379`

---

## 3. Importing & Activating the 4 n8n Workflows

1. Open the n8n UI at `http://localhost:5678` (authenticate using `N8N_BASIC_AUTH_USER` / `N8N_BASIC_AUTH_PASSWORD` from `.env`).
2. Navigate to **Workflows $\rightarrow$ Import from File** and import the 4 workflows from `n8n/workflows/`:
   - `01_daily_market_and_macro_ingestion.json` (Mon–Fri 16:00 WAT)
   - `02_regulatory_and_competitor_monitor.json` (Every 6 hours)
   - `03_opportunity_radar_alerts.json` (Mon–Fri 17:00 WAT)
   - `04_friday_weekly_intelligence_report.json` (Every Friday 16:30 WAT)
3. Toggle each workflow to **Active**.

---

## 4. Database Backup & Disaster Recovery Procedures

### 4.1 Run Automated Backup
- **Windows PowerShell**:
  ```powershell
  .\scripts\backup_db.ps1
  ```
- **Linux / AWS EC2**:
  ```bash
  chmod +x scripts/backup_db.sh
  ./scripts/backup_db.sh
  ```
Backups are written to `storage/backups/fmip_db_<UTC_TIMESTAMP>.sql(.gz)` with an accompanying `.sha256` cryptographic checksum file. When `AWS_BACKUP_BUCKET` is set in `.env`, backups are automatically uploaded with AES-256 server-side encryption to Amazon S3 (`s3://$AWS_BACKUP_BUCKET/database-backups/`).

### 4.2 Restore from Backup
```powershell
Get-Content storage\backups\fmip_db_<TIMESTAMP>.sql | docker exec -i fmip_timescaledb psql -U fmip_user -d fmip_intelligence
```

---

## 5. Production AWS Deployment Procedure

1. **Provision Infrastructure**:
   - **Compute**: AWS EC2 (`t3.large`, Ubuntu 24.04 LTS, 100 GB GP3 EBS encrypted) or AWS ECS Fargate.
   - **Security Group**: Allow inbound HTTPS (`443`) via AWS Application Load Balancer (ALB) with AWS Certificate Manager (ACM) TLS certificate. Keep ports `5432` (PostgreSQL) and `6379` (Redis) strictly internal to the VPC / Docker bridge network.
   - **S3 Bucket**: Create an encrypted bucket (`fmip-institutional-backups`) for daily `backup_db.sh` cron archives.
2. **Deploy Application**:
   ```bash
   git clone https://github.com/Dahray/FINANCIAL-MARKETS-INTELLIGENC-AGENT.git
   cd FINANCIAL-MARKETS-INTELLIGENC-AGENT
   cp .env.example .env
   # Populate production secrets and API keys in .env
   docker compose --profile full up -d --build
   ```
3. **Configure Daily Crontab Backup on AWS Host**:
   ```bash
   0 2 * * * cd /opt/FINANCIAL-MARKETS-INTELLIGENC-AGENT && ./scripts/backup_db.sh >> /var/log/fmip_backup.log 2>&1
   ```
