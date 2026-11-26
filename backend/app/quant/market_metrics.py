"""
Deterministic Market Performance, Technical Moving Averages, Volatility,
and Risk-Adjusted Return Calculations (Agent 6: Quantitative Analysis Agent).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd
try:
    from scipy import stats as _scipy_stats
except ImportError:
    _scipy_stats = None


@dataclass
class MarketPerformanceReport:
    """Verified deterministic historical market performance & risk metrics."""

    symbol: str
    as_of_date: str
    latest_price: float
    period_returns_pct: Dict[str, Optional[float]]
    moving_averages: Dict[str, Optional[float]]
    momentum_indicators: Dict[str, Optional[float]]
    annualized_volatility_pct: float
    rolling_30d_volatility_pct: Optional[float]
    downside_deviation_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: Optional[float]
    parametric_var_95_pct: float
    parametric_var_99_pct: float
    historical_var_95_pct: float
    historical_var_99_pct: float
    observations_count: int
    independent_check_passed: bool
    is_forecast: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _compute_rsi(series: pd.Series, window: int = 14) -> Optional[float]:
    """Compute Relative Strength Index (Wilder / rolling average formulation)."""
    if len(series) < window + 1:
        return None
    delta = series.diff().dropna()
    gains = delta.clip(lower=0.0)
    losses = -delta.clip(upper=0.0)
    avg_gain = gains.rolling(window=window, min_periods=window).mean().iloc[-1]
    avg_loss = losses.rolling(window=window, min_periods=window).mean().iloc[-1]
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(round(100.0 - (100.0 / (1.0 + rs)), 4))


def compute_market_performance(
    dates: Sequence[datetime | str],
    prices: Sequence[float],
    symbol: str,
    risk_free_rate_annual: float = 0.18,
    trading_days_per_year: int = 252,
) -> MarketPerformanceReport:
    """
    Compute comprehensive historical returns, moving averages, volatility, drawdown,
    VaR, Sharpe/Sortino ratios, and perform an independent mathematical identity check.
    """
    if len(prices) < 5 or len(dates) != len(prices):
        raise ValueError(
            f"compute_market_performance requires matching dates/prices with >= 5 observations (got {len(prices)})."
        )

    df = pd.DataFrame({"date": pd.to_datetime(dates, utc=True), "price": pd.to_numeric(prices, errors="coerce")})
    df = df.dropna(subset=["price"]).sort_values("date").reset_index(drop=True)
    if (df["price"] <= 0).any():
        raise ValueError(f"All price observations for {symbol} must be strictly positive.")

    s = df["price"]
    latest_price = float(s.iloc[-1])
    latest_dt = df["date"].iloc[-1]

    # Period returns (%)
    horizon_map = {
        "1D": 1,
        "1W": 5,
        "1M": 21,
        "3M": 63,
        "6M": 126,
        "1Y": 252,
    }
    period_returns: Dict[str, Optional[float]] = {}
    for label, lag in horizon_map.items():
        if len(s) > lag:
            prev_val = float(s.iloc[-(lag + 1)])
            period_returns[label] = round(((latest_price / prev_val) - 1.0) * 100.0, 4)
        else:
            period_returns[label] = None

    # YTD return
    current_year_df = df[df["date"].dt.year == latest_dt.year]
    if len(current_year_df) >= 2:
        ytd_start = float(current_year_df["price"].iloc[0])
        period_returns["YTD"] = round(((latest_price / ytd_start) - 1.0) * 100.0, 4)
    else:
        period_returns["YTD"] = None

    # Moving averages
    ma_dict: Dict[str, Optional[float]] = {
        "SMA_20": round(float(s.rolling(20).mean().iloc[-1]), 4) if len(s) >= 20 else None,
        "SMA_50": round(float(s.rolling(50).mean().iloc[-1]), 4) if len(s) >= 50 else None,
        "SMA_200": round(float(s.rolling(200).mean().iloc[-1]), 4) if len(s) >= 200 else None,
        "EMA_12": round(float(s.ewm(span=12, adjust=False).mean().iloc[-1]), 4) if len(s) >= 12 else None,
        "EMA_26": round(float(s.ewm(span=26, adjust=False).mean().iloc[-1]), 4) if len(s) >= 26 else None,
    }

    # Momentum (RSI-14 & MACD)
    ema12 = s.ewm(span=12, adjust=False).mean()
    ema26 = s.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    momentum: Dict[str, Optional[float]] = {
        "RSI_14": _compute_rsi(s, 14),
        "MACD": round(float(macd_line.iloc[-1]), 4) if len(s) >= 26 else None,
        "MACD_SIGNAL": round(float(signal_line.iloc[-1]), 4) if len(s) >= 35 else None,
        "MACD_HISTOGRAM": round(float((macd_line - signal_line).iloc[-1]), 4) if len(s) >= 35 else None,
    }

    # Daily simple & log returns
    daily_returns = s.pct_change().dropna()
    log_returns = np.log(s / s.shift(1)).dropna()

    daily_std = float(daily_returns.std(ddof=1))
    ann_vol_pct = round(daily_std * np.sqrt(trading_days_per_year) * 100.0, 4)

    rolling_30_vol: Optional[float] = None
    if len(daily_returns) >= 30:
        rolling_30_vol = round(
            float(daily_returns.rolling(30).std(ddof=1).iloc[-1] * np.sqrt(trading_days_per_year) * 100.0),
            4,
        )

    # Downside deviation & Sortino/Sharpe
    daily_rf = (1.0 + risk_free_rate_annual) ** (1.0 / trading_days_per_year) - 1.0
    excess_returns = daily_returns - daily_rf
    downside_returns = excess_returns[excess_returns < 0]
    downside_std_daily = (
        float(np.sqrt(np.mean(np.square(downside_returns))))
        if len(downside_returns) > 0
        else 1e-9
    )
    downside_dev_pct = round(downside_std_daily * np.sqrt(trading_days_per_year) * 100.0, 4)

    mean_excess_ann = float(excess_returns.mean()) * trading_days_per_year
    ann_vol_decimal = daily_std * np.sqrt(trading_days_per_year)
    sharpe = round(mean_excess_ann / ann_vol_decimal, 4) if ann_vol_decimal > 1e-9 else 0.0
    downside_ann_decimal = downside_std_daily * np.sqrt(trading_days_per_year)
    sortino = round(mean_excess_ann / downside_ann_decimal, 4) if downside_ann_decimal > 1e-9 else 0.0

    # Maximum Drawdown (%)
    cumulative_wealth = (1.0 + daily_returns).cumprod()
    running_peak = cumulative_wealth.cummax()
    drawdowns = (cumulative_wealth / running_peak) - 1.0
    max_drawdown_pct = round(float(drawdowns.min()) * 100.0, 4)

    ann_total_return = float((latest_price / float(s.iloc[0])) ** (trading_days_per_year / max(1, len(daily_returns))) - 1.0)
    calmar = (
        round((ann_total_return * 100.0) / abs(max_drawdown_pct), 4)
        if abs(max_drawdown_pct) > 1e-6
        else None
    )

    # Value-at-Risk (1-day VaR expressed as positive loss percentage)
    mu_daily = float(daily_returns.mean())
    z95 = float(_scipy_stats.norm.ppf(0.05)) if _scipy_stats is not None else -1.6448536269514729
    z99 = float(_scipy_stats.norm.ppf(0.01)) if _scipy_stats is not None else -2.3263478740408408
    param_var_95 = round(max(0.0, -(mu_daily + z95 * daily_std) * 100.0), 4)
    param_var_99 = round(max(0.0, -(mu_daily + z99 * daily_std) * 100.0), 4)
    hist_var_95 = round(max(0.0, -float(np.percentile(daily_returns, 5)) * 100.0), 4)
    hist_var_99 = round(max(0.0, -float(np.percentile(daily_returns, 1)) * 100.0), 4)

    # Independent verification check: sum of log returns == log(P_T / P_0) AND compound simple return == P_T / P_0
    sum_log_ret = float(log_returns.sum())
    endpoint_log_ret = float(np.log(latest_price / float(s.iloc[0])))
    compound_simple = float(np.prod(1.0 + daily_returns.to_numpy()))
    endpoint_ratio = latest_price / float(s.iloc[0])
    independent_check_passed = bool(
        abs(sum_log_ret - endpoint_log_ret) < 1e-7
        and abs(compound_simple - endpoint_ratio) < 1e-6
    )
    if not independent_check_passed:
        raise RuntimeError(f"Independent mathematical check failed for {symbol}.")

    return MarketPerformanceReport(
        symbol=symbol,
        as_of_date=latest_dt.strftime("%Y-%m-%d"),
        latest_price=round(latest_price, 4),
        period_returns_pct=period_returns,
        moving_averages=ma_dict,
        momentum_indicators=momentum,
        annualized_volatility_pct=ann_vol_pct,
        rolling_30d_volatility_pct=rolling_30_vol,
        downside_deviation_pct=downside_dev_pct,
        max_drawdown_pct=max_drawdown_pct,
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        calmar_ratio=calmar,
        parametric_var_95_pct=param_var_95,
        parametric_var_99_pct=param_var_99,
        historical_var_95_pct=hist_var_95,
        historical_var_99_pct=hist_var_99,
        observations_count=len(s),
        independent_check_passed=independent_check_passed,
        is_forecast=False,
    )
