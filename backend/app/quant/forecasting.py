"""
Deterministic Time-Series Forecasting & Walk-Forward Backtesting Engine
(Section 6 & Section 11: Nigerian Inflation, Exchange Rate Trends, Interest Rates,
Treasury Bill Yields, Bond Yields, Equity Market & Sector Performance).
Supports statsmodels/scikit-learn when installed and exact closed-form NumPy ARIMA/ETS/Ridge solvers.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

try:
    from statsmodels.tsa.arima.model import ARIMA as _SM_ARIMA
    from statsmodels.tsa.holtwinters import ExponentialSmoothing as _SM_ETS
except ImportError:
    _SM_ARIMA = None
    _SM_ETS = None

try:
    from sklearn.linear_model import Ridge as _SK_Ridge
except ImportError:
    _SK_Ridge = None


@dataclass
class BacktestEvaluationResult:
    """Out-of-sample walk-forward backtesting metrics comparing predictions with actual outcomes."""

    target_code: str
    model_family: str
    backtest_window_start: str
    backtest_window_end: str
    n_splits: int
    rmse: float
    mae: float
    mape_pct: float
    directional_accuracy_pct: float
    predicted_vs_actual: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VerifiedForecastResult:
    """
    Complete Section 11 Forecast Artifact.
    Strictly distinguishes historical observations from forward predictions (`is_forecast = True`),
    and provides Base Case, Bull Case, Bear Case, Key Assumptions, Confidence Level,
    Historical Model Backtest Performance, and Invalidation Factors.
    """

    target_code: str
    target_name: str
    model_family: str
    forecast_horizon_label: str
    forecast_target_date: str
    last_historical_value: float
    last_historical_date: str
    base_case: float
    bull_case: float
    bear_case: float
    confidence_level_pct: float
    key_assumptions: List[str]
    invalidation_factors: List[str]
    forecast_trajectory: List[Dict[str, Any]]
    historical_backtest: BacktestEvaluationResult
    currency_or_unit: str
    is_forecast: bool = True

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["historical_backtest"] = self.historical_backtest.to_dict()
        return d


def _fit_and_predict_step(
    train_vals: np.ndarray,
    steps: int,
    model_family: str,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Fit statistical/ML model on `train_vals` and return `(point_forecasts, std_errors)`.
    Supports `ARIMA`, `HOLT_WINTERS_ETS`, and `RIDGE_AUTOREGRESSIVE`.
    """
    y = np.asarray(train_vals, dtype=float)
    n = len(y)

    if model_family == "ARIMA":
        if _SM_ARIMA is not None:
            try:
                order = (1, 1, 1) if n >= 18 else (1, 1, 0)
                model = _SM_ARIMA(y, order=order, enforce_stationarity=False, enforce_invertibility=False)
                fitted = model.fit()
                fc_res = fitted.get_forecast(steps=steps)
                mean_fc = np.asarray(fc_res.predicted_mean, dtype=float)
                se_fc = np.asarray(fc_res.se_mean, dtype=float)
                se_fc = np.where(
                    np.isnan(se_fc) | (se_fc <= 0),
                    max(1e-6, float(np.std(np.diff(y)))) * np.sqrt(np.arange(1, steps + 1)),
                    se_fc,
                )
                return mean_fc, se_fc
            except Exception:
                pass

        # Exact ARIMA(1,1,0) on first differences via OLS: dy_t = c + phi * dy_{t-1}
        dy = np.diff(y)
        if len(dy) >= 4:
            X_ar = np.column_stack([np.ones(len(dy) - 1), dy[:-1]])
            betas, _, _, _ = np.linalg.lstsq(X_ar, dy[1:], rcond=None)
            c_ar, phi_ar = float(betas[0]), float(np.clip(betas[1], -0.95, 0.95))
            resid = dy[1:] - (X_ar @ betas)
            resid_std = max(1e-6, float(np.std(resid, ddof=1)))
        else:
            c_ar, phi_ar = float(np.mean(dy)), 0.0
            resid_std = max(1e-6, float(np.std(dy)))

        last_level = float(y[-1])
        last_diff = float(dy[-1])
        preds_ar: List[float] = []
        for _ in range(steps):
            nxt_diff = c_ar + phi_ar * last_diff
            last_level = last_level + nxt_diff
            last_diff = nxt_diff
            preds_ar.append(last_level)
        se_fc = resid_std * np.sqrt(np.arange(1, steps + 1, dtype=float))
        return np.asarray(preds_ar, dtype=float), se_fc

    if model_family == "HOLT_WINTERS_ETS":
        if _SM_ETS is not None:
            try:
                model = _SM_ETS(
                    y,
                    trend="add",
                    damped_trend=(n >= 15),
                    seasonal=None,
                    initialization_method="estimated",
                )
                fitted = model.fit(optimized=True)
                mean_fc = np.asarray(fitted.forecast(steps), dtype=float)
                resid_std = (
                    float(np.std(y - fitted.fittedvalues, ddof=1))
                    if n > 3
                    else float(np.std(np.diff(y)))
                )
                se_fc = max(1e-6, resid_std) * np.sqrt(np.arange(1, steps + 1, dtype=float))
                return mean_fc, se_fc
            except Exception:
                pass

        # Exact Holt Damped-Trend Double Exponential Smoothing
        alpha, beta, phi = 0.65, 0.25, 0.92
        level = float(y[0])
        trend = float(y[1] - y[0])
        fitted_vals = [level]
        for val in y[1:]:
            prev_level = level
            level = alpha * float(val) + (1.0 - alpha) * (prev_level + phi * trend)
            trend = beta * (level - prev_level) + (1.0 - beta) * phi * trend
            fitted_vals.append(level)
        resid_std = max(1e-6, float(np.std(y - np.asarray(fitted_vals), ddof=1)))
        preds_ets = []
        phi_sum = 0.0
        for h in range(1, steps + 1):
            phi_sum += phi ** h
            preds_ets.append(level + phi_sum * trend)
        se_fc = resid_std * np.sqrt(np.arange(1, steps + 1, dtype=float))
        return np.asarray(preds_ets, dtype=float), se_fc

    # RIDGE_AUTOREGRESSIVE (Closed-form Tikhonov L2 regularized autoregression with intercept)
    lags = min(3, max(1, n // 4))
    X_rows = []
    y_targets = []
    for idx in range(lags, n):
        X_rows.append([1.0] + list(y[idx - lags : idx][::-1]))
        y_targets.append(y[idx])
    X_mat = np.asarray(X_rows, dtype=float)
    y_vec = np.asarray(y_targets, dtype=float)

    reg_alpha = 1.0
    reg_eye = np.eye(X_mat.shape[1], dtype=float) * reg_alpha
    reg_eye[0, 0] = 0.0  # Do not penalize intercept
    weights = np.linalg.pinv(X_mat.T @ X_mat + reg_eye) @ (X_mat.T @ y_vec)
    in_sample_pred = X_mat @ weights
    resid_std = max(1e-6, float(np.std(y_vec - in_sample_pred, ddof=1)))

    history = list(y)
    preds = []
    for _ in range(steps):
        feat = np.asarray([1.0] + history[-lags:][::-1], dtype=float)
        nxt = float(feat @ weights)
        preds.append(nxt)
        history.append(nxt)
    se_fc = resid_std * np.sqrt(np.arange(1, steps + 1, dtype=float))
    return np.asarray(preds, dtype=float), se_fc


def run_walk_forward_backtest(
    dates: Sequence[datetime | str],
    values: Sequence[float],
    target_code: str,
    model_family: str = "ARIMA",
    n_test_splits: int = 8,
) -> BacktestEvaluationResult:
    """
    Perform expanding-window walk-forward historical backtesting comparing
    1-step-ahead out-of-sample model predictions against actual outcomes.
    """
    df = pd.DataFrame(
        {"date": pd.to_datetime(dates, utc=True), "val": pd.to_numeric(values, errors="coerce")}
    ).dropna().sort_values("date").reset_index(drop=True)

    y = df["val"].to_numpy(dtype=float)
    n = len(y)
    if n < 10:
        raise ValueError(f"Walk-forward backtesting for {target_code} requires >= 10 observations (got {n}).")

    actual_splits = min(n_test_splits, max(3, n // 3))
    start_idx = n - actual_splits

    preds: List[float] = []
    actuals: List[float] = []
    dir_hits: List[bool] = []
    pairs: List[Dict[str, Any]] = []

    for split_i in range(start_idx, n):
        train_slice = y[:split_i]
        prev_val = float(train_slice[-1])
        true_val = float(y[split_i])
        pred_arr, _ = _fit_and_predict_step(train_slice, steps=1, model_family=model_family)
        pred_val = float(pred_arr[0])

        preds.append(pred_val)
        actuals.append(true_val)

        actual_delta = true_val - prev_val
        pred_delta = pred_val - prev_val
        hit = (actual_delta * pred_delta >= 0) or (abs(actual_delta) < 1e-6 and abs(pred_delta) < 1e-6)
        dir_hits.append(bool(hit))

        dt_str = df["date"].iloc[split_i].strftime("%Y-%m-%d")
        err = pred_val - true_val
        ape = (abs(err) / abs(true_val) * 100.0) if abs(true_val) > 1e-9 else 0.0
        pairs.append(
            {
                "date": dt_str,
                "actual": round(true_val, 4),
                "predicted": round(pred_val, 4),
                "error": round(err, 4),
                "abs_pct_error": round(ape, 4),
            }
        )

    errors = np.asarray(preds) - np.asarray(actuals)
    rmse = float(np.sqrt(np.mean(np.square(errors))))
    mae = float(np.mean(np.abs(errors)))
    denom = np.where(np.abs(actuals) < 1e-9, 1.0, np.abs(actuals))
    mape_pct = float(np.mean(np.abs(errors) / denom) * 100.0)
    dir_acc = float(np.mean(dir_hits) * 100.0)

    return BacktestEvaluationResult(
        target_code=target_code,
        model_family=model_family,
        backtest_window_start=df["date"].iloc[start_idx].strftime("%Y-%m-%d"),
        backtest_window_end=df["date"].iloc[-1].strftime("%Y-%m-%d"),
        n_splits=actual_splits,
        rmse=round(rmse, 4),
        mae=round(mae, 4),
        mape_pct=round(mape_pct, 4),
        directional_accuracy_pct=round(dir_acc, 2),
        predicted_vs_actual=pairs,
    )


def generate_verified_forecast(
    dates: Sequence[datetime | str],
    values: Sequence[float],
    target_code: str,
    target_name: str,
    currency_or_unit: str,
    horizon_steps: int = 4,
    step_days: int = 7,
    forecast_horizon_label: str = "4_WEEKS",
    confidence_level_pct: float = 80.0,
    higher_is_bull: bool = True,
    key_assumptions: Optional[List[str]] = None,
    invalidation_factors: Optional[List[str]] = None,
    preferred_model_family: Optional[str] = None,
) -> VerifiedForecastResult:
    """
    Train & walk-forward backtest candidate forecasting models (ARIMA, Holt-Winters ETS,
    Ridge Autoregressive), select the highest-accuracy model (or `preferred_model_family`),
    and generate Base, Bull, and Bear scenario forecasts with confidence intervals.
    """
    df = pd.DataFrame(
        {"date": pd.to_datetime(dates, utc=True), "val": pd.to_numeric(values, errors="coerce")}
    ).dropna().sort_values("date").reset_index(drop=True)

    if len(df) < 10:
        raise ValueError(f"generate_verified_forecast for {target_code} requires >= 10 historical observations.")

    candidate_families = (
        [preferred_model_family]
        if preferred_model_family
        else ["ARIMA", "HOLT_WINTERS_ETS", "RIDGE_AUTOREGRESSIVE"]
    )

    best_bt: Optional[BacktestEvaluationResult] = None
    best_family = candidate_families[0]

    for fam in candidate_families:
        bt = run_walk_forward_backtest(
            dates=df["date"].tolist(),
            values=df["val"].tolist(),
            target_code=target_code,
            model_family=fam,
        )
        if best_bt is None or bt.rmse < best_bt.rmse:
            best_bt = bt
            best_family = fam

    assert best_bt is not None

    y_all = df["val"].to_numpy(dtype=float)
    last_dt = df["date"].iloc[-1]
    last_val = float(y_all[-1])

    mean_fc, se_fc = _fit_and_predict_step(y_all, steps=horizon_steps, model_family=best_family)

    z_mult = 1.2816 if confidence_level_pct <= 80.0 else (1.6449 if confidence_level_pct <= 90.0 else 1.9600)

    trajectory: List[Dict[str, Any]] = []
    for step_idx in range(horizon_steps):
        target_dt = last_dt + timedelta(days=step_days * (step_idx + 1))
        pt = float(mean_fc[step_idx])
        band = float(se_fc[step_idx]) * z_mult
        upper = pt + band
        lower = pt - band
        bull_val = upper if higher_is_bull else lower
        bear_val = lower if higher_is_bull else upper
        trajectory.append(
            {
                "step": step_idx + 1,
                "forecast_date": target_dt.strftime("%Y-%m-%d"),
                "base_case": round(pt, 4),
                "bull_case": round(bull_val, 4),
                "bear_case": round(bear_val, 4),
                "upper_bound": round(upper, 4),
                "lower_bound": round(lower, 4),
                "is_forecast": True,
            }
        )

    final_step = trajectory[-1]
    default_assumptions = key_assumptions or [
        "Continuation of current CBN monetary policy transmission and liquidity management regime.",
        "No unscheduled sovereign debt restructuring or external commodity price regime shock (>25% move in Brent crude).",
        f"Historical error structure remains consistent with out-of-sample backtest MAPE of {best_bt.mape_pct:.2f}%.",
    ]
    default_invalidations = invalidation_factors or [
        "Emergency CBN MPC rate adjustment exceeding +/- 200 bps outside scheduled calendar.",
        "Structural shift in NAFEM foreign exchange market liquidity rules or crude oil production disruption > 300k bpd.",
        "Fiscal supplementary budget expansion significantly altering domestic NTB/FGN Bond issuance supply.",
    ]

    return VerifiedForecastResult(
        target_code=target_code,
        target_name=target_name,
        model_family=best_family,
        forecast_horizon_label=forecast_horizon_label,
        forecast_target_date=final_step["forecast_date"],
        last_historical_value=round(last_val, 4),
        last_historical_date=last_dt.strftime("%Y-%m-%d"),
        base_case=final_step["base_case"],
        bull_case=final_step["bull_case"],
        bear_case=final_step["bear_case"],
        confidence_level_pct=confidence_level_pct,
        key_assumptions=default_assumptions,
        invalidation_factors=default_invalidations,
        forecast_trajectory=trajectory,
        historical_backtest=best_bt,
        currency_or_unit=currency_or_unit,
        is_forecast=True,
    )
