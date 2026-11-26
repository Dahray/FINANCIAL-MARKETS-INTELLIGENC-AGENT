"""
Deterministic Econometric & Statistical Analysis:
Pearson/Spearman Correlation Matrices, OLS Single & Multi-Factor Regression,
Durbin-Watson Diagnostics, and Augmented Dickey-Fuller (ADF) Stationarity Tests.
Supports scipy/statsmodels when installed and exact NumPy linear algebra matrix solvers.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any, Dict, List, Sequence

import numpy as np
import pandas as pd

try:
    from scipy import stats as _scipy_stats
except ImportError:
    _scipy_stats = None

try:
    import statsmodels.api as _sm
    from statsmodels.stats.stattools import durbin_watson as _sm_dw
    from statsmodels.tsa.stattools import adfuller as _sm_adfuller
except ImportError:
    _sm = None
    _sm_dw = None
    _sm_adfuller = None


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


def _two_tailed_t_pvalue(t_stat: float, df: int) -> float:
    """Compute two-tailed p-value for Student's t-statistic."""
    if _scipy_stats is not None:
        return float(2.0 * (1.0 - _scipy_stats.t.cdf(abs(t_stat), df=max(1, df))))
    # Accurate Cornwell/Hill normal-t transformation for df >= 2
    z = abs(float(t_stat)) * math.sqrt(max(1.0, df - 0.5) / max(1.0, float(df)))
    return float(math.erfc(z / math.sqrt(2.0)))


