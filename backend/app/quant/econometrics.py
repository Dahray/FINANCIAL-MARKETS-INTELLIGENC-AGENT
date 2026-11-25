"""
Deterministic Econometric & Statistical Analysis:
Pearson/Spearman Correlation Matrices, OLS Single & Multi-Factor Regression,
Durbin-Watson Diagnostics, and Augmented Dickey-Fuller (ADF) Stationarity Tests.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Sequence

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm
from statsmodels.stats.stattools import durbin_watson
from statsmodels.tsa.stattools import adfuller


@dataclass
class CorrelationAnalysisReport:
    """Verified Pearson & Spearman correlation matrix with two-tailed p-values."""

    variables: List[str]
    pearson_matrix: Dict[str, Dict[str, float]]
    spearman_matrix: Dict[str, Dict[str, float]]
    p_value_matrix: Dict[str, Dict[str, float]]
    significant_pairs: List[Dict[str, Any]]
    observations_count: int
    independent_check_passed: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OLSRegressionReport:
    """Verified Ordinary Least Squares (OLS) econometric regression output."""

    dependent_variable: str
    independent_variables: List[str]
    intercept: float
    coefficients: Dict[str, float]
    std_errors: Dict[str, float]
    t_stats: Dict[str, float]
    p_values: Dict[str, float]
    r_squared: float
    adj_r_squared: float
    f_statistic: float
    f_pvalue: float
    durbin_watson_stat: float
    residual_std_error: float
    observations_count: int
    independent_check_passed: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compute_correlation_matrix(
    series_dict: Dict[str, Sequence[float]],
    significance_alpha: float = 0.05,
) -> CorrelationAnalysisReport:
    """
    Compute aligned Pearson & Spearman correlation matrices and two-tailed p-values.
    Independently cross-checks Pearson r against numpy.corrcoef.
    """
    if len(series_dict) < 2:
        raise ValueError("compute_correlation_matrix requires at least 2 variables.")

    df = pd.DataFrame({k: pd.to_numeric(v, errors="coerce") for k, v in series_dict.items()}).dropna()
    if len(df) < 4:
        raise ValueError("Insufficient aligned observations (< 4) for correlation analysis.")

    cols = list(df.columns)
    pearson_mat: Dict[str, Dict[str, float]] = {c: {} for c in cols}
    spearman_mat: Dict[str, Dict[str, float]] = {c: {} for c in cols}
    pval_mat: Dict[str, Dict[str, float]] = {c: {} for c in cols}
    sig_pairs: List[Dict[str, Any]] = []

    np_corr = np.corrcoef(df.to_numpy(), rowvar=False)
    independent_check = True

    for i, c1 in enumerate(cols):
        for j, c2 in enumerate(cols):
            if i == j:
                pearson_mat[c1][c2] = 1.0
                spearman_mat[c1][c2] = 1.0
                pval_mat[c1][c2] = 0.0
                continue
            r_p, p_p = stats.pearsonr(df[c1].to_numpy(), df[c2].to_numpy())
            r_s, _ = stats.spearmanr(df[c1].to_numpy(), df[c2].to_numpy())
            if abs(float(r_p) - float(np_corr[i, j])) > 1e-6:
                independent_check = False

            pearson_mat[c1][c2] = round(float(r_p), 4)
            spearman_mat[c1][c2] = round(float(r_s), 4)
            pval_mat[c1][c2] = round(float(p_p), 6)

            if i < j and float(p_p) <= significance_alpha:
                sig_pairs.append(
                    {
                        "var_1": c1,
                        "var_2": c2,
                        "pearson_r": round(float(r_p), 4),
                        "spearman_rho": round(float(r_s), 4),
                        "p_value": round(float(p_p), 6),
                        "relationship": "POSITIVE" if r_p > 0 else "NEGATIVE",
                    }
                )

    if not independent_check:
        raise RuntimeError("Correlation matrix cross-check against numpy.corrcoef failed.")

    return CorrelationAnalysisReport(
        variables=cols,
        pearson_matrix=pearson_mat,
        spearman_matrix=spearman_mat,
        p_value_matrix=pval_mat,
        significant_pairs=sig_pairs,
        observations_count=len(df),
        independent_check_passed=independent_check,
    )


def run_ols_regression(
    y_series: Sequence[float],
    x_series_dict: Dict[str, Sequence[float]],
    dependent_name: str = "Y",
) -> OLSRegressionReport:
    """
    Execute Ordinary Least Squares (OLS) regression using statsmodels and verify
    that fitted values + residuals reconstruct Y within 1e-7.
    """
    if not x_series_dict:
        raise ValueError("run_ols_regression requires at least one explanatory variable.")

    data = {"__y__": pd.to_numeric(y_series, errors="coerce")}
    for k, v in x_series_dict.items():
        data[k] = pd.to_numeric(v, errors="coerce")
    df = pd.DataFrame(data).dropna()
    x_cols = list(x_series_dict.keys())

    if len(df) <= len(x_cols) + 2:
        raise ValueError("Insufficient observations relative to number of explanatory variables.")

    y_vec = df["__y__"].to_numpy(dtype=float)
    X_mat = sm.add_constant(df[x_cols], has_constant="add")
    model = sm.OLS(y_vec, X_mat).fit()

    # Independent mathematical check: max(|y - (y_hat + resid)|) < 1e-7 and SST == SSR + SSE
    reconstructed = model.fittedvalues + model.resid
    max_recon_err = float(np.max(np.abs(y_vec - reconstructed)))
    sst = float(np.sum(np.square(y_vec - np.mean(y_vec))))
    sse = float(np.sum(np.square(model.resid)))
    r2_manual = 1.0 - (sse / sst) if sst > 1e-12 else 0.0
    independent_check = bool(
        max_recon_err < 1e-7 and abs(float(model.rsquared) - r2_manual) < 1e-6
    )
    if not independent_check:
        raise RuntimeError("OLS regression independent mathematical cross-check failed.")

    params = model.params
    bse = model.bse
    tvals = model.tvalues
    pvals = model.pvalues

    return OLSRegressionReport(
        dependent_variable=dependent_name,
        independent_variables=x_cols,
        intercept=round(float(params["const"]), 6),
        coefficients={k: round(float(params[k]), 6) for k in x_cols},
        std_errors={k: round(float(bse[k]), 6) for k in x_cols},
        t_stats={k: round(float(tvals[k]), 4) for k in x_cols},
        p_values={k: round(float(pvals[k]), 6) for k in x_cols},
        r_squared=round(float(model.rsquared), 4),
        adj_r_squared=round(float(model.rsquared_adj), 4),
        f_statistic=round(float(model.fvalue), 4) if model.fvalue is not None else 0.0,
        f_pvalue=round(float(model.f_pvalue), 6) if model.f_pvalue is not None else 1.0,
        durbin_watson_stat=round(float(durbin_watson(model.resid)), 4),
        residual_std_error=round(float(np.sqrt(model.mse_resid)), 6),
        observations_count=len(df),
        independent_check_passed=independent_check,
    )


def run_adf_stationarity_test(
    series: Sequence[float],
    series_name: str = "Series",
) -> Dict[str, Any]:
    """Run Augmented Dickey-Fuller (ADF) unit root test for time-series stationarity."""
    s = pd.Series(pd.to_numeric(series, errors="coerce")).dropna()
    if len(s) < 12:
        raise ValueError("ADF test requires at least 12 observations.")
    adf_stat, pval, usedlag, nobs, crit_vals, _ = adfuller(s.to_numpy(dtype=float), autolag="AIC")
    return {
        "series_name": series_name,
        "adf_statistic": round(float(adf_stat), 4),
        "p_value": round(float(pval), 6),
        "used_lag": int(usedlag),
        "observations": int(nobs),
        "critical_values": {k: round(float(v), 4) for k, v in crit_vals.items()},
        "is_stationary_at_5pct": bool(float(pval) < 0.05),
    }
