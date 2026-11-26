# FMIP REST API Documentation (`v1`)

Interactive OpenAPI / Swagger UI is served automatically at **`http://localhost:8000/docs`** and ReDoc at **`http://localhost:8000/redoc`**.

All endpoints are prefixed with `/api/v1` (except `/health`). Every response includes the `X-RateLimit-Remaining` header enforced by the sliding-window rate limiter.

---

## 1. System Health
- **`GET /health`**: Returns application health, active SQLAlchemy dialect (`postgresql` / `sqlite`), and UTC timestamp.

## 2. Authentication & Security (`/api/v1/auth`)
- **`POST /api/v1/auth/login`**: Authenticates email & password (`PBKDF2-HMAC-SHA256`), records a `LOGIN_SUCCESS` or `LOGIN_FAILED` audit log, and returns JWT `access_token`, `refresh_token`, and RBAC role (`EXECUTIVE_ADMIN`, `RESEARCH_ANALYST`, `PORTFOLIO_MANAGER`, `BOARD_VIEWER`).
- **`GET /api/v1/auth/me`**: (Bearer JWT required) Returns active user profile and role.
- **`GET /api/v1/auth/audit-logs`**: (`EXECUTIVE_ADMIN` role required; returns `403 Forbidden` for lower roles) Lists immutable security and operational audit records.

## 3. Executive Overview (`/api/v1/overview`)
- **`GET /api/v1/overview/dashboard`**: Consolidates the latest Friday report summary, answers to the **5 Core Strategic Questions**, market metrics, sovereign yield curve summary, macro snapshot, **11-Question Analytical Developments**, Top Ranked Opportunities, and Chief Editor quality-gate verdict.

## 4. Financial Markets & Quantitative Analytics (`/api/v1/markets`)
- **`GET /api/v1/markets/timeseries`**: Query params: `symbol` (e.g., `NGXASI`, `NGNUSD.NAFEM`, `GTCO.NG`, `ZENITHBANK.NG`, `DANGCEM.NG`, `SEPLAT.NG`, `BRENT`, `BONNYLIGHT`, `SPX`, `NG_OPR_RATE`), `market_region`, `asset_class`, `limit`. Returns verified observations with all 9 mandatory Section 4 provenance fields.
- **`GET /api/v1/markets/analytics/{symbol}`**: Executes deterministic Python quantitative analytics (`compute_market_performance`) returning period returns (`1D`, `1W`, `1M`, `3M`, `6M`, `YTD`, `1Y`), `SMA_20/50/200`, `EMA_12/26`, `RSI_14`, `MACD`, annualized volatility, max drawdown, Sharpe, Sortino, Calmar, Parametric/Historical VaR (`95%`, `99%`), and `independent_check_passed`.
- **`GET /api/v1/markets/yield-curve`**: Fits the parametric **Nelson-Siegel yield curve** across Nigerian Treasury Bills (`91D`, `182D`, `364D`) and FGN Bonds (`2Y`–`30Y`), calculates **Fisher exact real yields**, term spreads, and FGN 10Y benchmark Macaulay/Modified duration, convexity, and DV01.
- **`POST /api/v1/markets/ingest`**: Triggers an immediate provider-abstracted ingestion cycle across CBN, NGX, FMDQ, DMO, SEC, PenCom, NAICOM, FRED, FMP, Alpha Vantage, Tavily, and public financial RSS feeds.

## 5. Macroeconomics, Econometrics & Forecasting (`/api/v1/macro`)
- **`GET /api/v1/macro/indicators`**: Query params: `country`, `indicator_code`, `limit`. Returns verified macroeconomic indicators with full provenance.
- **`GET /api/v1/macro/forecasts/{target_code}`**: Runs expanding-window **Walk-Forward Backtesting** across `ARIMA`, `HOLT_WINTERS_ETS`, and `RIDGE_AUTOREGRESSIVE`, selects the lowest-RMSE model, and returns `base_case`, `bull_case`, `bear_case`, `confidence_level_pct`, `key_assumptions`, `invalidation_factors`, and `historical_backtest` (`rmse`, `mae`, `mape_pct`, `directional_accuracy_pct`).
- **`GET /api/v1/macro/econometrics`**: Computes aligned Pearson & Spearman correlation matrices with two-tailed $p$-values and multi-factor OLS regression of `NGXASI` against global and domestic macro drivers.
- **`GET /api/v1/macro/scenarios`**: Executes deterministic 4-regime multi-asset portfolio stress testing (`BASE_CASE`, `BULL_CASE_DISINFLATION_RALLY`, `BEAR_CASE_INFLATION_MPR_SHOCK`, `TAIL_RISK_OIL_AND_FX_STRESS`).

## 6. Investment & Strategic Opportunity Radar (`/api/v1/opportunities`)
- **`GET /api/v1/opportunities`**: Query params: `opportunity_class` (`INVESTMENT_OPPORTUNITY` | `STRATEGIC_BUSINESS_OPPORTUNITY`), `radar_category`, `target_business_line`, `min_score`. Returns ranked opportunities with 7-dimension scores, thesis, assumptions, risk assessment, and 10-criterion strategic evaluation matrix.

## 7. Competitive Intelligence (`/api/v1/competitors`)
- **`GET /api/v1/competitors/profiles`**: Lists competitor profiles across all 9 financial services categories.
- **`GET /api/v1/competitors/events`**: Lists tracked competitor moves, what they are doing differently, implications for our business, and counter-strategies.

## 8. Regulatory Monitor & Source Register (`/api/v1/regulatory`)
- **`GET /api/v1/regulatory/events`**: Query param: `regulator_code` (`CBN`, `SEC_NG`, `PENCOM`, `NAICOM`, `NGX`, `FMF_NG`). Returns official circulars, policy summaries, compliance implications, capital impact, and business opportunities.
- **`GET /api/v1/regulatory/source-register`**: Returns the complete immutable Source Register with reliability tiers and epistemic classifications.

## 9. Weekly Reports, PDF/Excel Exports & Archive (`/api/v1/reports`)
- **`GET /api/v1/reports`**: Lists generated Friday-to-Friday Weekly Intelligence Reports.
- **`POST /api/v1/reports/generate`**: Runs all 8 LangGraph agents, generates the 16-section PDF and 8-sheet Excel workbook, archives to Google Drive, and delivers via Gmail.
- **`GET /api/v1/reports/{report_code}`**: Retrieves full 16-section JSON payload for a specific report (use `latest` for most recent).
- **`GET /api/v1/reports/{report_code}/download/pdf`**: Downloads the generated 16-section `.pdf` file.
- **`GET /api/v1/reports/{report_code}/download/excel`**: Downloads the generated 8-sheet `.xlsx` data workbook.
- **`GET /api/v1/reports/archive/search`**: Keyword and document-type search across the research archive.

## 10. Executive AI Research Assistant (`/api/v1/assistant`)
- **`POST /api/v1/assistant/ask`**: Body: `{"question": "..."}`. Executes `pgvector` 768-dim semantic search + live quantitative database lookup to return an institutional markdown response with inline citations, retrieved evidence chunks, and Source Register references.

## 11. n8n Automation Webhooks & Preferences (`/api/v1/webhooks`)
- **`POST /api/v1/webhooks/n8n/daily-market-ingestion`**
- **`POST /api/v1/webhooks/n8n/regulatory-monitor`**
- **`POST /api/v1/webhooks/n8n/opportunity-alerts`**
- **`POST /api/v1/webhooks/n8n/friday-weekly-report`**
- **`GET /api/v1/webhooks/preferences`** & **`PUT /api/v1/webhooks/preferences`**
