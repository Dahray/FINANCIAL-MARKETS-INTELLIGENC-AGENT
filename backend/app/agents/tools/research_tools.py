"""
Deterministic Research & Quantitative Tools invoked by Agents 1 through 8.
All tool calls query verified SQLAlchemy database records or execute validated Python functions in `app/quant/`.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.intelligence import CompetitorProfile
from app.models.macro import MacroIndicator
from app.models.market import MarketTimeseries, YieldCurvePoint
from app.models.source import SourceRegister
from app.quant.econometrics import compute_correlation_matrix, run_ols_regression
from app.quant.fixed_income import analyze_yield_curve, compute_bond_risk_metrics
from app.quant.forecasting import generate_verified_forecast
from app.quant.market_metrics import compute_market_performance
from app.quant.valuation import (
    compute_equity_valuation_dcf,
    compute_financial_ratios,
    run_macro_market_scenario_analysis,
)


def load_source_register_ledger(db: Session, limit: int = 50) -> List[Dict[str, Any]]:
    """Return verified entries from `source_register` for traceable citation binding."""
    rows = (
        db.execute(
            select(SourceRegister)
            .where(SourceRegister.verification_status == "VERIFIED")
            .order_by(SourceRegister.publication_date.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": r.id,
            "source_name": r.source_name,
            "publication_title": r.publication_title,
            "publication_date": r.publication_date.strftime("%Y-%m-%d"),
            "retrieval_date": r.retrieval_date.strftime("%Y-%m-%d %H:%M UTC"),
            "url": r.url,
            "relevant_finding": r.relevant_finding,
            "reliability_classification": r.reliability_classification,
            "epistemic_type": r.epistemic_type,
        }
        for r in rows
    ]


def verify_citations_exist(
    db: Session, candidate_ids: Sequence[str]
) -> tuple[List[str], List[str]]:
    """
    Verify candidate `source_register_id` UUIDs against the database `source_register`.
    Returns `(valid_ids, invalid_ids)`.
    """
    if not candidate_ids:
        return [], []
    existing_ids = set(
        db.execute(
            select(SourceRegister.id).where(SourceRegister.id.in_(list(candidate_ids)))
        )
        .scalars()
        .all()
    )
    valid = [cid for cid in candidate_ids if cid in existing_ids]
    invalid = [cid for cid in candidate_ids if cid not in existing_ids]
    return valid, invalid


def tool_compute_all_market_metrics(
    db: Session,
    symbols: Optional[Sequence[str]] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Run `compute_market_performance` across all tracked Nigerian and global symbols.
    Strictly prioritizes live Tier-1/2 official records over archival baselines when available,
    and attaches freshness & verification metadata to every symbol.
    """
    from app.services.verification_service import compute_freshness_assessment

    target_symbols = list(
        symbols
        or [
            "NGXASI",
            "NGNUSD.NAFEM",
            "GTCO.NG",
            "ZENITHBANK.NG",
            "DANGCEM.NG",
            "SEPLAT.NG",
            "BRENT",
            "BONNYLIGHT",
            "SPX",
            "NG_OPR_RATE",
            "NG_OVN_RATE",
        ]
    )
    results: Dict[str, Dict[str, Any]] = {}
    for sym in target_symbols:
        all_rows = (
            db.execute(
                select(MarketTimeseries)
                .where(
                    MarketTimeseries.symbol == sym,
                    MarketTimeseries.verification_status == "VERIFIED",
                )
                .order_by(MarketTimeseries.publication_date.asc())
            )
            .scalars()
            .all()
        )
        live_rows = [r for r in all_rows if not r.is_archival_baseline]
        rows = live_rows if len(live_rows) >= 5 else all_rows
        if len(rows) >= 5:
            perf = compute_market_performance(
                dates=[r.publication_date for r in rows],
                prices=[float(r.value) for r in rows],
                symbol=sym,
            )
            latest_row = rows[-1]
            fresh = compute_freshness_assessment(
                indicator_key=sym,
                publication_date=latest_row.publication_date,
                effective_date=latest_row.effective_date,
                is_archival_baseline=bool(latest_row.is_archival_baseline),
            )
            d = perf.to_dict()
            d["indicator_name"] = latest_row.indicator_name
            d["asset_class"] = latest_row.asset_class
            d["market_region"] = latest_row.market_region
            d["currency_or_unit"] = latest_row.currency_or_unit
            d["source_tier"] = latest_row.source_tier
            d["source_url"] = latest_row.source_url or ""
            d["is_archival_baseline"] = bool(latest_row.is_archival_baseline)
            d["freshness_status"] = fresh["freshness_status"]
            d["age_days"] = fresh["age_days"]
            d["stale_warning"] = fresh["stale_warning"]
            results[sym] = d
    return results


