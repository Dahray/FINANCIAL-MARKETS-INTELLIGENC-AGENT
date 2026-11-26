"""
Global Financial Market & Macroeconomic Data Providers:
- Financial Modeling Prep (FMP) API
- Alpha Vantage API
- St. Louis Fed FRED API (JSON API + public FRED CSV series fallback)
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import io
from typing import Dict, List, Optional, Tuple

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.core.ssl_helper import create_http_client
from app.providers.base import (
    BaseMacroDataProvider,
    BaseMarketDataProvider,
    IngestedMacroPoint,
    IngestedMarketPoint,
    IngestedYieldPoint,
)

logger = get_logger("fmip.providers.global")


class FMPDataProvider(BaseMarketDataProvider):
    """
    Financial Modeling Prep (FMP) API adapter for global equities, indices,
    commodities, FX pairs, and company fundamentals.
    """

    provider_code = "FMP_API"
    provider_name = "Financial Modeling Prep (FMP)"
    reliability_tier = "TIER_2_INSTITUTIONAL"
    BASE_URL = "https://financialmodelingprep.com/api/v3"

    DEFAULT_SYMBOLS: List[Tuple[str, str, str, str, str]] = [
        ("^GSPC", "S&P 500 Index", "INDEX", "GLOBAL", "INDEX_POINTS"),
        ("^IXIC", "NASDAQ Composite Index", "INDEX", "GLOBAL", "INDEX_POINTS"),
        ("^FTSE", "FTSE 100 Index", "INDEX", "GLOBAL", "INDEX_POINTS"),
        ("BZUSD", "Brent Crude Oil Futures", "COMMODITY", "GLOBAL", "USD_PER_BBL"),
        ("GCUSD", "Gold Spot USD/oz", "COMMODITY", "GLOBAL", "USD_PER_OZ"),
        ("USDNGN", "USD/NGN Exchange Rate", "FX", "NIGERIA", "NGN_PER_USD"),
    ]

    def fetch_market_timeseries(
        self, symbols: Optional[List[str]] = None
    ) -> List[IngestedMarketPoint]:
        if not settings.FMP_API_KEY:
            logger.info("FMP_API_KEY not configured in .env; skipping live FMP REST call.")
            return []

        points: List[IngestedMarketPoint] = []
        now_utc = datetime.now(timezone.utc)
        target_tuples = self.DEFAULT_SYMBOLS
        if symbols:
            target_tuples = [t for t in self.DEFAULT_SYMBOLS if t[0] in symbols] or [
                (s, s, "EQUITY", "GLOBAL", "USD") for s in symbols
            ]

        symbol_csv = ",".join(t[0] for t in target_tuples)
        meta_map = {t[0]: t for t in target_tuples}
        url = f"{self.BASE_URL}/quote/{symbol_csv}"

        try:
            with create_http_client(timeout=settings.DATA_PROVIDER_TIMEOUT_SECONDS) as client:
                resp = client.get(url, params={"apikey": settings.FMP_API_KEY})
                if resp.status_code == 200 and isinstance(resp.json(), list):
                    for item in resp.json():
                        sym = str(item.get("symbol", ""))
                        price = item.get("price")
                        if not sym or price is None:
                            continue
                        _, name, asset_cls, region, unit = meta_map.get(
                            sym, (sym, item.get("name", sym), "EQUITY", "GLOBAL", "USD")
                        )
                        ts = item.get("timestamp")
                        pub_dt = (
                            datetime.fromtimestamp(int(ts), tz=timezone.utc)
                            if ts
                            else now_utc
                        )
                        points.append(
                            IngestedMarketPoint(
                                symbol=sym,
                                indicator_name=name,
                                asset_class=asset_cls,
                                market_region=region,
                                value=float(price),
                                open_value=float(item["open"]) if item.get("open") is not None else None,
                                high_value=float(item["dayHigh"]) if item.get("dayHigh") is not None else None,
                                low_value=float(item["dayLow"]) if item.get("dayLow") is not None else None,
                                close_value=float(price),
                                volume=float(item["volume"]) if item.get("volume") is not None else None,
                                market_cap=float(item["marketCap"]) if item.get("marketCap") is not None else None,
                                currency_or_unit=unit,
                                reporting_period=pub_dt.strftime("%Y-%m-%d"),
                                publication_date=pub_dt,
                                source_code=self.provider_code,
                                source_url=f"{self.BASE_URL}/quote/{sym}",
                                data_frequency="DAILY",
                                verification_status="VERIFIED",
                            )
                        )
        except Exception as exc:
            logger.warning("FMPDataProvider error: %s", exc)
        return points


class AlphaVantageDataProvider(BaseMarketDataProvider):
    """
    Alpha Vantage API adapter for FX exchange rates and global commodities.
    """

    provider_code = "ALPHA_VANTAGE"
    provider_name = "Alpha Vantage Financial API"
    reliability_tier = "TIER_2_INSTITUTIONAL"
    BASE_URL = "https://www.alphavantage.co/query"

    def fetch_market_timeseries(
        self, symbols: Optional[List[str]] = None
    ) -> List[IngestedMarketPoint]:
        if not settings.ALPHA_VANTAGE_API_KEY:
            logger.info("ALPHA_VANTAGE_API_KEY not configured in .env; skipping Alpha Vantage call.")
            return []

        points: List[IngestedMarketPoint] = []
        now_utc = datetime.now(timezone.utc)
        try:
            with create_http_client(timeout=settings.DATA_PROVIDER_TIMEOUT_SECONDS) as client:
                resp = client.get(
                    self.BASE_URL,
                    params={
                        "function": "CURRENCY_EXCHANGE_RATE",
                        "from_currency": "USD",
                        "to_currency": "NGN",
                        "apikey": settings.ALPHA_VANTAGE_API_KEY,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json().get("Realtime Currency Exchange Rate", {})
                    rate_str = data.get("5. Exchange Rate")
                    if rate_str:
                        rate_val = float(rate_str)
                        points.append(
                            IngestedMarketPoint(
                                symbol="USDNGN.AV",
                                indicator_name="USD/NGN Exchange Rate (Alpha Vantage)",
                                asset_class="FX",
                                market_region="NIGERIA",
                                value=rate_val,
                                close_value=rate_val,
                                currency_or_unit="NGN_PER_USD",
                                reporting_period=now_utc.strftime("%Y-%m-%d"),
                                publication_date=now_utc,
                                source_code=self.provider_code,
                                source_url=self.BASE_URL,
                                data_frequency="DAILY",
                                verification_status="VERIFIED",
                            )
                        )
        except Exception as exc:
            logger.warning("AlphaVantageDataProvider error: %s", exc)
        return points


class FREDDataProvider(BaseMacroDataProvider, BaseMarketDataProvider):
    """
    Federal Reserve Economic Data (FRED - St. Louis Fed) provider.
    Supports both the authenticated FRED JSON API (when FRED_API_KEY is configured)
    and FRED's official public CSV endpoint (`https://fred.stlouisfed.org/graph/fredgraph.csv?id=...`)
    for zero-key live ingestion of global macro, US Treasury yields, Brent crude, and World Bank Nigerian series.
    """

    provider_code = "FRED_API"
    provider_name = "Federal Reserve Economic Data (FRED - St. Louis Fed)"
    reliability_tier = "TIER_1_OFFICIAL"
    JSON_API_URL = "https://api.stlouisfed.org/fred/series/observations"
    PUBLIC_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"

    MACRO_SERIES: List[Dict[str, str]] = [
        {
            "fred_id": "FEDFUNDS",
            "code": "US_FED_FUNDS",
            "name": "US Federal Funds Effective Rate",
            "country": "USA",
            "category": "MONETARY_POLICY",
            "unit": "PERCENT",
            "freq": "MONTHLY",
        },
        {
            "fred_id": "FPCPITOTLZGNGA",
            "code": "NG_WB_CPI_INFLATION_ANNUAL",
            "name": "Nigeria Consumer Price Inflation (World Bank / FRED)",
            "country": "NIGERIA",
            "category": "INFLATION",
            "unit": "PERCENT",
            "freq": "ANNUAL",
        },
    ]

    MARKET_SERIES: List[Dict[str, str]] = [
        {
            "fred_id": "DCOILBRENTEU",
            "symbol": "BRENT",
            "name": "Crude Oil Prices: Brent - Europe",
            "asset_class": "COMMODITY",
            "region": "GLOBAL",
            "unit": "USD_PER_BBL",
        },
    ]

    UST_YIELD_SERIES: List[Tuple[str, str, int, float]] = [
        ("DGS2", "2Y", 730, 2.0),
        ("DGS5", "5Y", 1825, 5.0),
        ("DGS10", "10Y", 3650, 10.0),
        ("DGS30", "30Y", 10950, 30.0),
    ]

    def _fetch_series_tail(
        self, fred_id: str, limit: int = 15
    ) -> List[Tuple[datetime, float]]:
        """Fetch latest `limit` observations for a FRED series via JSON API or official CSV."""
        observations: List[Tuple[datetime, float]] = []
        try:
            with create_http_client(
                timeout=settings.DATA_PROVIDER_TIMEOUT_SECONDS,
                follow_redirects=True,
            ) as client:
                if settings.FRED_API_KEY:
                    resp = client.get(
                        self.JSON_API_URL,
                        params={
                            "series_id": fred_id,
                            "api_key": settings.FRED_API_KEY,
                            "file_type": "json",
                            "sort_order": "desc",
                            "limit": limit,
                        },
                    )
                    if resp.status_code == 200:
                        for row in reversed(resp.json().get("observations", [])):
                            val_str = row.get("value", ".")
                            if val_str and val_str != ".":
                                dt = datetime.strptime(row["date"], "%Y-%m-%d").replace(
                                    tzinfo=timezone.utc
                                )
                                observations.append((dt, float(val_str)))
                        return observations

                # Official public FRED CSV fallback
                resp = client.get(self.PUBLIC_CSV_URL, params={"id": fred_id})
                if resp.status_code == 200 and resp.text:
                    reader = csv.reader(io.StringIO(resp.text))
                    rows = list(reader)[1:]  # skip header
                    valid_rows = [r for r in rows if len(r) >= 2 and r[1] not in ("", ".")]
                    for dt_str, val_str in valid_rows[-limit:]:
                        dt = datetime.strptime(dt_str.strip(), "%Y-%m-%d").replace(
                            tzinfo=timezone.utc
                        )
                        observations.append((dt, float(val_str.strip())))
        except Exception as exc:
            logger.info("FRED series fetch note for %s: %s", fred_id, exc)
        return observations

    def fetch_macro_indicators(self) -> List[IngestedMacroPoint]:
        points: List[IngestedMacroPoint] = []
        for meta in self.MACRO_SERIES:
            obs = self._fetch_series_tail(meta["fred_id"], limit=6)
            for idx, (dt, val) in enumerate(obs):
                prev_val = obs[idx - 1][1] if idx > 0 else None
                points.append(
                    IngestedMacroPoint(
                        indicator_code=meta["code"],
                        indicator_name=meta["name"],
                        country=meta["country"],
                        category=meta["category"],
                        value=val,
                        previous_value=prev_val,
                        currency_or_unit=meta["unit"],
                        reporting_period=dt.strftime("%Y-%m"),
                        publication_date=dt,
                        source_code=self.provider_code,
                        source_url=f"https://fred.stlouisfed.org/series/{meta['fred_id']}",
                        data_frequency=meta["freq"],
                        verification_status="VERIFIED",
                    )
                )
        return points

    def fetch_market_timeseries(
        self, symbols: Optional[List[str]] = None
    ) -> List[IngestedMarketPoint]:
        points: List[IngestedMarketPoint] = []
        for meta in self.MARKET_SERIES:
            obs = self._fetch_series_tail(meta["fred_id"], limit=15)
            for dt, val in obs:
                points.append(
                    IngestedMarketPoint(
                        symbol=meta["symbol"],
                        indicator_name=meta["name"],
                        asset_class=meta["asset_class"],
                        market_region=meta["region"],
                        value=val,
                        close_value=val,
                        currency_or_unit=meta["unit"],
                        reporting_period=dt.strftime("%Y-%m-%d"),
                        publication_date=dt,
                        source_code=self.provider_code,
                        source_url=f"https://fred.stlouisfed.org/series/{meta['fred_id']}",
                        data_frequency="DAILY",
                        verification_status="VERIFIED",
                    )
                )
        return points

    def fetch_yield_curves(self) -> List[IngestedYieldPoint]:
        points: List[IngestedYieldPoint] = []
        for fred_id, tenor_lbl, t_days, t_years in self.UST_YIELD_SERIES:
            obs = self._fetch_series_tail(fred_id, limit=3)
            for dt, val in obs:
                points.append(
                    IngestedYieldPoint(
                        curve_name="USD_UST_BENCHMARK",
                        instrument_type="US_TREASURY",
                        tenor_label=tenor_lbl,
                        tenor_days=t_days,
                        tenor_years=t_years,
                        indicator_name=f"US Treasury {tenor_lbl} Constant Maturity Yield",
                        value=val,
                        currency_or_unit="PERCENT",
                        reporting_period=dt.strftime("%Y-%m-%d"),
                        publication_date=dt,
                        source_code=self.provider_code,
                        source_url=f"https://fred.stlouisfed.org/series/{fred_id}",
                        data_frequency="DAILY",
                        verification_status="VERIFIED",
                    )
                )
        return points