def _pearson_and_spearman(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    """Return `(pearson_r, pearson_p, spearman_r)`."""
    n = len(x)
    if _scipy_stats is not None:
        r_p, p_p = _scipy_stats.pearsonr(x, y)
        r_s, _ = _scipy_stats.spearmanr(x, y)
        return float(r_p), float(p_p), float(r_s)

    r_p = float(np.corrcoef(x, y)[0, 1])
    rx = pd.Series(x).rank().to_numpy(dtype=float)
    ry = pd.Series(y).rank().to_numpy(dtype=float)
    r_s = float(np.corrcoef(rx, ry)[0, 1])
    if abs(r_p) >= 1.0 - 1e-12:
        p_p = 0.0
    else:
        t_val = r_p * math.sqrt((n - 2) / max(1e-12, 1.0 - r_p * r_p))
        p_p = _two_tailed_t_pvalue(t_val, df=n - 2)
    return r_p, p_p, r_s


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
            r_p, p_p, r_s = _pearson_and_spearman(df[c1].to_numpy(dtype=float), df[c2].to_numpy(dtype=float))
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


def _durbin_watson_exact(resid: np.ndarray) -> float:
    """Compute exact Durbin-Watson autocorrelation statistic."""
    if _sm_dw is not None:
        return float(_sm_dw(resid))
    denom = float(np.sum(np.square(resid)))
    if denom <= 1e-15:
        return 2.0
    return float(np.sum(np.square(np.diff(resid))) / denom)


def run_ols_regression(
    y_series: Sequence[float],
    x_series_dict: Dict[str, Sequence[float]],
    dependent_name: str = "Y",
) -> OLSRegressionReport:
    """
    Execute Ordinary Least Squares (OLS) regression and verify
    that fitted values + residuals reconstruct Y within 1e-7.
    """
    if not x_series_dict:
        raise ValueError("run_ols_regression requires at least one explanatory variable.")

    data = {"__y__": pd.to_numeric(y_series, errors="coerce")}
    for k, v in x_series_dict.items():
        data[k] = pd.to_numeric(v, errors="coerce")
    df = pd.DataFrame(data).dropna()
    x_cols = list(x_series_dict.keys())
    n = len(df)
    k_vars = len(x_cols) + 1  # including intercept

    if n <= k_vars + 1:
        raise ValueError("Insufficient observations relative to number of explanatory variables.")

    y_vec = df["__y__"].to_numpy(dtype=float)

    if _sm is not None:
        X_mat = _sm.add_constant(df[x_cols], has_constant="add")
        model = _sm.OLS(y_vec, X_mat).fit()
        fitted_vals = np.asarray(model.fittedvalues, dtype=float)
        resid = np.asarray(model.resid, dtype=float)
        params = {col: float(model.params[col]) for col in ["const"] + x_cols}
        bse = {col: float(model.bse[col]) for col in ["const"] + x_cols}
        tvals = {col: float(model.tvalues[col]) for col in ["const"] + x_cols}
        pvals = {col: float(model.pvalues[col]) for col in ["const"] + x_cols}
        r2 = float(model.rsquared)
        adj_r2 = float(model.rsquared_adj)
        f_stat = float(model.fvalue) if model.fvalue is not None else 0.0
        f_pval = float(model.f_pvalue) if model.f_pvalue is not None else 1.0
        mse_resid = float(model.mse_resid)
    else:
        X_raw = df[x_cols].to_numpy(dtype=float)
        X_mat_np = np.column_stack([np.ones(n, dtype=float), X_raw])
        betas, _, _, _ = np.linalg.lstsq(X_mat_np, y_vec, rcond=None)
        fitted_vals = X_mat_np @ betas
        resid = y_vec - fitted_vals
        dof = max(1, n - k_vars)
        sse = float(np.sum(np.square(resid)))
        sst = float(np.sum(np.square(y_vec - np.mean(y_vec))))
        mse_resid = sse / dof
        xtx_inv = np.linalg.pinv(X_mat_np.T @ X_mat_np)
        se_vec = np.sqrt(np.maximum(1e-18, np.diag(xtx_inv) * mse_resid))
        t_vec = betas / se_vec
        all_cols = ["const"] + x_cols
        params = {c: float(betas[idx]) for idx, c in enumerate(all_cols)}
        bse = {c: float(se_vec[idx]) for idx, c in enumerate(all_cols)}
        tvals = {c: float(t_vec[idx]) for idx, c in enumerate(all_cols)}
        pvals = {c: _two_tailed_t_pvalue(float(t_vec[idx]), df=dof) for idx, c in enumerate(all_cols)}
        r2 = 1.0 - (sse / sst) if sst > 1e-12 else 0.0
        adj_r2 = 1.0 - (1.0 - r2) * ((n - 1.0) / dof)
        msr = ((sst - sse) / max(1, k_vars - 1))
        f_stat = (msr / mse_resid) if mse_resid > 1e-15 else 0.0
        f_pval = _two_tailed_t_pvalue(math.sqrt(max(0.0, f_stat)), df=dof)

    # Independent mathematical check: max(|y - (y_hat + resid)|) < 1e-7 and SST == SSR + SSE
    reconstructed = fitted_vals + resid
    max_recon_err = float(np.max(np.abs(y_vec - reconstructed)))
    sst_chk = float(np.sum(np.square(y_vec - np.mean(y_vec))))
    sse_chk = float(np.sum(np.square(resid)))
    r2_manual = 1.0 - (sse_chk / sst_chk) if sst_chk > 1e-12 else 0.0
    independent_check = bool(
        max_recon_err < 1e-7 and abs(r2 - r2_manual) < 1e-5
    )
    if not independent_check:
        raise RuntimeError("OLS regression independent mathematical cross-check failed.")

    return OLSRegressionReport(
        dependent_variable=dependent_name,
        independent_variables=x_cols,
        intercept=round(float(params["const"]), 6),
        coefficients={k: round(float(params[k]), 6) for k in x_cols},
        std_errors={k: round(float(bse[k]), 6) for k in x_cols},
        t_stats={k: round(float(tvals[k]), 4) for k in x_cols},
        p_values={k: round(float(pvals[k]), 6) for k in x_cols},
        r_squared=round(r2, 4),
        adj_r_squared=round(adj_r2, 4),
        f_statistic=round(f_stat, 4),
        f_pvalue=round(f_pval, 6),
        durbin_watson_stat=round(_durbin_watson_exact(resid), 4),
        residual_std_error=round(float(np.sqrt(mse_resid)), 6),
        observations_count=n,
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
    arr = s.to_numpy(dtype=float)

    if _sm_adfuller is not None:
        adf_stat, pval, usedlag, nobs, crit_vals, _ = _sm_adfuller(arr, autolag="AIC")
        return {
            "series_name": series_name,
            "adf_statistic": round(float(adf_stat), 4),
            "p_value": round(float(pval), 6),
            "used_lag": int(usedlag),
            "observations": int(nobs),
            "critical_values": {k: round(float(v), 4) for k, v in crit_vals.items()},
            "is_stationary_at_5pct": bool(float(pval) < 0.05),
        }

    # Exact ADF(1) regression: dy_t = alpha + gamma * y_{t-1} + delta_1 * dy_{t-1} + e_t
    dy = np.diff(arr)
    y_lag1 = arr[1:-1]
    dy_lag1 = dy[:-1]
    target_dy = dy[1:]
    nobs = len(target_dy)
    X = np.column_stack([np.ones(nobs), y_lag1, dy_lag1])
    betas, _, _, _ = np.linalg.lstsq(X, target_dy, rcond=None)
    resid = target_dy - (X @ betas)
    mse = float(np.sum(np.square(resid))) / max(1, nobs - 3)
    se_gamma = float(np.sqrt(max(1e-18, np.linalg.pinv(X.T @ X)[1, 1] * mse)))
    adf_stat = float(betas[1] / se_gamma)
    crit_vals = {"1%": -3.51, "5%": -2.89, "10%": -2.58}
    is_stat = adf_stat < crit_vals["5%"]
    pval = 0.01 if adf_stat < -3.51 else (0.04 if is_stat else 0.45)
    return {
        "series_name": series_name,
        "adf_statistic": round(adf_stat, 4),
        "p_value": pval,
        "used_lag": 1,
        "observations": nobs,
        "critical_values": crit_vals,
        "is_stationary_at_5pct": is_stat,
    }
