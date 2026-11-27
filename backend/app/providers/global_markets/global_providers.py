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
    BASE_URL = "https://financialmodelingprep.com/stable"

    DEFAULT_SYMBOLS: List[Tuple[str, str, str, str, str, str]] = [
        ("^GSPC", "SPX", "S&P 500 Index", "INDEX", "GLOBAL", "INDEX_POINTS"),
        ("^DJI", "DJI", "Dow Jones Industrial Average", "INDEX", "GLOBAL", "INDEX_POINTS"),
        ("^IXIC", "^IXIC", "NASDAQ Composite Index", "INDEX", "GLOBAL", "INDEX_POINTS"),
        ("^FTSE", "^FTSE", "FTSE 100 Index", "INDEX", "GLOBAL", "INDEX_POINTS"),
        ("^STOXX50E", "STOXX50E", "Euro Stoxx 50 Index", "INDEX", "GLOBAL", "INDEX_POINTS"),
        ("^N225", "NIKKEI225", "Nikkei 225 Index", "INDEX", "GLOBAL", "INDEX_POINTS"),
        ("^HSI", "HSI", "Hang Seng Index", "INDEX", "GLOBAL", "INDEX_POINTS"),
        ("BZUSD", "BRENT", "Brent Crude Oil Futures (FMP)", "COMMODITY", "GLOBAL", "USD_PER_BBL"),
        ("GCUSD", "GOLD", "Gold Futures USD/oz", "COMMODITY", "GLOBAL", "USD_PER_OZ"),
        ("SIUSD", "SILVER", "Silver Futures USD/oz", "COMMODITY", "GLOBAL", "USD_PER_OZ"),
    ]

    EXPANDED_SYMBOLS: List[Tuple[str, str, str, str, str, str]] = DEFAULT_SYMBOLS + [
        ("^GDAXI", "DAX", "Germany DAX Index", "INDEX", "GLOBAL", "INDEX_POINTS"),
        ("^BVSP", "BOVESPA", "Brazil Bovespa Index", "INDEX", "GLOBAL", "INDEX_POINTS"),
        ("^JN0U.JO", "JSE", "Johannesburg Stock Exchange Index", "INDEX", "AFRICA", "INDEX_POINTS"),
        ("CLUSD", "WTI", "WTI Crude Oil Futures", "COMMODITY", "GLOBAL", "USD_PER_BBL"),
        ("NGUSD", "NATGAS", "Natural Gas Futures", "COMMODITY", "GLOBAL", "USD_PER_MMBTU"),
        ("EEM", "EEM", "iShares MSCI Emerging Markets ETF", "INDEX", "GLOBAL", "USD"),
    ]

    ENTERPRISE_SYMBOLS: List[Tuple[str, str, str, str, str, str]] = EXPANDED_SYMBOLS + [
        ("AFK", "AFK", "VanEck Africa Index ETF", "INDEX", "AFRICA", "USD"),
        ("HGUSD", "COPPER", "Copper Futures", "COMMODITY", "GLOBAL", "USD_PER_LB"),
    ]

    def fetch_market_timeseries(
        self,
        symbols: Optional[List[str]] = None,
        symbol_tier: str = "FREE_STARTER",
        include_eod_history_days: int = 260,
    ) -> List[IngestedMarketPoint]:
        if not settings.FMP_API_KEY or "placeholder" in settings.FMP_API_KEY.lower():
            logger.info("FMP_API_KEY not configured in .env; skipping live FMP REST call.")
            return []

        points: List[IngestedMarketPoint] = []
        now_utc = datetime.now(timezone.utc)
        if symbol_tier == "ENTERPRISE_UNLIMITED":
            target_tuples = self.ENTERPRISE_SYMBOLS
        elif symbol_tier == "STANDARD_PAID":
            target_tuples = self.EXPANDED_SYMBOLS
        else:
            target_tuples = self.DEFAULT_SYMBOLS

        if symbols:
            target_tuples = [t for t in self.ENTERPRISE_SYMBOLS if t[0] in symbols or t[1] in symbols] or [
                (s, s, s, "EQUITY", "GLOBAL", "USD") for s in symbols
            ]

        quote_url = f"{self.BASE_URL}/quote"
        hist_url = f"{self.BASE_URL}/historical-price-eod/light"

        try:
            with create_http_client(timeout=settings.DATA_PROVIDER_TIMEOUT_SECONDS) as client:
                for api_sym, db_sym, name, asset_cls, region, unit in target_tuples:
                    try:
                        # 1. Live quote snapshot
                        resp = client.get(
                            quote_url,
                            params={"symbol": api_sym, "apikey": settings.FMP_API_KEY},
                        )
                        if resp.status_code == 200:
                            payload = resp.json()
                            if isinstance(payload, list) and payload:
                                item = payload[0]
                                price = item.get("price")
                                if price is not None:
                                    ts = item.get("timestamp")
                                    pub_dt = (
                                        datetime.fromtimestamp(int(ts), tz=timezone.utc)
                                        if ts
                                        else now_utc
                                    )
                                    points.append(
                                        IngestedMarketPoint(
                                            symbol=db_sym,
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
                                            effective_date=pub_dt,
                                            source_code=self.provider_code,
                                            source_url=f"https://financialmodelingprep.com/stable/quote?symbol={api_sym}",
                                            source_tier="TIER_2_INSTITUTIONAL",
                                            confidence_score=90.0,
                                            is_archival_baseline=False,
                                            data_frequency="DAILY",
                                            verification_status="VERIFIED",
                                        )
                                    )

                        # 2. Trailing daily EOD history for exact WTD/MTD/YTD/YoY & 50D/200D MA
                        if include_eod_history_days > 0:
                            hresp = client.get(
                                hist_url,
                                params={"symbol": api_sym, "apikey": settings.FMP_API_KEY},
                            )
                            if hresp.status_code == 200:
                                hdata = hresp.json()
                                if isinstance(hdata, list):
                                    # FMP returns newest-first; take trailing window
                                    for row in reversed(hdata[:include_eod_history_days]):
                                        dt_s = row.get("date")
                                        px = row.get("price")
                                        if not dt_s or px is None:
                                            continue
                                        h_dt = datetime.strptime(str(dt_s)[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                                        points.append(
                                            IngestedMarketPoint(
                                                symbol=db_sym,
                                                indicator_name=name,
                                                asset_class=asset_cls,
                                                market_region=region,
                                                value=float(px),
                                                close_value=float(px),
                                                volume=float(row["volume"]) if row.get("volume") is not None else None,
                                                currency_or_unit=unit,
                                                reporting_period=h_dt.strftime("%Y-%m-%d"),
                                                publication_date=h_dt,
                                                effective_date=h_dt,
                                                source_code=self.provider_code,
                                                source_url=f"https://financialmodelingprep.com/stable/historical-price-eod/light?symbol={api_sym}",
                                                source_tier="TIER_2_INSTITUTIONAL",
                                                confidence_score=90.0,
                                                is_archival_baseline=False,
                                                data_frequency="DAILY",
                                                verification_status="VERIFIED",
                                            )
                                        )
                    except Exception as sym_exc:
                        logger.info("FMP symbol %s fetch note: %s", api_sym, sym_exc)
        except Exception as exc:
            logger.warning("FMPDataProvider error: %s", exc)
        return points



class AlphaVantageDataProvider(BaseMarketDataProvider):
    """
    Alpha Vantage API adapter for FX exchange rates and global commodities.
    Supports single-pair mode on FREE_STARTER (to protect 25 req/day limit)
    and multi-pair African/Global FX ingestion on STANDARD_PAID / ENTERPRISE_UNLIMITED.
    """

    provider_code = "ALPHA_VANTAGE"
    provider_name = "Alpha Vantage Financial API"
    reliability_tier = "TIER_2_INSTITUTIONAL"
    BASE_URL = "https://www.alphavantage.co/query"

    FX_PAIRS_BY_TIER: Dict[str, List[Tuple[str, str, str, str]]] = {
        "FREE_STARTER": [
            ("USD", "NGN", "NIGERIA", "NGN_PER_USD"),
        ],
        "STANDARD_PAID": [
            ("USD", "NGN", "NIGERIA", "NGN_PER_USD"),
            ("GBP", "NGN", "NIGERIA", "NGN_PER_GBP"),
            ("EUR", "NGN", "NIGERIA", "NGN_PER_EUR"),
        ],
        "ENTERPRISE_UNLIMITED": [
            ("USD", "NGN", "NIGERIA", "NGN_PER_USD"),
            ("GBP", "NGN", "NIGERIA", "NGN_PER_GBP"),
            ("EUR", "NGN", "NIGERIA", "NGN_PER_EUR"),
            ("USD", "ZAR", "AFRICA", "ZAR_PER_USD"),
            ("USD", "GHS", "AFRICA", "GHS_PER_USD"),
        ],
    }

    def fetch_market_timeseries(
        self,
        symbols: Optional[List[str]] = None,
        quota_tier: str = "FREE_STARTER",
    ) -> List[IngestedMarketPoint]:
        if not settings.ALPHA_VANTAGE_API_KEY:
            logger.info("ALPHA_VANTAGE_API_KEY not configured in .env; skipping Alpha Vantage call.")
            return []

        points: List[IngestedMarketPoint] = []
        now_utc = datetime.now(timezone.utc)
        pairs = self.FX_PAIRS_BY_TIER.get(quota_tier, self.FX_PAIRS_BY_TIER["FREE_STARTER"])

        try:
            with create_http_client(timeout=settings.DATA_PROVIDER_TIMEOUT_SECONDS) as client:
                for from_ccy, to_ccy, region, unit in pairs:
                    resp = client.get(
                        self.BASE_URL,
                        params={
                            "function": "CURRENCY_EXCHANGE_RATE",
                            "from_currency": from_ccy,
                            "to_currency": to_ccy,
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
                                    symbol=f"{from_ccy}{to_ccy}.AV",
                                    indicator_name=f"{from_ccy}/{to_ccy} Exchange Rate (Alpha Vantage)",
                                    asset_class="FX",
                                    market_region=region,
                                    value=rate_val,
                                    close_value=rate_val,
                                    currency_or_unit=unit,
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
            "fred_id": "ECBDFR",
            "code": "EU_ECB_POLICY_RATE",
            "name": "European Central Bank (ECB) Deposit Facility Rate",
            "country": "EUROZONE",
            "category": "MONETARY_POLICY",
            "unit": "PERCENT",
            "freq": "DAILY",
        },
        {
            "fred_id": "UNRATE",
            "code": "US_UNEMPLOYMENT_RATE",
            "name": "US Unemployment Rate (BLS)",
            "country": "USA",
            "category": "EMPLOYMENT",
            "unit": "PERCENT",
            "freq": "MONTHLY",
        },
        {
            "fred_id": "PAYEMS",
            "code": "US_NONFARM_PAYROLLS_TOTAL",
            "name": "US Total Non-Farm Payrolls ('000, BLS)",
            "country": "USA",
            "category": "EMPLOYMENT",
            "unit": "THOUSANDS",
            "freq": "MONTHLY",
        },
        {
            "fred_id": "JTSJOL",
            "code": "US_JOLTS_JOB_OPENINGS",
            "name": "US JOLTS Job Openings ('000, BLS)",
            "country": "USA",
            "category": "EMPLOYMENT",
            "unit": "THOUSANDS",
            "freq": "MONTHLY",
        },
        {
            "fred_id": "CCSA",
            "code": "US_CONTINUED_JOBLESS_CLAIMS",
            "name": "US Continued Jobless Claims (Weekly, DOL)",
            "country": "USA",
            "category": "EMPLOYMENT",
            "unit": "PERSONS",
            "freq": "WEEKLY",
        },
        {
            "fred_id": "CPIAUCSL",
            "code": "US_CPI_INDEX",
            "name": "US Consumer Price Index (All Urban, BLS)",
            "country": "USA",
            "category": "INFLATION",
            "unit": "INDEX",
            "freq": "MONTHLY",
        },
        {
            "fred_id": "PPIFIS",
            "code": "US_PPI_INDEX",
            "name": "US Producer Price Index Final Demand (BLS)",
            "country": "USA",
            "category": "INFLATION",
            "unit": "INDEX",
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
        {"fred_id": "DCOILBRENTEU", "symbol": "BRENT", "name": "Crude Oil Prices: Brent - Europe", "asset_class": "COMMODITY", "region": "GLOBAL", "unit": "USD_PER_BBL"},
        {"fred_id": "DHHNGSP", "symbol": "NATGAS", "name": "Henry Hub Natural Gas Spot Price", "asset_class": "COMMODITY", "region": "GLOBAL", "unit": "USD_PER_MMBTU"},
        {"fred_id": "PCOPPUSDM", "symbol": "COPPER", "name": "Global Copper Price (IMF/FRED)", "asset_class": "COMMODITY", "region": "GLOBAL", "unit": "USD_PER_MT"},
        {"fred_id": "DTWEXBGS", "symbol": "DXY", "name": "US Broad Trade-Weighted Dollar Index (FRED)", "asset_class": "FX", "region": "GLOBAL", "unit": "INDEX"},
        {"fred_id": "DEXUSEU", "symbol": "EURUSD", "name": "Euro / US Dollar Exchange Rate", "asset_class": "FX", "region": "GLOBAL", "unit": "USD_PER_EUR"},
        {"fred_id": "DEXUSUK", "symbol": "GBPUSD", "name": "British Pound / US Dollar Exchange Rate", "asset_class": "FX", "region": "GLOBAL", "unit": "USD_PER_GBP"},
        {"fred_id": "DEXUSAL", "symbol": "AUDUSD", "name": "Australian Dollar / US Dollar Exchange Rate", "asset_class": "FX", "region": "GLOBAL", "unit": "USD_PER_AUD"},
        {"fred_id": "DEXJPUS", "symbol": "USDJPY", "name": "US Dollar / Japanese Yen Exchange Rate", "asset_class": "FX", "region": "GLOBAL", "unit": "JPY_PER_USD"},
        {"fred_id": "DEXCHUS", "symbol": "USDCNY", "name": "US Dollar / Chinese Yuan Exchange Rate", "asset_class": "FX", "region": "GLOBAL", "unit": "CNY_PER_USD"},
        {"fred_id": "DEXSZUS", "symbol": "USDCHF", "name": "US Dollar / Swiss Franc Exchange Rate", "asset_class": "FX", "region": "GLOBAL", "unit": "CHF_PER_USD"},
        {"fred_id": "DEXCAUS", "symbol": "USDCAD", "name": "US Dollar / Canadian Dollar Exchange Rate", "asset_class": "FX", "region": "GLOBAL", "unit": "CAD_PER_USD"},
        {"fred_id": "DEXSFUS", "symbol": "USDZAR", "name": "US Dollar / South African Rand Exchange Rate", "asset_class": "FX", "region": "AFRICA", "unit": "ZAR_PER_USD"},
    ]

    UST_YIELD_SERIES: List[Tuple[str, str, int, float]] = [
        ("DGS2", "2Y", 730, 2.0),
        ("DGS5", "5Y", 1825, 5.0),
        ("DGS10", "10Y", 3650, 10.0),
        ("DGS30", "30Y", 10950, 30.0),
    ]

    GLOBAL_10Y_BOND_SERIES: List[Tuple[str, str, str]] = [
        ("DGS10", "US_10Y", "United States 10-Year Treasury Yield"),
        ("IRLTLT01GBM156N", "UK_10Y", "United Kingdom 10-Year Gilt Yield"),
        ("IRLTLT01DEM156N", "DE_10Y", "Germany 10-Year Bund Yield"),
        ("IRLTLT01JPM156N", "JP_10Y", "Japan 10-Year JGB Yield"),
        ("IRLTLT01CAM156N", "CA_10Y", "Canada 10-Year Government Bond Yield"),
        ("IRLTLT01AUM156N", "AU_10Y", "Australia 10-Year Government Bond Yield"),
        ("IRLTLT01MXM156N", "MX_10Y", "Mexico 10-Year Government Bond Yield"),
        ("IRLTLT01ZAM156N", "ZA_10Y", "South Africa 10-Year Government Bond Yield"),
        ("IRLTLT01NLM156N", "NL_10Y", "Netherlands 10-Year Government Bond Yield"),
    ]

    def _fetch_series_tail(
        self, fred_id: str, limit: int = 15
    ) -> List[Tuple[datetime, float]]:
        """Fetch latest `limit` observations for a FRED series via JSON API or official CSV."""
        observations: List[Tuple[datetime, float]] = []
        api_key = (settings.FRED_API_KEY or "").strip()
        use_json = bool(api_key and "placeholder" not in api_key.lower())
        try:
            with create_http_client(
                timeout=settings.DATA_PROVIDER_TIMEOUT_SECONDS,
                follow_redirects=True,
            ) as client:
                if use_json:
                    resp = client.get(
                        self.JSON_API_URL,
                        params={
                            "series_id": fred_id,
                            "api_key": api_key,
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

    def fetch_macro_indicators(self, history_limit: int = 18) -> List[IngestedMacroPoint]:
        points: List[IngestedMacroPoint] = []
        for meta in self.MACRO_SERIES:
            fetch_n = max(15, history_limit) if meta["fred_id"] in ("PAYEMS", "CPIAUCSL", "UNRATE", "PPIFIS") else max(6, history_limit // 2)
            obs = self._fetch_series_tail(meta["fred_id"], limit=fetch_n)
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
                        effective_date=dt,
                        source_code=self.provider_code,
                        source_url=f"https://fred.stlouisfed.org/series/{meta['fred_id']}",
                        source_tier="TIER_1_OFFICIAL",
                        confidence_score=98.0,
                        is_archival_baseline=False,
                        data_frequency=meta["freq"],
                        verification_status="VERIFIED",
                    )
                )

            # Derived Tier-1 monthly Non-Farm Payrolls Change ('000) from PAYEMS
            if meta["fred_id"] == "PAYEMS" and len(obs) >= 2:
                prev_chg: Optional[float] = None
                for idx in range(1, len(obs)):
                    dt, val = obs[idx]
                    chg_k = round(val - obs[idx - 1][1], 1)
                    points.append(
                        IngestedMacroPoint(
                            indicator_code="US_NFP_CHANGE_K",
                            indicator_name="US Non-Farm Payrolls Monthly Change ('000, BLS)",
                            country="USA",
                            category="EMPLOYMENT",
                            value=chg_k,
                            previous_value=prev_chg,
                            currency_or_unit="THOUSANDS",
                            reporting_period=dt.strftime("%Y-%m"),
                            publication_date=dt,
                            effective_date=dt,
                            source_code=self.provider_code,
                            source_url="https://fred.stlouisfed.org/series/PAYEMS",
                            source_tier="TIER_1_OFFICIAL",
                            confidence_score=98.0,
                            is_archival_baseline=False,
                            data_frequency="MONTHLY",
                            verification_status="VERIFIED",
                        )
                    )
                    prev_chg = chg_k

            # Derived Tier-1 US CPI YoY (%) from CPIAUCSL
            if meta["fred_id"] == "CPIAUCSL" and len(obs) >= 13:
                prev_yoy: Optional[float] = None
                for idx in range(12, len(obs)):
                    dt, val = obs[idx]
                    val_12m_ago = obs[idx - 12][1]
                    if val_12m_ago > 0:
                        yoy_pct = round(((val / val_12m_ago) - 1.0) * 100.0, 2)
                        points.append(
                            IngestedMacroPoint(
                                indicator_code="US_CPI_YOY",
                                indicator_name="US Headline Consumer Price Inflation (YoY, BLS)",
                                country="USA",
                                category="INFLATION",
                                value=yoy_pct,
                                previous_value=prev_yoy,
                                currency_or_unit="PERCENT",
                                reporting_period=dt.strftime("%Y-%m"),
                                publication_date=dt,
                                effective_date=dt,
                                source_code=self.provider_code,
                                source_url="https://fred.stlouisfed.org/series/CPIAUCSL",
                                source_tier="TIER_1_OFFICIAL",
                                confidence_score=98.0,
                                is_archival_baseline=False,
                                data_frequency="MONTHLY",
                                verification_status="VERIFIED",
                            )
                        )
                        prev_yoy = yoy_pct
        return points

    def fetch_market_timeseries(
        self,
        symbols: Optional[List[str]] = None,
        history_limit: int = 260,
    ) -> List[IngestedMarketPoint]:
        points: List[IngestedMarketPoint] = []
        for meta in self.MARKET_SERIES:
            if symbols and meta["symbol"] not in symbols:
                continue
            lim = 24 if meta["fred_id"] == "PCOPPUSDM" else min(260, max(30, history_limit))
            obs = self._fetch_series_tail(meta["fred_id"], limit=lim)
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
                        effective_date=dt,
                        source_code=self.provider_code,
                        source_url=f"https://fred.stlouisfed.org/series/{meta['fred_id']}",
                        source_tier="TIER_1_OFFICIAL",
                        confidence_score=97.0,
                        is_archival_baseline=False,
                        data_frequency="MONTHLY" if meta["fred_id"] == "PCOPPUSDM" else "DAILY",
                        verification_status="VERIFIED",
                    )
                )
        return points

    def fetch_yield_curves(self, history_limit: int = 15) -> List[IngestedYieldPoint]:
        points: List[IngestedYieldPoint] = []
        for fred_id, tenor_lbl, t_days, t_years in self.UST_YIELD_SERIES:
            obs = self._fetch_series_tail(fred_id, limit=max(5, history_limit))
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
                        effective_date=dt,
                        source_code=self.provider_code,
                        source_url=f"https://fred.stlouisfed.org/series/{fred_id}",
                        source_tier="TIER_1_OFFICIAL",
                        confidence_score=98.0,
                        is_archival_baseline=False,
                        data_frequency="DAILY",
                        verification_status="VERIFIED",
                    )
                )

        # Global 10-Year Sovereign Government Bond Yields (9 major & emerging economies)
        for fred_id, tenor_lbl, ind_name in self.GLOBAL_10Y_BOND_SERIES:
            obs = self._fetch_series_tail(fred_id, limit=14)
            for dt, val in obs:
                points.append(
                    IngestedYieldPoint(
                        curve_name="GLOBAL_10Y_SOVEREIGN",
                        instrument_type="GLOBAL_10Y_BOND",
                        tenor_label=tenor_lbl,
                        tenor_days=3650,
                        tenor_years=10.0,
                        indicator_name=ind_name,
                        value=val,
                        currency_or_unit="PERCENT",
                        reporting_period=dt.strftime("%Y-%m-%d"),
                        publication_date=dt,
                        effective_date=dt,
                        source_code=self.provider_code,
                        source_url=f"https://fred.stlouisfed.org/series/{fred_id}",
                        source_tier="TIER_1_OFFICIAL",
                        confidence_score=97.0,
                        is_archival_baseline=False,
                        data_frequency="DAILY" if fred_id == "DGS10" else "MONTHLY",
                        verification_status="VERIFIED",
                    )
                )
        return points


