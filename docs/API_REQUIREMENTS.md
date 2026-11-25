# External API Requirements, Nigerian Data Providers, Cost Analysis & Roadmap

## 1. External API Requirements Matrix

FMIP uses a **Provider Abstraction Architecture** (`app/providers/base.py`) so that any market data, macroeconomic, search, or regulatory provider can be added, upgraded, or swapped without modifying agent logic or quantitative analytics.

### 1.1 Commercial & Cloud APIs Requiring Credentials

| Provider | Environment Variable(s) | Primary Purpose in FMIP | Free Tier Availability | Paid Institutional Tier | Setup URL |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Google Gemini API** | `GEMINI_API_KEY` | Primary LLM reasoning (`gemini-2.5-pro`, `gemini-2.5-flash`) for all 8 agents & `text-embedding-004` (768-dim) for `pgvector` RAG. | Yes (Google AI Studio Free Tier with rate limits) | Pay-as-you-go via Google Cloud / Vertex AI (`~$1.25 / 1M input tokens`) | `https://aistudio.google.com/apikey` |
| **Tavily Search API** | `TAVILY_API_KEY` | Deep web research for Nigerian/African financial news, competitor events, M&A, and regulatory announcements with full-text extraction. | Yes (`1,000 searches/month` free) | Project (`$30/mo` for 4,000 searches) or Bootstrap (`$100/mo` for 15,000 searches) | `https://app.tavily.com` |
| **Google Custom Search API** | `GOOGLE_SEARCH_API_KEY`, `GOOGLE_SEARCH_ENGINE_ID` | Secondary/fallback targeted search across `.gov.ng` and official financial domains (`cbn.gov.ng`, `sec.gov.ng`, `ngxgroup.com`). | Yes (`100 queries/day` free) | `$5 per 1,000 queries` | `https://programmablesearchengine.google.com` |
| **Financial Modeling Prep (FMP)** | `FMP_API_KEY` | Global & emerging-market equities, indices, commodities, FX rates, company financial statements, ratios, and economic calendars. | Yes (`250 calls/day` free tier) | Starter (`$22/mo`), Professional (`$59/mo`), Enterprise (`$149/mo`) | `https://site.financialmodelingprep.com/developer` |
| **Alpha Vantage API** | `ALPHA_VANTAGE_API_KEY` | Global FX pairs (`USD/NGN`, `EUR/USD`, `GBP/USD`), Brent/WTI crude oil, gold, agricultural commodities, and technical series. | Yes (`25 requests/day` free tier) | `$49.99/mo` (75 req/min, unlimited daily) | `https://www.alphavantage.co/support/#api-key` |
| **FRED API (St. Louis Fed)** | `FRED_API_KEY` | Global macro indicators (US CPI, Fed Funds Rate, SOFR, 2Y/10Y/30Y US Treasury yields, DXY, World Bank/IMF African macro series hosted on FRED). | **100% Free** (Unlimited with free API key) | Free (`$0/mo`) | `https://fred.stlouisfed.org/docs/api/api_key.html` |
| **Google Drive API v3** | `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_DRIVE_REPORTS_FOLDER_ID` | Automated upload and structured archiving of weekly Friday PDF reports and Excel data workbooks. | **100% Free** via GCP Service Account | Included with Google Workspace (`$0` API fee) | `https://console.cloud.google.com/apis/library/drive.googleapis.com` |
| **Gmail / SMTP Delivery** | `SMTP_USERNAME`, `SMTP_APP_PASSWORD` | Automated Friday delivery of executive intelligence briefs with PDF & Excel attachments to ExCo and Investment Committee. | **100% Free** with Gmail / Google Workspace App Password | Included with Google Workspace | `https://myaccount.google.com/apppasswords` |

---

## 2. Official Nigerian Financial Market & Regulatory Data Sources

Nigerian financial market data is fragmented across multiple regulatory and self-regulatory bodies. FMIP implements dedicated, resilient adapters under `backend/app/providers/nigerian/` that ingest directly from official publications, RSS feeds, structured tables, and verified market summaries—**never fabricating figures when an endpoint is unavailable**.

