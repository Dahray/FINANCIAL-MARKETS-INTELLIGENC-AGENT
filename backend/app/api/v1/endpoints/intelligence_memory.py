"""
Institutional Data Verification, Historical Research Memory, Forecast Accuracy,
Knowledge Graph & Interactive Scenario Stress-Testing Endpoints
(Parts 1, 2, 3, 5 & Ultimate Product Vision).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.forecast_evaluation_service import ForecastEvaluationService
from app.services.ingestion_service import IngestionService
from app.services.research_memory_service import ResearchMemoryService
from app.services.verification_service import FinancialDataVerificationEngine

router = APIRouter(
    prefix="/intelligence",
    tags=["Data Accuracy, Historical Memory, Forecast Evaluation & Knowledge Graph"],
)


class CustomScenarioRequest(BaseModel):
    mpr_shock_bps: float = Field(default=0.0, ge=-1000, le=1000)
    inflation_shock_bps: float = Field(default=0.0, ge=-1500, le=2000)
    fx_depreciation_pct: float = Field(default=0.0, ge=-40, le=100)
    crude_oil_price_usd: float = Field(default=85.0, ge=20, le=200)
    us_fed_shock_bps: float = Field(default=0.0, ge=-500, le=500)
    govt_borrowing_shock_pct: float = Field(default=0.0, ge=-50, le=100)
    portfolio_value_ngn: float = Field(default=10_000_000_000.0, gt=0)


@router.get("/data-accuracy")
def get_data_accuracy_monitor(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Part 5A: Data Accuracy Monitor.
    Returns every tracked macro, market, and yield curve indicator with all 12 mandatory
    provenance attributes, Freshness SLA warnings, and Cross-Source Discrepancy records.
    """
    return FinancialDataVerificationEngine.get_data_accuracy_monitor(db)


@router.post("/data-accuracy/audit")
def run_live_verification_and_discrepancy_audit(
    force_live_fetch: bool = Query(default=True),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Trigger a live official CBN/FRED/Market verification refresh, reclassify any stale
    archival rows, resolve cross-source discrepancies via Tier 1 > Tier 2 > Tier 3 hierarchy,
    and return the refreshed Data Accuracy Monitor.
    """
    ingest_res: Dict[str, Any] = {}
    if force_live_fetch:
        ingest_res = IngestionService.run_live_ingestion_cycle(db, force=True, cooldown_seconds=0)
    else:
        FinancialDataVerificationEngine.mark_legacy_seed_records_as_archival(db)
        FinancialDataVerificationEngine.run_discrepancy_detection_and_resolution(db)

    monitor = FinancialDataVerificationEngine.get_data_accuracy_monitor(db)
    return {
        "status": "verified",
        "ingestion_summary": ingest_res,
        "accuracy_monitor": monitor,
    }


@router.get("/historical-comparison")
def get_historical_market_comparison(
    horizon: str = Query(default="1M", pattern="^(1W|1M|3M|6M|1Y)$"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Part 5B: Historical Market & Macro Indicator Comparison across 1W, 1M, 3M, 6M, and 1Y."""
    return ResearchMemoryService.compare_indicators_across_horizons(db=db, horizon=horizon)


@router.get("/research-memory")
def get_searchable_research_memory(
    q: str = Query(default=""),
    lookback: str = Query(default="ALL"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Part 5C & Part 5E: Searchable Historical Research Archive & Intelligence Change Log
    (reports, persistent findings, strategic recommendations, 14-pt business cases, risks,
    opportunity lifecycles, and governance change log).
    """
    return ResearchMemoryService.get_searchable_research_memory(db=db, q=q, lookback=lookback)


@router.get("/forecast-accuracy")
def get_forecast_accuracy_dashboard(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Part 2.4 & Part 5D: Forecast Performance Dashboard.
    Computes MAE, RMSE, MAPE, Directional Accuracy, and Band Hit Rate across indicators,
    horizons, individual agents, and time periods without modifying immutable original forecasts.
    """
    return ForecastEvaluationService.get_forecast_accuracy_dashboard(db)


@router.get("/what-changed")
def get_what_has_changed_since_last_report(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Part 3.1: Live 'WHAT HAS CHANGED SINCE OUR LAST REPORT?' comparative intelligence brief."""
    return ResearchMemoryService.build_weekly_comparison_context(db)


@router.get("/knowledge-graph")
def get_institutional_knowledge_graph(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Vision #3: Institutional Knowledge Graph connecting indicators, regulations, opportunities & outcomes."""
    return ResearchMemoryService.get_knowledge_graph(db)


@router.post("/scenario-stress-test")
def run_custom_scenario_stress_test(
    payload: CustomScenarioRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Vision #4: Interactive Custom Scenario Planning & Base/Bull/Bear Stress Testing Engine."""
    return ResearchMemoryService.run_custom_scenario_stress_test(
        db=db,
        mpr_shock_bps=payload.mpr_shock_bps,
        inflation_shock_bps=payload.inflation_shock_bps,
        fx_depreciation_pct=payload.fx_depreciation_pct,
        crude_oil_price_usd=payload.crude_oil_price_usd,
        us_fed_shock_bps=payload.us_fed_shock_bps,
        govt_borrowing_shock_pct=payload.govt_borrowing_shock_pct,
        portfolio_value_ngn=payload.portfolio_value_ngn,
    )


@router.post("/ingest-pdf")
async def ingest_institutional_pdf_report(
    file: UploadFile = File(...),
    title: Optional[str] = Query(default=None),
    source_code: str = Query(default="CBN_OFFICIAL"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Ingest and analyze an external institutional PDF report (e.g., CBN MPC Communique,
    NBS CPI/GDP release, DMO Debt Bulletin, IMF WEO, or Market Research PDF), sanitize
    against prompt injection, extract numerical metrics/tables, and index 768-dim chunks.
    """
    from app.services.pdf_research_parser import InstitutionalPDFResearchParser

    pdf_bytes = await file.read()
    return InstitutionalPDFResearchParser.ingest_pdf_into_research_memory(
        db=db,
        pdf_bytes=pdf_bytes,
        filename=file.filename or "institutional_report.pdf",
        title=title,
        source_code=source_code,
    )

