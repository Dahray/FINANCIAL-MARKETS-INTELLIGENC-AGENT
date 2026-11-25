"""
Deterministic Fixed-Income & Sovereign Yield Curve Analytics:
Nelson-Siegel Curve Fitting, Term Spreads, Real Yields (Fisher Equation),
Macaulay/Modified Duration, Convexity, and DV01 (Agent 6: Quantitative Analysis Agent).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Sequence

import numpy as np
from scipy.optimize import least_squares


@dataclass
class YieldCurveAnalyticsReport:
    """Deterministic yield curve analysis including Nelson-Siegel parameters and real yields."""

    curve_name: str
    observed_points: List[Dict[str, float]]
    nelson_siegel_params: Dict[str, float]
    fitted_standard_tenors: Dict[str, float]
    real_yields_fisher_pct: Dict[str, float]
    simple_real_spreads_pct: Dict[str, float]
    term_spreads_bps: Dict[str, float]
    curve_shape: str
    average_nominal_yield_pct: float
    average_real_yield_pct: float
    inflation_benchmark_pct: float
    fit_rmse_bps: float
    independent_check_passed: bool
    is_forecast: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BondRiskMetrics:
    """Deterministic bond pricing, duration, convexity, and DV01 report."""

    clean_price: float
    macaulay_duration_years: float
    modified_duration_years: float
    effective_convexity: float
    dv01_per_100_par: float
    price_change_plus_100bps_pct: float
    price_change_minus_100bps_pct: float
    independent_check_passed: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _nelson_siegel_yield(
    tau: np.ndarray,
    beta0: float,
    beta1: float,
    beta2: float,
    lam: float,
) -> np.ndarray:
    """Evaluate Nelson-Siegel parametric yield curve at maturities `tau` (in years)."""
    tau_safe = np.maximum(np.asarray(tau, dtype=float), 1e-4)
    lam_safe = max(float(lam), 1e-3)
    x = tau_safe / lam_safe
    factor1 = (1.0 - np.exp(-x)) / x
    factor2 = factor1 - np.exp(-x)
    return beta0 + beta1 * factor1 + beta2 * factor2


def analyze_yield_curve(
    tenor_years: Sequence[float],
    yields_pct: Sequence[float],
    inflation_rate_pct: float,
    curve_name: str = "NGN_SOVEREIGN_FMDQ",
) -> YieldCurveAnalyticsReport:
    """
    Fit a Nelson-Siegel yield curve to sovereign NTB/Bond observations, compute term spreads,
    classify curve morphology, and calculate Fisher exact real yields against inflation.
    """
    if len(tenor_years) < 3 or len(tenor_years) != len(yields_pct):
        raise ValueError("analyze_yield_curve requires at least 3 matching (tenor, yield) observations.")

    order = np.argsort(tenor_years)
    taus = np.asarray(tenor_years, dtype=float)[order]
    y_obs = np.asarray(yields_pct, dtype=float)[order]

    # Fit Nelson-Siegel parameters [beta0, beta1, beta2, lambda]
    init_guess = np.array([float(y_obs[-1]), float(y_obs[0] - y_obs[-1]), 0.0, 1.5])
    bounds = ([-5.0, -30.0, -30.0, 0.1], [60.0, 30.0, 30.0, 15.0])

    def residuals(params: np.ndarray) -> np.ndarray:
        return _nelson_siegel_yield(taus, params[0], params[1], params[2], params[3]) - y_obs

    res = least_squares(residuals, init_guess, bounds=bounds)
    b0, b1, b2, lam = [float(v) for v in res.x]

    fitted_obs = _nelson_siegel_yield(taus, b0, b1, b2, lam)
    fit_rmse_bps = round(float(np.sqrt(np.mean(np.square(fitted_obs - y_obs))) * 100.0), 2)

    standard_tenors = {
        "91D": 91.0 / 365.0,
        "182D": 182.0 / 365.0,
        "364D": 1.0,
        "2Y": 2.0,
        "3Y": 3.0,
        "5Y": 5.0,
        "7Y": 7.0,
        "10Y": 10.0,
        "15Y": 15.0,
        "20Y": 20.0,
        "30Y": 30.0,
    }

    fitted_map: Dict[str, float] = {}
    fisher_real_map: Dict[str, float] = {}
    simple_real_map: Dict[str, float] = {}
    pi_dec = inflation_rate_pct / 100.0

    for label, t_yr in standard_tenors.items():
        y_hat = float(_nelson_siegel_yield(np.array([t_yr]), b0, b1, b2, lam)[0])
        fitted_map[label] = round(y_hat, 4)
        y_dec = y_hat / 100.0
        fisher_real = (((1.0 + y_dec) / (1.0 + pi_dec)) - 1.0) * 100.0
        fisher_real_map[label] = round(fisher_real, 4)
        simple_real_map[label] = round(y_hat - inflation_rate_pct, 4)

    spread_10y_1y_bps = round((fitted_map["10Y"] - fitted_map["364D"]) * 100.0, 2)
    spread_10y_2y_bps = round((fitted_map["10Y"] - fitted_map["2Y"]) * 100.0, 2)
    spread_30y_10y_bps = round((fitted_map["30Y"] - fitted_map["10Y"]) * 100.0, 2)
    spread_1y_91d_bps = round((fitted_map["364D"] - fitted_map["91D"]) * 100.0, 2)

    term_spreads = {
        "10Y_minus_1Y_bps": spread_10y_1y_bps,
        "10Y_minus_2Y_bps": spread_10y_2y_bps,
        "30Y_minus_10Y_bps": spread_30y_10y_bps,
        "364D_minus_91D_bps": spread_1y_91d_bps,
    }

    # Classify curve shape
    if fitted_map["364D"] > fitted_map["10Y"] and fitted_map["364D"] > fitted_map["91D"]:
        curve_shape = "HUMPED_FRONT_END_ELEVATED"
    elif spread_10y_2y_bps < -25.0:
        curve_shape = "INVERTED"
    elif abs(spread_10y_2y_bps) <= 25.0:
        curve_shape = "FLAT"
    elif spread_10y_2y_bps > 150.0:
        curve_shape = "NORMAL_STEEP"
    else:
        curve_shape = "NORMAL_UPWARD_SLOPING"

    observed_points = [
        {"tenor_years": round(float(t), 4), "yield_pct": round(float(y), 4)}
        for t, y in zip(taus, y_obs)
    ]

    # Independent verification check on Fisher identity: (1 + r_real)(1 + pi) == (1 + y_nominal)
    y10_dec = fitted_map["10Y"] / 100.0
    r10_dec = fisher_real_map["10Y"] / 100.0
    independent_check = abs((1.0 + r10_dec) * (1.0 + pi_dec) - (1.0 + y10_dec)) < 1e-4
    if not independent_check:
        raise RuntimeError("Fisher real yield mathematical cross-check failed.")

    return YieldCurveAnalyticsReport(
        curve_name=curve_name,
        observed_points=observed_points,
        nelson_siegel_params={
            "beta0_long_term_level": round(b0, 4),
            "beta1_short_term_slope": round(b1, 4),
            "beta2_medium_term_curvature": round(b2, 4),
            "lambda_decay_factor": round(lam, 4),
        },
        fitted_standard_tenors=fitted_map,
        real_yields_fisher_pct=fisher_real_map,
        simple_real_spreads_pct=simple_real_map,
        term_spreads_bps=term_spreads,
        curve_shape=curve_shape,
        average_nominal_yield_pct=round(float(np.mean(y_obs)), 4),
        average_real_yield_pct=round(float(np.mean(list(fisher_real_map.values()))), 4),
        inflation_benchmark_pct=round(inflation_rate_pct, 4),
        fit_rmse_bps=fit_rmse_bps,
        independent_check_passed=independent_check,
        is_forecast=False,
    )


def compute_bond_risk_metrics(
    face_value: float = 100.0,
    coupon_rate_pct: float = 18.50,
    ytm_pct: float = 19.25,
    years_to_maturity: float = 10.0,
    frequency: int = 2,
) -> BondRiskMetrics:
    """
    Compute exact fixed-coupon bond price, Macaulay Duration, Modified Duration,
    Effective Convexity, and DV01, with independent numerical shock cross-checking.
    """
    if years_to_maturity <= 0 or frequency <= 0:
        raise ValueError("years_to_maturity and frequency must be positive.")

    n_periods = max(1, int(round(years_to_maturity * frequency)))
    c_period = (coupon_rate_pct / 100.0) * face_value / frequency

    def price_at_ytm(y_annual_pct: float) -> float:
        r = (y_annual_pct / 100.0) / frequency
        periods = np.arange(1, n_periods + 1, dtype=float)
        cashflows = np.full(n_periods, c_period, dtype=float)
        cashflows[-1] += face_value
        discounts = (1.0 + r) ** periods
        return float(np.sum(cashflows / discounts))

    p0 = price_at_ytm(ytm_pct)
    r0 = (ytm_pct / 100.0) / frequency
    periods = np.arange(1, n_periods + 1, dtype=float)
    cashflows = np.full(n_periods, c_period, dtype=float)
    cashflows[-1] += face_value
    pv_cf = cashflows / ((1.0 + r0) ** periods)

    macaulay_periods = float(np.sum(periods * pv_cf) / p0)
    macaulay_years = macaulay_periods / frequency
    modified_years = macaulay_years / (1.0 + r0)

    # Effective duration & convexity via 1bp and 100bp finite differences
    dy_1bp = 0.01  # 0.01% = 1 bp
    p_up_1bp = price_at_ytm(ytm_pct + dy_1bp)
    p_dn_1bp = price_at_ytm(ytm_pct - dy_1bp)
    dv01 = (p_dn_1bp - p_up_1bp) / 2.0

    dy_100bp = 1.0  # 1.00% = 100 bps
    dy_dec = 0.01
    p_up_100 = price_at_ytm(ytm_pct + dy_100bp)
    p_dn_100 = price_at_ytm(ytm_pct - dy_100bp)
    eff_convexity = (p_dn_100 + p_up_100 - 2.0 * p0) / (p0 * (dy_dec ** 2))

    # Independent check: finite-difference modified duration matches analytical modified duration within 0.02 yrs
    fd_mod_dur = (p_dn_1bp - p_up_1bp) / (2.0 * p0 * 0.0001)
    independent_check = abs(fd_mod_dur - modified_years) < 0.02
    if not independent_check:
        raise RuntimeError("Bond duration independent mathematical check failed.")

    return BondRiskMetrics(
        clean_price=round(p0, 4),
        macaulay_duration_years=round(macaulay_years, 4),
        modified_duration_years=round(modified_years, 4),
        effective_convexity=round(eff_convexity, 4),
        dv01_per_100_par=round(dv01 * (100.0 / face_value), 4),
        price_change_plus_100bps_pct=round(((p_up_100 / p0) - 1.0) * 100.0, 4),
        price_change_minus_100bps_pct=round(((p_dn_100 / p0) - 1.0) * 100.0, 4),
        independent_check_passed=independent_check,
    )