| Institution | Adapter Class | Data Collected | Reliability Tier | Public vs. Commercial Feed Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Central Bank of Nigeria (CBN)** | `CBNDataProvider` | Monetary Policy Rate (MPR), Cash Reserve Ratio (CRR), Liquidity Ratio, NAFEM/NFEM Official FX Rates, Gross External Reserves, OMO & NTB Auction Stop Rates, Money Market (OPR/OVN), and Official CBN Circulars (BSD, TED, FPR, PSM). | `TIER_1_OFFICIAL` | Publicly accessible via `cbn.gov.ng` statistical tables, JSON/CSV endpoints, and circular PDF links. |
| **Nigerian Exchange Group (NGX)** | `NGXDataProvider` | NGX All-Share Index (ASI), Market Capitalization, Sector Indices (NGX Banking, NGX Industrial, NGX Oil & Gas, NGX Consumer Goods, NGX Insurance), top blue-chip equities (`DANGCEM`, `AIRTELAFRI`, `MTNN`, `BUACEMENT`, `GTCO`, `ZENITHBANK`, `GEREGU`, `SEPLAT`, `FBNH`, `UBA`, `ACCESSCORP`), and corporate disclosures. | `TIER_1_OFFICIAL` | Daily market snapshot and corporate disclosures publicly accessible; real-time Level-2 tick feeds require commercial NGX X-Gen market data licensing. |
| **FMDQ Securities Exchange** | `FMDQDataProvider` | Nigerian sovereign yield curve (NTBs 91D/182D/364D, FGN Bonds 2Y–30Y), Commercial Papers (CPs), NAFEM FX turnover & fixing rates, and Overnight/Open Repo money market rates. | `TIER_1_OFFICIAL` | Daily market summary tables publicly posted; full historical raw tick feed requires FMDQ Q-ex / e-Markets subscription. |
| **Debt Management Office (DMO)** | `DMODataProvider` | Monthly FGN Bond auction results, quarterly FGN Bond issuance calendars, FGN Savings Bond rates, and Nigeria Total Public Debt Stock (Domestic & External). | `TIER_1_OFFICIAL` | 100% public on `dmo.gov.ng`. |
| **National Bureau of Statistics (NBS)** | `NBSDataProvider` | Monthly CPI & Inflation reports (Headline, Food, Core, Urban/Rural), Quarterly Real GDP & Sectoral growth reports, Capital Importation, Foreign Trade in Goods, and Labor Force statistics. | `TIER_1_OFFICIAL` | 100% public on `nigerianstat.gov.ng` and CBN Statistical Bulletin mirror. |
| **Securities and Exchange Commission (SEC Nigeria)** | `SECNigeriaProvider` | New rules & amendments, CIS (Collective Investment Scheme / Mutual Fund) NAV & AUM filings, capital market circulars, digital asset / VASP regulatory releases, and enforcement actions. | `TIER_1_OFFICIAL` | 100% public on `sec.gov.ng`. |
| **National Pension Commission (PenCom)** | `PenComProvider` | Monthly/Quarterly Pension Fund Assets (AUM) breakdown by asset class (FGN Securities, Domestic Equities, Money Market, Corporate Debt, Private Equity/Infrastructure), RSA fund performance, and investment regulation updates. | `TIER_1_OFFICIAL` | 100% public on `pencom.gov.ng`. |
| **National Insurance Commission (NAICOM)** | `NAICOMProvider` | Prudential guidelines, capital requirement directives, claims settlement bulletins, and insurance sector regulatory circulars. | `TIER_1_OFFICIAL` | 100% public on `naicom.gov.ng`. |

---

## 3. Estimated Infrastructure & API Costs

Below is a realistic monthly cost breakdown across three deployment profiles.

### 3.1 Tier 1: Local Development & Proof-of-Operations (`$0 – $40 / month`)
Suitable for local workstation execution using Docker Compose (`PostgreSQL/TimescaleDB`, `Redis`, `FastAPI`, `Next.js`, `n8n` running locally).
- **Infrastructure**: `$0/mo` (Local Docker Desktop on workstation)
- **Google Gemini API**: `$0 – $15/mo` (Free tier or low pay-as-you-go token usage)
- **Tavily Search API**: `$0/mo` (Free tier: 1,000 searches/month)
- **FRED API**: `$0/mo` (Free)
- **FMP & Alpha Vantage**: `$0 – $22/mo` (Free tiers or FMP Starter)
- **Google Drive & Gmail**: `$0/mo` (Existing Google account / Workspace)
- **Total Estimated Monthly Cost**: **`$0 – $37 / month`**

### 3.2 Tier 2: Standard Institutional Production on AWS (`$215 – $395 / month`)
Recommended production deployment for an investment management firm or holding company executive team (10–50 internal users, daily automated ingestion, weekly Friday reports, continuous Opportunity Radar, and interactive AI Research Assistant).

