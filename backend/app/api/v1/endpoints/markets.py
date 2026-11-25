"""Financial Markets, Sovereign Yield Curves, Quantitative Performance & Data Ingestion Endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.macro import MacroIndicator
from app.models.market import MarketTimeseries, YieldCurvePoint
from app.quant.fixed_income import analyze_yield_curve, compute_bond_risk_metrics
from app.quant.market_metrics import compute_market_performance
from app.services.ingestion_service import IngestionService

router = APIRouter(prefix="/markets", tags=["Financial Markets & Quantitative Analytics"])


@router.get("/timeseries")
def get_market_timeseries(
    symbol: Optional[str] = Query(default=None, description="Filter by ticker/symbol (e.g. NGXASI, NGNUSD.NAFEM, GTCO.NG, BRENT)"),
    market_region: Optional[str] = Query(default=None, description="NIGERIA | AFRICA | GLOBAL"),
    asset_class: Optional[str] = Query(default=None, description="INDEX | EQUITY | FX | FIXED_INCOME | MONEY_MARKET | COMMODITY"),
    limit: int = Query(default=60, ge=1, le=500),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Retrieve verified market time-series observations with full Section 4 provenance."""
    stmt = select(MarketTimeseries).order_by(MarketTimeseries.publication_date.desc())
    if symbol:
        stmt = stmt.where(MarketTimeseries.symbol == symbol.upper())
    if market_region:
        stmt = stmt.where(MarketTimeseries.market_region == market_region.upper())
    if asset_class:
        stmt = stmt.where(MarketTimeseries.asset_class == asset_class.upper())

    rows = db.execute(stmt.limit(limit)).scalars().all()
    return [
        {
            "id": r.id,
            "symbol": r.symbol,
            "indicator_name": r.indicator_name,
            "asset_class": r.asset_class,
            "market_region": r.market_region,
            "value": float(r.value),
            "open_value": float(r.open_value) if r.open_value is not None else None,
            "high_value": float(r.high_value) if r.high_value is not None else None,
            "low_value": float(r.low_value) if r.low_value is not None else None,
            "close_value": float(r.close_value) if r.close_value is not None else float(r.value),
            "volume": float(r.volume) if r.volume is not None else None,
            "currency_or_unit": r.currency_or_unit,
            "reporting_period": r.reporting_period,
            "publication_date": r.publication_date.isoformat(),
            "retrieval_date": r.retrieval_date.isoformat(),
            "source_id": r.source_id,
            "data_frequency": r.data_frequency,
            "verification_status": r.verification_status,
            "quality_flags": r.quality_flags,
        }
        for r in reversed(rows)
    ]


@router.get("/analytics/{symbol}")
def get_symbol_quant_analytics(
    symbol: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Execute deterministic Python quantitative performance & risk analysis for a symbol."""
    rows = (
        db.execute(
            select(MarketTimeseries)
            .where(MarketTimeseries.symbol == symbol.upper())
            .order_by(MarketTimeseries.publication_date.asc())
        )
        .scalars()
        .all()
    )
    if len(rows) < 5:
        raise HTTPException(
            status_code=404,
            detail=f"Symbol '{symbol}' has fewer than 5 historical observations in the database.",
        )

    dates = [r.publication_date for r in rows]
    prices = [float(r.value) for r in rows]
    report = compute_market_performance(dates=dates, prices=prices, symbol=symbol.upper())
    return report.to_dict()


@router.get("/yield-curve")
def get_sovereign_yield_curve(
    curve_name: str = Query(default="NGN_SOVEREIGN_FMDQ"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Retrieve sovereign yield curve points and execute Nelson-Siegel parametric curve fitting,
    Fisher exact real yield computation, and FGN 10Y benchmark duration/convexity analytics.
    """
    rows = (
        db.execute(
            select(YieldCurvePoint)
            .where(YieldCurvePoint.curve_name == curve_name)
            .order_by(YieldCurvePoint.tenor_days.asc())
        )
        .scalars()
        .all()
    )
    if len(rows) < 3:
        raise HTTPException(status_code=404, detail=f"Yield curve '{curve_name}' not found.")

    # Deduplicate by tenor_label (latest observation per tenor)
    latest_by_tenor: Dict[str, YieldCurvePoint] = {}
    for r in rows:
        latest_by_tenor[r.tenor_label] = r
    ordered_pts = sorted(latest_by_tenor.values(), key=lambda x: x.tenor_days)

    # Get latest headline inflation for real yield calculation
    latest_cpi_row = (
        db.execute(
            select(MacroIndicator)
            .where(MacroIndicator.indicator_code == "NG_CPI_HEADLINE_YOY")
            .order_by(MacroIndicator.publication_date.desc())
            .limit(1)
        )
        .scalar_one_or_none()
    )
    cpi_rate = float(latest_cpi_row.value) if latest_cpi_row else 33.88

    curve_report = analyze_yield_curve(
        tenor_years=[float(p.tenor_years) for p in ordered_pts],
        yields_pct=[float(p.value) for p in ordered_pts],
        inflation_rate_pct=cpi_rate,
        curve_name=curve_name,
    )

    fgn_10y_yield = curve_report.fitted_standard_tenors.get("10Y", 20.30)
    bond_risk = compute_bond_risk_metrics(
        face_value=100.0,
        coupon_rate_pct=19.89,
        ytm_pct=fgn_10y_yield,
        years_to_maturity=10.0,
    )

    return {
        "curve_analytics": curve_report.to_dict(),
        "benchmark_10y_bond_risk": bond_risk.to_dict(),
        "raw_points": [
            {
                "tenor_label": p.tenor_label,
                "tenor_days": p.tenor_days,
                "tenor_years": float(p.tenor_years),
                "instrument_type": p.instrument_type,
                "yield_pct": float(p.value),
                "coupon_rate": float(p.coupon_rate) if p.coupon_rate is not None else None,
                "bid_to_cover": float(p.bid_to_cover) if p.bid_to_cover is not None else None,
                "publication_date": p.publication_date.isoformat(),
                "verification_status": p.verification_status,
            }
            for p in ordered_pts
        ],
    }


@router.post("/ingest")
def trigger_data_ingestion(
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Trigger an immediate provider-abstracted data ingestion cycle across all configured providers."""
    return IngestionService.run_live_ingestion_cycle(db)