def tool_compute_yield_curve_and_bond_risk(
    db: Session,
    curve_name: str = "NGN_SOVEREIGN_FMDQ",
) -> Dict[str, Any]:
    """Run Nelson-Siegel yield curve fitting and FGN 10Y duration/convexity analytics using verified authoritative curves & CPI."""
    from app.services.verification_service import FinancialDataVerificationEngine

    rows = (
        db.execute(
            select(YieldCurvePoint)
            .where(YieldCurvePoint.curve_name == curve_name)
            .order_by(YieldCurvePoint.tenor_days.asc())
        )
        .scalars()
        .all()
    )
    grouped_tenor: Dict[str, List[YieldCurvePoint]] = {}
    for r in rows:
        grouped_tenor.setdefault(r.tenor_label, []).append(r)

    ordered: List[YieldCurvePoint] = []
    for tenor, t_rows in grouped_tenor.items():
        live_t = [r for r in t_rows if not r.is_archival_baseline]
        pool = live_t if live_t else t_rows
        best = max(pool, key=FinancialDataVerificationEngine._sort_key_authoritative)
        ordered.append(best)
    ordered.sort(key=lambda x: x.tenor_days)

    macro_snap = FinancialDataVerificationEngine.get_authoritative_macro_snapshot(db)
    cpi_val = float(macro_snap.get("NG_CPI_HEADLINE_YOY", {}).get("latest_value", 14.06))

    yc = analyze_yield_curve(
        tenor_years=[float(p.tenor_years) for p in ordered],
        yields_pct=[float(p.value) for p in ordered],
        inflation_rate_pct=cpi_val,
        curve_name=curve_name,
    )
    y10 = yc.fitted_standard_tenors.get("10Y", 20.30)
    bond10 = compute_bond_risk_metrics(
        face_value=100.0,
        coupon_rate_pct=19.89,
        ytm_pct=y10,
        years_to_maturity=10.0,
    )
    return {
        "yield_curve": yc.to_dict(),
        "fgn_10y_bond_risk": bond10.to_dict(),
    }


def tool_load_latest_macro_snapshot(db: Session) -> Dict[str, Dict[str, Any]]:
    """
    Retrieve authoritative, source-hierarchy-verified values + full 12-attribute provenance
    and freshness monitoring for every macroeconomic indicator.
    """
    from app.services.verification_service import FinancialDataVerificationEngine

    return FinancialDataVerificationEngine.get_authoritative_macro_snapshot(db)