| Component | AWS / Vendor Specification | Estimated Monthly Cost (USD) |
| :--- | :--- | :--- |
| **Application Compute** | AWS ECS Fargate or EC2 (`t3.large` — 2 vCPU, 8 GB RAM running FastAPI, Next.js, Redis Worker, n8n) | `$65 – $85` |
| **Database (PostgreSQL + TimescaleDB + pgvector)** | Self-managed TimescaleDB-HA on EC2 (`t3.medium` + 100 GB GP3 EBS + daily S3 snapshots) or Managed Timescale Cloud | `$55 – $110` |
| **Redis Cache & Queue** | Containerized Redis with AOF persistence (or AWS ElastiCache `cache.t4g.micro`) | `$0 – $16` |
| **Load Balancer, S3 Backups & CloudWatch Logs** | AWS ALB + S3 encrypted database/report backups (50 GB) + KMS | `$25 – $35` |
| **Google Gemini API (`2.5-pro` + `2.5-flash` + embeddings)** | ~30 daily runs + 4 comprehensive Friday 8-agent runs + ~500 executive RAG queries/month | `$20 – $45` |
| **Tavily Search API** | Project Plan (4,000 deep research queries/month) | `$30` |
| **Financial Modeling Prep (FMP) API** | Starter / Professional Plan | `$22 – $59` |
| **FRED API, Nigerian Official Adapters, Drive & Gmail** | Included / Free | `$0` |
| **Total Estimated Monthly Cost** | **Standard Institutional Production** | **`$217 – $380 / month`** |

### 3.3 Tier 3: Enterprise Holding Company High-Availability Tier (`$750 – $1,450 / month`)
For multi-subsidiary deployment (Asset Management, Investment Banking, Securities Brokerage, Wealth Management) requiring Multi-AZ database failover and optional commercial real-time exchange feeds:
- **AWS Multi-AZ Compute + Managed Database + ElastiCache + WAF**: `$350 – $550/mo`
- **AI & Global APIs (Gemini, Tavily Bootstrap, FMP Enterprise, Alpha Vantage Premium)**: `$300 – $450/mo`
- **Optional Commercial Exchange Subscriptions (NGX X-Gen / FMDQ e-Markets institutional terminal license)**: Billed directly by NGX / FMDQ per institutional agreement.

---

## 4. Seven-Phase Development Roadmap & Verification Gates

| Phase | Core Deliverables | Verification & Testing Gate |
| :--- | :--- | :--- |
| **Phase 1: System Architecture** | System architecture specification, tech stack confirmation, folder structure, 18-table PostgreSQL/TimescaleDB/pgvector schema design, 8-agent LangGraph design, API matrix, cost model, `docker-compose.yml`, `.env.example`, Git repo initialization. | Architecture files verified on disk; Git repository initialized; Docker & Python environment validated. |
| **Phase 2: Backend, Database & Quantitative Engine** | FastAPI app structure, SQLAlchemy 2.0 ORM models (all 18 tables), Alembic migrations, RBAC & JWT security, Prompt Injection Sanitizer, Provider-Abstracted Data Ingestion Service (Nigerian + Global + FRED + Search), and Deterministic Python Quantitative Engine (`app/quant/`). | Unit & integration tests verifying ORM persistence, data quality validation, deduplication, and 100% deterministic math calculations (returns, volatility, Nelson-Siegel yield curve, OLS regression, ARIMA/SARIMAX forecasting & backtesting). |
| **Phase 3: Multi-Agent Intelligence System** | All 8 specialized agents implemented in LangGraph (`agent_1_market` through `agent_8_editor`), tool-calling bindings to the database and quant engine, 11-question development analyzer, Opportunity Radar service, and Chief Research Editor contradiction/citation audit loop. | End-to-end multi-agent orchestration test verifying tool calling, source register traceability, rejection of unsupported claims, and structured Pydantic output compliance. |
| **Phase 4: Institutional Frontend Dashboard** | Next.js + TypeScript + Tailwind + shadcn/ui application with authentication and all 8 mandatory pages (`Overview`, `Nigerian Markets`, `Global Markets`, `Opportunity Radar`, `Competitive Intelligence`, `Regulatory Monitor`, `Research Reports`, `AI Research Assistant`) + interactive financial charts. | TypeScript compilation, production build check, and live API integration verification across all 8 dashboard pages. |
| **Phase 5: Weekly Reporting Engine & Automation** | ReportLab 16-section institutional PDF generator, OpenPyXL multi-tab Excel workbook generator, Google Drive archiver, Gmail HTML + attachment delivery service, and 4 production n8n workflow JSON definitions. | Generate actual Friday-to-Friday 16-section PDF report and multi-sheet Excel workbook from verified database records; inspect file integrity, tables, charts, and citations. |
| **Phase 6: Comprehensive Testing & Security Audit** | Full pytest suite covering financial calculations, data ingestion quality checks, agent citation verification, PDF/Excel report generation, prompt injection defense, rate limiting, and RBAC authentication. | 100% passing automated test suite with zero mocked/hardcoded fake report shortcuts. |
| **Phase 7: Deployment & Operations Runbook** | Production Dockerfiles (`docker/backend/Dockerfile`, `docker/frontend/Dockerfile`), AWS deployment scripts & architecture guide, automated database backup script (`scripts/backup_db.sh`), GitHub Actions CI/CD workflow, and maintenance runbook. | Container build verification, backup/restore script verification, and final readiness audit. |