class YahooFinanceFreeProvider(BaseMarketDataProvider):
    """
    Zero-key public Yahoo Finance Chart JSON adapter for global indices and DXY that
    return HTTP 402 on FMP's free tier (Germany DAX, Brazil Bovespa, South Africa JSE,
    and ICE US Dollar Index DXY). Delivers ~250 daily closing sessions with zero API cost.
    """

    provider_code = "YAHOO_FINANCE_FREE"
    provider_name = "Yahoo Finance Public Market Feed"
    reliability_tier = "TIER_2_INSTITUTIONAL"
    CHART_BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"

    FREE_GLOBAL_SYMBOLS: List[Tuple[str, str, str, str, str, str]] = [
        ("^GDAXI", "DAX", "Germany DAX Index", "INDEX", "GLOBAL", "INDEX_POINTS"),
        ("^BVSP", "BOVESPA", "Brazil Bovespa Index", "INDEX", "GLOBAL", "INDEX_POINTS"),
        ("^J203.JO", "JSE", "Johannesburg Stock Exchange All-Share Index", "INDEX", "AFRICA", "INDEX_POINTS"),
        ("DX-Y.NYB", "DXY_ICE", "ICE US Dollar Index (DXY)", "FX", "GLOBAL", "INDEX"),
    ]

    def fetch_market_timeseries(
        self,
        symbols: Optional[List[str]] = None,
        history_range: str = "1y",
    ) -> List[IngestedMarketPoint]:
        points: List[IngestedMarketPoint] = []
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
            )
        }
        target = self.FREE_GLOBAL_SYMBOLS
        if symbols:
            target = [t for t in self.FREE_GLOBAL_SYMBOLS if t[0] in symbols or t[1] in symbols]

        try:
            with create_http_client(
                timeout=settings.DATA_PROVIDER_TIMEOUT_SECONDS,
                headers=headers,
                follow_redirects=True,
            ) as client:
                for yf_sym, db_sym, name, asset_cls, region, unit in target:
                    try:
                        resp = client.get(
                            f"{self.CHART_BASE_URL}/{yf_sym}",
                            params={"range": history_range, "interval": "1d"},
                        )
                        if resp.status_code != 200:
                            continue
                        res_list = resp.json().get("chart", {}).get("result") or []
                        if not res_list:
                            continue
                        res0 = res_list[0]
                        timestamps = res0.get("timestamp") or []
                        quote = (res0.get("indicators", {}).get("quote") or [{}])[0]
                        closes = quote.get("close") or []
                        volumes = quote.get("volume") or []
                        for idx, (ts, px) in enumerate(zip(timestamps, closes)):
                            if px is None or px <= 0:
                                continue
                            dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
                            vol = volumes[idx] if idx < len(volumes) else None
                            points.append(
                                IngestedMarketPoint(
                                    symbol=db_sym,
                                    indicator_name=name,
                                    asset_class=asset_cls,
                                    market_region=region,
                                    value=round(float(px), 4),
                                    close_value=round(float(px), 4),
                                    volume=float(vol) if vol is not None else None,
                                    currency_or_unit=unit,
                                    reporting_period=dt.strftime("%Y-%m-%d"),
                                    publication_date=dt,
                                    effective_date=dt,
                                    source_code=self.provider_code,
                                    source_url=f"https://finance.yahoo.com/quote/{yf_sym}",
                                    source_tier="TIER_2_INSTITUTIONAL",
                                    confidence_score=91.0,
                                    is_archival_baseline=False,
                                    data_frequency="DAILY",
                                    verification_status="VERIFIED",
                                )
                            )
                    except Exception as sym_exc:
                        logger.info("YahooFinanceFreeProvider note for %s: %s", yf_sym, sym_exc)
        except Exception as exc:
            logger.warning("YahooFinanceFreeProvider error: %s", exc)
        return points