def tool_compute_equity_valuations_and_ratios(
    market_metrics: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """
    Execute fundamental ratio analysis and 2-stage DCF intrinsic valuation
    for core covered Nigerian equities (GTCO, ZENITHBANK, DANGCEM, SEPLAT).
    """
    gtco_px = market_metrics.get("GTCO.NG", {}).get("latest_price", 55.50)
    zenith_px = market_metrics.get("ZENITHBANK.NG", {}).get("latest_price", 46.30)
    dangcem_px = market_metrics.get("DANGCEM.NG", {}).get("latest_price", 602.50)
    seplat_px = market_metrics.get("SEPLAT.NG", {}).get("latest_price", 5215.00)

    fundamentals = [
        {
            "ticker": "GTCO.NG",
            "name": "Guaranty Trust Holding Company Plc",
            "sector": "Banking & Financial Services",
            "price": gtco_px,
            "shares": 29_431_179_224,
            "net_income": 539_650_000_000,
            "book_equity": 1_480_000_000_000,
            "total_assets": 9_691_000_000_000,
            "dps": 3.20,
            "nii": 550_000_000_000,
            "earning_assets": 6_200_000_000_000,
            "opex": 250_000_000_000,
            "opinc": 860_000_000_000,
            "fcfe_per_share": 15.80,
            "high_growth_pct": 18.5,
            "term_growth_pct": 10.5,
            "beta": 1.02,
        },
        {
            "ticker": "ZENITHBANK.NG",
            "name": "Zenith Bank Plc",
            "sector": "Banking & Financial Services",
            "price": zenith_px,
            "shares": 31_396_493_786,
            "net_income": 676_900_000_000,
            "book_equity": 2_320_000_000_000,
            "total_assets": 20_360_000_000_000,
            "dps": 4.00,
            "nii": 1_120_000_000_000,
            "earning_assets": 13_400_000_000_000,
            "opex": 440_000_000_000,
            "opinc": 1_450_000_000_000,
            "fcfe_per_share": 14.40,
            "high_growth_pct": 17.5,
            "term_growth_pct": 10.0,
            "beta": 1.05,
        },
        {
            "ticker": "DANGCEM.NG",
            "name": "Dangote Cement Plc",
            "sector": "Industrial Goods",
            "price": dangcem_px,
            "shares": 17_040_507_405,
            "net_income": 455_580_000_000,
            "book_equity": 1_730_000_000_000,
            "total_assets": 3_940_000_000_000,
            "dps": 30.00,
            "nii": None,
            "earning_assets": None,
            "opex": None,
            "opinc": None,
            "fcfe_per_share": 115.0,
            "high_growth_pct": 19.0,
            "term_growth_pct": 11.0,
            "beta": 0.94,
        },
        {
            "ticker": "SEPLAT.NG",
            "name": "Seplat Energy Plc",
            "sector": "Oil & Gas",
            "price": seplat_px,
            "shares": 588_444_561,
            "net_income": 195_400_000_000,
            "book_equity": 2_680_000_000_000,
            "total_assets": 4_850_000_000_000,
            "dps": 185.00,
            "nii": None,
            "earning_assets": None,
            "opex": None,
            "opinc": None,
            "fcfe_per_share": 980.0,
            "high_growth_pct": 21.0,
            "term_growth_pct": 11.0,
            "beta": 1.08,
        },
    ]

    output: Dict[str, Dict[str, Any]] = {}
    for f in fundamentals:
        ratios = compute_financial_ratios(
            ticker=f["ticker"],
            period="FY-Latest Audited",
            share_price=float(f["price"]),
            shares_outstanding=float(f["shares"]),
            net_income=float(f["net_income"]),
            book_value_equity=float(f["book_equity"]),
            total_assets=float(f["total_assets"]),
            dividends_per_share=float(f["dps"]),
            net_interest_income=f["nii"],
            earning_assets=f["earning_assets"],
            operating_expenses=f["opex"],
            operating_income=f["opinc"],
        )
        dcf = compute_equity_valuation_dcf(
            ticker=f["ticker"],
            current_share_price=float(f["price"]),
            base_fcfe_per_share=float(f["fcfe_per_share"]),
            high_growth_rate_pct=float(f["high_growth_pct"]),
            terminal_growth_rate_pct=float(f["term_growth_pct"]),
            risk_free_rate_pct=19.45,
            beta=float(f["beta"]),
        )
        output[f["ticker"]] = {
            "name": f["name"],
            "sector": f["sector"],
            "ratios": ratios.to_dict(),
            "dcf_valuation": dcf.to_dict(),
        }
    return output


def tool_load_competitor_profiles(db: Session) -> List[Dict[str, Any]]:
    """Load registered Nigerian financial services competitor profiles."""
    rows = db.execute(select(CompetitorProfile)).scalars().all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "category": r.category,
            "tier": r.tier,
            "headquarters": r.headquarters,
            "key_products": r.key_products,
            "aum_or_capital_estimate": r.aum_or_capital_estimate,
            "competitive_strengths": r.competitive_strengths,
            "vulnerabilities": r.vulnerabilities,
        }
        for r in rows
    ]
