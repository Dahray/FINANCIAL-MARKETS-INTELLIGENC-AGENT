# Financial Markets Intelligence Platform (FMIP)

An institutional AI-powered financial research, quantitative analytics, competitive/regulatory intelligence, opportunity discovery, and automated weekly reporting platform focused on **Nigeria, African, and international financial markets**.

Engineered to operate as an autonomous financial research department for a financial services holding company, asset management firm, investment management company, and senior executive leadership.

---

## 1. The Three Interconnected Systems

1. **System 1 — Financial Markets Intelligence System**
   - Monitors the Nigerian Exchange (NGX), FMDQ fixed-income & FX markets (NAFEM/NFEM), Treasury Bills (NTBs), FGN Bonds, money markets (OPR/OVN), commodities (Brent, Bonny Light, Gold, Cocoa), and global benchmarks.
   - Tracks Nigerian & global macroeconomic indicators (NBS CPI inflation, GDP, CBN MPR/CRR, gross external reserves, public debt, PMI, trade balances) and official regulatory releases (CBN, SEC Nigeria, NGX, PenCom, NAICOM, FRC, FMF).
   - Executes **100% deterministic Python quantitative analytics** (returns, volatility, VaR, Nelson-Siegel yield curves, Fisher real yields, duration/convexity, Pearson/Spearman correlations, OLS multi-factor regressions, 2-stage DCF equity valuations, scenario stress tests, and walk-forward backtested ARIMA/ETS/Ridge forecasts).

2. **System 2 — Investment & Business Opportunity System**
   - Continuously operates the **Investment Opportunity Radar** across 10 opportunity categories and ranks opportunities across 7 quantitative/qualitative dimensions with an explicit **Evidence Quality Gate**.
   - Monitors 9 categories of financial services competitors (Asset Managers, Commercial Banks, Investment Banks, PFAs, Insurers, Fintechs, Brokerages, Investment Platforms, Wealth Managers).
   - Evaluates strategic business opportunities across 8 financial service lines using a 10-criterion executive matrix.

3. **System 3 — Executive Intelligence Assistant & Weekly Reporting Engine**
   - Supervised by **Agent 8 (Chief Research Editor)**, which audits every numerical claim against the Quantitative Engine, verifies every citation against the `source_register`, challenges weak assumptions, and answers the **5 Core Strategic Questions**:
     1. *Where is the financial market currently?*
     2. *What is changing in the market?*
     3. *Where are the emerging opportunities?*
     4. *What are the risks and threats?*
     5. *What strategic actions should our organisation consider?*
   - Every Friday, generates a **16-section institutional PDF Report** (`ReportLab` / PDF 1.4) and **8-Sheet Excel Data Workbook** (`OpenPyXL`), archives them to **Google Drive**, delivers executive briefs via **Gmail**, and updates the **8-page Next.js Intelligence Dashboard** and **Citation-Backed AI Research Assistant**.

---

## 2. Complete Documentation Index

- [**System Architecture & Multi-Agent Blueprint**](docs/ARCHITECTURE.md)
- [**Database Schema (18 Tables: PostgreSQL 16 + TimescaleDB + pgvector)**](docs/DATABASE_SCHEMA.md)
- [**External API Requirements, Nigerian Data Sources & Cost Analysis**](docs/API_REQUIREMENTS.md)
- [**REST API Documentation (`v1`)**](docs/API_DOCUMENTATION.md)
- [**Deployment, Database Backup, n8n Automation & Maintenance Runbook**](docs/DEPLOYMENT_AND_MAINTENANCE.md)
- [**Live Development Progress Tracker (All 7 Phases)**](PROGRESS_TRACKER.md)

---

## 3. Quick Start & Verification Commands

### Step 1: Copy Environment Configuration
```powershell
Copy-Item .env.example .env
```

### Step 2: Start PostgreSQL (TimescaleDB + pgvector) and Redis
```powershell
docker compose up -d db redis
```

### Step 3: Run All 20 Automated Verification & Security Suites (Phases 2–6)
```powershell
python scripts/run_all_tests.py
```

### Step 4: Start the FastAPI Backend (`http://localhost:8000`)
```powershell
$env:PYTHONPATH="backend"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 5: Start the Next.js 8-Page Institutional Dashboard (`http://localhost:3000`)
```powershell
npm install
npm run dev
```
