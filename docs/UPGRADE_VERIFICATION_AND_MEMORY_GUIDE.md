# FMIP Institutional Upgrade Guide: Live Data Verification Engine & Historical Research Memory

## 1. Architecture Summary

The upgraded Financial Markets Intelligence Platform (FMIP v2.0) enforces strict separation between **official verified data ingestion**, **deterministic Python quantitative calculations**, **historical research memory**, and **AI synthesis**:

```
OFFICIAL TIER-1 SOURCES (CBN REST APIs, NGX, FMDQ, DMO, NBS, FRED)
        ↓
PROVIDER INGESTION (CBNDataProvider, Global & Search Providers)
        ↓
CENTRALIZED VERIFICATION ENGINE (Tier 1 > Tier 2 > Tier 3, Freshness SLAs, Discrepancy Audit)
        ↓
HISTORICAL DATABASE (28 SQLAlchemy ORM Tables + Alembic Migration 002)
        ↓
DETERMINISTIC PYTHON QUANT & FORECAST EVALUATION ENGINE (MAE, RMSE, MAPE, Directional Accuracy)
        ↓
8-AGENT RESEARCH WORKFLOW + HISTORICAL COMPARISON ("WHAT HAS CHANGED SINCE OUR LAST REPORT?")
        ↓
NEXT.JS INSTITUTIONAL DASHBOARD, 16-SECTION PDF/EXCEL REPORTS & n8n AUTOMATION (Daily/Weekly/Monthly/Quarterly)
```

## 2. Live Official CBN REST APIs Integrated

`CBNDataProvider` (`backend/app/providers/nigerian/nigerian_providers.py`) directly ingests live official JSON from `https://www.cbn.gov.ng`:

- `/api/GetAllMoneyMarketIndicators` → **CBN MPR (23.00%)**, Interbank Call Rate, Prime & Maximum Lending Rates, Savings Deposit Rate (24-month official history)
- `/api/GetAllInflationRates` → **Nigeria Headline CPI YoY (14.06%)**, Food Inflation YoY (19.13%), Core CPI YoY (10.78%)
- `/api/GetAllNFEM_Rates` → **Official NFEM USD/NGN Closing, High, Low, Weighted Avg & Turnover** (60 business days)
- `/api/GetAllReserves` → **Daily Gross & Liquid External Reserves (USD 54.11B)**
- `/api/GetAllCrudeOilPrices` → **Bonny Light Crude Oil Price & Domestic Production (mbpd)**
- `/api/GetAllSecuritiesNTB` → **Live Primary Market Nigerian Treasury Bill 91D / 182D / 364D Stop Rates & Bid-to-Cover Ratios**
- `/api/GetAllCirculars` → **Official CBN Regulatory Circulars with Reference Numbers & Direct PDF URLs**

## 3. Database Migration & New Institutional Memory Tables (Alembic Migration `002`)

Run Alembic migration on PostgreSQL (or let `init_database_schema()` apply non-destructive upgrades automatically):
```powershell
alembic -c backend/alembic.ini upgrade head
```

**10 New Tables Added (`backend/app/models/memory.py`):**
1. `data_discrepancies` — Cross-source discrepancy log & source-hierarchy resolution audit
2. `intelligence_change_log` — Immutable governance trail of data corrections, new findings & evaluations
3. `research_findings` — Unique-ID tracked findings across weekly/monthly/quarterly reports
4. `strategic_recommendations` — Business recommendations with 14-point business cases & review dates
5. `identified_risks` — Persistent institutional risk register with trigger thresholds
6. `forecast_outcomes` — Immutable realized outcome evaluations (separate from original `quant_forecasts`)
7. `research_performance_evaluations` — Periodic accuracy metrics & 9-dimension QA scorecard
8. `opportunity_evaluations` — Opportunity lifecycle transitions (`NEWLY_IDENTIFIED` → `ACTIVE_OPPORTUNITY` → `MATERIALISED` / `INVALIDATED` / `EXPIRED`)
9. `knowledge_graph_nodes` & `knowledge_graph_edges` — Institutional cross-market & regulatory knowledge graph

## 4. New API Endpoints & Dashboard Pages

| Dashboard Page (`http://localhost:3000`) | Backing API Endpoint (`/api/v1/intelligence/...`) | Capability |
| :--- | :--- | :--- |
| **Data Accuracy Monitor** (`/data-accuracy`) | `GET /data-accuracy`, `POST /data-accuracy/audit` | 12-attribute provenance, Freshness SLAs, Stale warnings & Discrepancy Log |
| **Historical & Scenarios** (`/historical-intelligence`) | `GET /historical-comparison`, `POST /scenario-stress-test`, `GET /knowledge-graph` | 1W/1M/3M/6M/1Y comparison, Custom Stress Tester (Base/Bull/Bear) & Knowledge Graph |
| **Forecast Accuracy** (`/forecast-accuracy`) | `GET /forecast-accuracy` | MAE, RMSE, MAPE, Directional Accuracy by Indicator/Horizon/Agent + Immutable Ledger |
| **Research Memory & Log** (`/research-memory`) | `GET /research-memory`, `GET /what-changed` | Searchable Reports, Findings, 14-Pt Business Cases, Risk Register, QA Scorecard & Change Log |

## 5. Continuous Automation (n8n Workflows)

- **Daily**: `01_daily_market_and_macro_ingestion.json`, `02_regulatory_and_competitor_monitor.json`, `03_opportunity_radar_alerts.json`
- **Weekly (Friday 16:30 WAT)**: `04_friday_weekly_intelligence_report.json` (now includes **"WHAT HAS CHANGED SINCE OUR LAST REPORT?"**)
- **Monthly (1st Business Day)**: `05_monthly_market_review.json` → `POST /api/v1/webhooks/n8n/monthly-review`
- **Quarterly (Jan/Apr/Jul/Oct)**: `06_quarterly_financial_outlook.json` → `POST /api/v1/webhooks/n8n/quarterly-outlook`

## 6. Verification Command

```powershell
python backend/tests/integration/test_stage8_verification_and_research_memory.py
```
