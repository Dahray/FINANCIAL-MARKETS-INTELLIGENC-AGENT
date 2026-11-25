"""Macroeconomic Indicators, Econometric Correlations, Walk-Forward Backtested Forecasts, and Scenario Analysis Endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.macro import MacroIndicator
from app.models.market import MarketTimeseries
from app.quant.econometrics import compute_correlation_matrix, run_ols_regression
from app.quant.forecasting import generate_verified_forecast
from app.quant.valuation import run_macro_market_scenario_analysis

router = APIRouter(prefix="/macro", tags=["Macroeconomics, Econometrics & Forecasting"])


@router.get("/indicators")
def list_macro_indicators(
    country: Optional[str] = Query(default=None),
    indicator_code: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Retrieve macroeconomic indicators with full Section 4 provenance."""
    stmt = select(MacroIndicator).order_by(MacroIndicator.publication_date.desc())
    if country:
        stmt = stmt.where(MacroIndicator.country == country.upper())
    if indicator_code:
        stmt = stmt.where(MacroIndicator.indicator_code == indicator_code.upper())

    rows = db.execute(stmt.limit(limit)).scalars().all()
    return [
        {
            "id": r.id,
            "indicator_code": r.indicator_code,
            "indicator_name": r.indicator_name,
            "country": r.country,
            "category": r.category,
            "value": float(r.value),
            "previous_value": float(r.previous_value) if r.previous_value is not None else None,
            "currency_or_unit": r.currency_or_unit,
            "reporting_period": r.reporting_period,
            "publication_date": r.publication_date.isoformat(),
            "retrieval_date": r.retrieval_date.isoformat(),
            "source_id": r.source_id,
            "data_frequency": r.data_frequency,
            "verification_status": r.verification_status,
        }
        for r in reversed(rows)
    ]


@router.get("/forecasts/{target_code}")
def get_macro_or_market_forecast(
    target_code: str,
    horizon_steps: int = Query(default=4, ge=1, le=12),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Generate a walk-forward backtested statistical/ML forecast (ARIMA / Holt-Winters ETS / Ridge)
    with Base, Bull, and Bear cases, key assumptions, confidence level, and invalidation factors.
    """
    code_upper = target_code.upper()

    # Check if target is a macro series
    macro_rows = (
        db.execute(
            select(MacroIndicator)
            .where(MacroIndicator.indicator_code == code_upper)
            .order_by(MacroIndicator.publication_date.asc())
        )
        .scalars()
        .all()
    )
    if len(macro_rows) >= 10:
        dates = [r.publication_date for r in macro_rows]
        vals = [float(r.value) for r in macro_rows]
        higher_bull = code_upper not in ("NG_CPI_HEADLINE_YOY", "NG_CPI_FOOD_YOY")
        res = generate_verified_forecast(
            dates=dates,
            values=vals,
            target_code=code_upper,
            target_name=macro_rows[-1].indicator_name,
            currency_or_unit=macro_rows[-1].currency_or_unit,
            horizon_steps=horizon_steps,
            step_days=30,
            forecast_horizon_label=f"{horizon_steps}_MONTHS",
            higher_is_bull=higher_bull,
        )
        return res.to_dict()

    # Otherwise check market time-series
    mkt_rows = (
        db.execute(
            select(MarketTimeseries)
            .where(MarketTimeseries.symbol == code_upper)
            .order_by(MarketTimeseries.publication_date.asc())
        )
        .scalars()
        .all()
    )
    if len(mkt_rows) >= 10:
        dates = [r.publication_date for r in mkt_rows]
        vals = [float(r.value) for r in mkt_rows]
        higher_bull = code_upper != "NGNUSD.NAFEM"
        res = generate_verified_forecast(
            dates=dates,
            values=vals,
            target_code=code_upper,
            target_name=mkt_rows[-1].indicator_name,
            currency_or_unit=mkt_rows[-1].currency_or_unit,
            horizon_steps=horizon_steps,
            step_days=7,
            forecast_horizon_label=f"{horizon_steps}_WEEKS",
            higher_is_bull=higher_bull,
        )
        return res.to_dict()

    raise HTTPException(
        status_code=404,
        detail=f"Target '{target_code}' has fewer than 10 historical observations for walk-forward backtested forecasting.",
    )


@router.get("/econometrics")
def run_market_econometrics(
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Execute cross-asset correlation matrix (NGXASI, NGNUSD.NAFEM, BRENT, GTCO.NG, DANGCEM.NG, NG_OPR_RATE)
    and OLS regression of NGX All-Share Index against Brent Crude, NAFEM FX, and Money Market Rates.
    """
    symbols = ["NGXASI", "NGNUSD.NAFEM", "BRENT", "GTCO.NG", "DANGCEM.NG", "NG_OPR_RATE"]
    series_map: Dict[str, List[float]] = {}
    min_len = 999999

    for sym in symbols:
        rows = (
            db.execute(
                select(MarketTimeseries.value)
                .where(MarketTimeseries.symbol == sym)
                .order_by(MarketTimeseries.publication_date.asc())
            )
            .scalars()
            .all()
        )
        vals = [float(v) for v in rows]
        if len(vals) >= 10:
            series_map[sym] = vals
            min_len = min(min_len, len(vals))

    if len(series_map) < 2 or min_len < 10:
        raise HTTPException(status_code=400, detail="Insufficient aligned series for econometric analysis.")

    aligned = {k: v[-min_len:] for k, v in series_map.items()}
    corr_report = compute_correlation_matrix(aligned)

    ols_report = None
    if "NGXASI" in aligned and len(aligned) >= 3:
        x_vars = {k: v for k, v in aligned.items() if k in ("BRENT", "NGNUSD.NAFEM", "NG_OPR_RATE")}
        if x_vars:
            ols_report = run_ols_regression(
                y_series=aligned["NGXASI"],
                x_series_dict=x_vars,
                dependent_name="NGXASI",
            ).to_dict()

    return {
        "correlation_analysis": corr_report.to_dict(),
        "ols_regression_ngx_drivers": ols_report,
    }


@router.get("/scenarios")
def get_scenario_stress_test(
    portfolio_value_ngn: float = Query(default=10_000_000_000.0, gt=0),
) -> Dict[str, Any]:
    """Execute deterministic multi-asset scenario analysis across 4 institutional macro regimes."""
    return run_macro_market_scenario_analysis(portfolio_value_ngn=portfolio_value_ngn)
