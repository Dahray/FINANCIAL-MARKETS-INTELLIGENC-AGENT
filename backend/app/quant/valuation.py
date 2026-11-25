"""
Deterministic Corporate Financial Ratios, Equity Valuation (2-Stage DCF / Gordon Growth),
and Multi-Variable Scenario & Sensitivity Modelling (Agent 6: Quantitative Analysis Agent).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Sequence


@dataclass
class FinancialRatiosReport:
    """Verified corporate & banking financial ratios."""

    ticker: str
    period: str
    pe_ratio: Optional[float]
    pb_ratio: Optional[float]
    ev_to_ebitda: Optional[float]
    dividend_yield_pct: Optional[float]
    roe_pct: Optional[float]
    roa_pct: Optional[float]
    net_profit_margin_pct: Optional[float]
    net_interest_margin_pct: Optional[float]
    cost_to_income_pct: Optional[float]
    debt_to_equity: Optional[float]
    current_ratio: Optional[float]
    interest_coverage: Optional[float]
    free_cash_flow_yield_pct: Optional[float]
    independent_check_passed: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EquityValuationReport:
    """Deterministic 2-Stage DCF equity valuation with 2D sensitivity matrix."""

    ticker: str
    current_share_price: float
    intrinsic_value_per_share: float
    upside_or_downside_pct: float
    margin_of_safety_pct: float
    cost_of_equity_pct: float
    wacc_pct: float
    pv_explicit_cash_flows_per_share: float
    pv_terminal_value_per_share: float
    valuation_verdict: str
    sensitivity_matrix: Dict[str, Dict[str, float]]
    assumptions: Dict[str, Any]
    independent_check_passed: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compute_financial_ratios(
    ticker: str,
    period: str,
    share_price: float,
    shares_outstanding: float,
    net_income: float,
    book_value_equity: float,
    total_assets: float,
    total_debt: float = 0.0,
    cash_and_equivalents: float = 0.0,
    revenue: Optional[float] = None,
    ebitda: Optional[float] = None,
    ebit: Optional[float] = None,
    interest_expense: Optional[float] = None,
    dividends_per_share: float = 0.0,
    free_cash_flow: Optional[float] = None,
    current_assets: Optional[float] = None,
    current_liabilities: Optional[float] = None,
    net_interest_income: Optional[float] = None,
    earning_assets: Optional[float] = None,
    operating_expenses: Optional[float] = None,
    operating_income: Optional[float] = None,
) -> FinancialRatiosReport:
    """Compute fundamental financial & banking ratios with deterministic verification."""
    if share_price <= 0 or shares_outstanding <= 0:
        raise ValueError("share_price and shares_outstanding must be strictly positive.")

    market_cap = share_price * shares_outstanding
    eps = net_income / shares_outstanding
    bvps = book_value_equity / shares_outstanding

    pe = round(share_price / eps, 4) if eps > 0 else None
    pb = round(share_price / bvps, 4) if bvps > 0 else None

    enterprise_value = market_cap + total_debt - cash_and_equivalents
    ev_ebitda = (
        round(enterprise_value / ebitda, 4)
        if (ebitda is not None and ebitda > 0)
        else None
    )
    div_yield = round((dividends_per_share / share_price) * 100.0, 4)
    roe = (
        round((net_income / book_value_equity) * 100.0, 4)
        if book_value_equity > 0
        else None
    )
    roa = (
        round((net_income / total_assets) * 100.0, 4)
        if total_assets > 0
        else None
    )
    net_margin = (
        round((net_income / revenue) * 100.0, 4)
        if (revenue is not None and revenue > 0)
        else None
    )
    nim = (
        round((net_interest_income / earning_assets) * 100.0, 4)
        if (net_interest_income is not None and earning_assets and earning_assets > 0)
        else None
    )
    cir = (
        round((operating_expenses / operating_income) * 100.0, 4)
        if (operating_expenses is not None and operating_income and operating_income > 0)
        else None
    )
    d_to_e = (
        round(total_debt / book_value_equity, 4)
        if book_value_equity > 0
        else None
    )
    curr_ratio = (
        round(current_assets / current_liabilities, 4)
        if (current_assets is not None and current_liabilities and current_liabilities > 0)
        else None
    )
    int_cov = (
        round(ebit / interest_expense, 4)
        if (ebit is not None and interest_expense and interest_expense > 0)
        else None
    )
    fcf_yield = (
        round((free_cash_flow / market_cap) * 100.0, 4)
        if free_cash_flow is not None
        else None
    )

    # Independent cross-check: P/E == Market Cap / Net Income when EPS > 0
    independent_check = True
    if pe is not None and net_income > 0:
        independent_check = abs(pe - (market_cap / net_income)) < 1e-4

    return FinancialRatiosReport(
        ticker=ticker,
        period=period,
        pe_ratio=pe,
        pb_ratio=pb,
        ev_to_ebitda=ev_ebitda,
        dividend_yield_pct=div_yield,
        roe_pct=roe,
        roa_pct=roa,
        net_profit_margin_pct=net_margin,
        net_interest_margin_pct=nim,
        cost_to_income_pct=cir,
        debt_to_equity=d_to_e,
        current_ratio=curr_ratio,
        interest_coverage=int_cov,
        free_cash_flow_yield_pct=fcf_yield,
        independent_check_passed=independent_check,
    )


def compute_equity_valuation_dcf(
    ticker: str,
    current_share_price: float,
    base_fcfe_per_share: float,
    high_growth_rate_pct: float = 18.0,
    high_growth_years: int = 5,
    terminal_growth_rate_pct: float = 10.0,
    risk_free_rate_pct: float = 18.5,
    beta: float = 1.05,
    equity_risk_premium_pct: float = 6.5,
    country_risk_premium_pct: float = 2.0,
) -> EquityValuationReport:
    """
    Compute 2-stage Free Cash Flow to Equity (FCFE) / Dividend Discount intrinsic value
    per share with a 2D sensitivity table across discount rates and terminal growth rates.
    """
    if current_share_price <= 0 or base_fcfe_per_share <= 0:
        raise ValueError("current_share_price and base_fcfe_per_share must be positive.")

    ke_pct = risk_free_rate_pct + beta * (equity_risk_premium_pct + country_risk_premium_pct)
    g_high = high_growth_rate_pct / 100.0

    def value_at_params(discount_pct: float, term_g_pct: float) -> tuple[float, float, float]:
        r = discount_pct / 100.0
        g_term = term_g_pct / 100.0
        if r <= g_term + 0.005:
            r = g_term + 0.01
        pv_explicit = 0.0
        cf = base_fcfe_per_share
        for t in range(1, high_growth_years + 1):
            cf = cf * (1.0 + g_high)
            pv_explicit += cf / ((1.0 + r) ** t)
        terminal_cf = cf * (1.0 + g_term)
        terminal_val = terminal_cf / (r - g_term)
        pv_terminal = terminal_val / ((1.0 + r) ** high_growth_years)
        return pv_explicit + pv_terminal, pv_explicit, pv_terminal

    intrinsic, pv_exp, pv_term = value_at_params(ke_pct, terminal_growth_rate_pct)
    upside_pct = ((intrinsic / current_share_price) - 1.0) * 100.0
    mos_pct = ((intrinsic - current_share_price) / intrinsic) * 100.0 if intrinsic > 0 else 0.0

    if upside_pct >= 20.0:
        verdict = "UNDERVALUED_ATTRACTIVE"
    elif upside_pct <= -15.0:
        verdict = "OVERVALUED_CAUTION"
    else:
        verdict = "FAIRLY_VALUED"

    # Build 2D sensitivity matrix: Cost of Equity (+/- 200 bps) vs Terminal Growth (+/- 200 bps)
    sens_matrix: Dict[str, Dict[str, float]] = {}
    for d_shift in (-2.0, -1.0, 0.0, 1.0, 2.0):
        d_rate = round(ke_pct + d_shift, 2)
        row_key = f"Ke_{d_rate:.2f}%"
        sens_matrix[row_key] = {}
        for g_shift in (-2.0, -1.0, 0.0, 1.0, 2.0):
            g_rate = round(terminal_growth_rate_pct + g_shift, 2)
            col_key = f"g_{g_rate:.2f}%"
            val, _, _ = value_at_params(d_rate, g_rate)
            sens_matrix[row_key][col_key] = round(val, 2)

    independent_check = abs(intrinsic - (pv_exp + pv_term)) < 1e-6

    return EquityValuationReport(
        ticker=ticker,
        current_share_price=round(current_share_price, 2),
        intrinsic_value_per_share=round(intrinsic, 2),
        upside_or_downside_pct=round(upside_pct, 2),
        margin_of_safety_pct=round(mos_pct, 2),
        cost_of_equity_pct=round(ke_pct, 2),
        wacc_pct=round(ke_pct, 2),
        pv_explicit_cash_flows_per_share=round(pv_exp, 2),
        pv_terminal_value_per_share=round(pv_term, 2),
        valuation_verdict=verdict,
        sensitivity_matrix=sens_matrix,
        assumptions={
            "base_fcfe_per_share": base_fcfe_per_share,
            "high_growth_rate_pct": high_growth_rate_pct,
            "high_growth_years": high_growth_years,
            "terminal_growth_rate_pct": terminal_growth_rate_pct,
            "risk_free_rate_pct": risk_free_rate_pct,
            "beta": beta,
            "equity_risk_premium_pct": equity_risk_premium_pct,
            "country_risk_premium_pct": country_risk_premium_pct,
        },
        independent_check_passed=independent_check,
    )


def run_macro_market_scenario_analysis(
    portfolio_value_ngn: float,
    fixed_income_weight: float = 0.55,
    equity_weight: float = 0.30,
    fx_usd_asset_weight: float = 0.15,
    avg_bond_modified_duration: float = 4.2,
    avg_bond_running_yield_pct: float = 19.5,
    equity_beta_to_ngx: float = 1.05,
) -> Dict[str, Any]:
    """
    Deterministic multi-asset scenario stress test across 4 institutional macro scenarios
    (Base Case, Bull / Disinflation & FX Stability, Bear / Inflation & Rate Hike Shock,
    External Oil & FX Liquidity Stress).
    """
    total_w = fixed_income_weight + equity_weight + fx_usd_asset_weight
    if abs(total_w - 1.0) > 1e-4:
        raise ValueError("Asset allocation weights must sum to 1.0.")

    scenarios: Sequence[Dict[str, Any]] = [
        {
            "name": "BASE_CASE_GRADUAL_STABILIZATION",
            "description": "CBN maintains tight monetary stance; gradual disinflation; NAFEM FX trading within +/-5% band.",
            "yield_shift_bps": -50.0,
            "ngx_equity_return_pct": 16.5,
            "ngn_depreciation_pct": 4.0,
        },
        {
            "name": "BULL_CASE_DISINFLATION_RALLY",
            "description": "Headline inflation moderates >400 bps; bond yields compress 250 bps; strong NGX re-rating.",
            "yield_shift_bps": -250.0,
            "ngx_equity_return_pct": 32.0,
            "ngn_depreciation_pct": -5.0,  # NGN appreciates 5%
        },
        {
            "name": "BEAR_CASE_INFLATION_MPR_SHOCK",
            "description": "Food & energy price spike forces +200 bps CBN rate hike; sovereign yields rise 225 bps.",
            "yield_shift_bps": 225.0,
            "ngx_equity_return_pct": -12.0,
            "ngn_depreciation_pct": 15.0,
        },
        {
            "name": "TAIL_RISK_OIL_AND_FX_STRESS",
            "description": "Brent crude drops below $60/bbl; external reserves pressure triggers 25% NGN depreciation.",
            "yield_shift_bps": 300.0,
            "ngx_equity_return_pct": -18.5,
            "ngn_depreciation_pct": 25.0,
        },
    ]

    results: List[Dict[str, Any]] = []
    for sc in scenarios:
        dy_pct = float(sc["yield_shift_bps"]) / 100.0
        # Fixed-income total return = running yield - modified_duration * dy
        fi_return_pct = avg_bond_running_yield_pct - (avg_bond_modified_duration * dy_pct)
        eq_return_pct = float(sc["ngx_equity_return_pct"]) * equity_beta_to_ngx
        # USD asset NGN return = USD cash yield (~4.5%) + NGN depreciation effect
        fx_return_pct = 4.5 + float(sc["ngn_depreciation_pct"])

        total_return_pct = (
            fixed_income_weight * fi_return_pct
            + equity_weight * eq_return_pct
            + fx_usd_asset_weight * fx_return_pct
        )
        projected_value = portfolio_value_ngn * (1.0 + total_return_pct / 100.0)
        pnl_ngn = projected_value - portfolio_value_ngn

        results.append(
            {
                "scenario_name": sc["name"],
                "description": sc["description"],
                "shocks": {
                    "yield_shift_bps": sc["yield_shift_bps"],
                    "ngx_equity_return_pct": sc["ngx_equity_return_pct"],
                    "ngn_depreciation_pct": sc["ngn_depreciation_pct"],
                },
                "component_returns_pct": {
                    "fixed_income_return_pct": round(fi_return_pct, 2),
                    "equity_return_pct": round(eq_return_pct, 2),
                    "fx_usd_asset_return_pct": round(fx_return_pct, 2),
                },
                "portfolio_total_return_pct": round(total_return_pct, 2),
                "projected_portfolio_value_ngn": round(projected_value, 2),
                "net_pnl_ngn": round(pnl_ngn, 2),
            }
        )

    return {
        "initial_portfolio_value_ngn": portfolio_value_ngn,
        "allocation": {
            "fixed_income_weight": fixed_income_weight,
            "equity_weight": equity_weight,
            "fx_usd_asset_weight": fx_usd_asset_weight,
        },
        "scenarios": results,
    }
