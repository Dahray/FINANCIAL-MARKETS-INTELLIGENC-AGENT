"""
Official Nigerian Financial Market & Regulatory Data Providers:
- Central Bank of Nigeria (CBN)
- Nigerian Exchange Group (NGX)
- FMDQ Securities Exchange & Debt Management Office (DMO)
- National Bureau of Statistics (NBS), SEC Nigeria, PenCom, NAICOM
- Financial Statement & Annual Report PDF Extractor
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import httpx
try:
    from pypdf import PdfReader
except ImportError:
    from PyPDF2 import PdfReader  # type: ignore[no-redef]

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import PromptInjectionSanitizer
from app.core.ssl_helper import create_http_client
from app.providers.base import (
    BaseMacroDataProvider,
    BaseMarketDataProvider,
    BaseRegulatoryProvider,
    IngestedMacroPoint,
    IngestedMarketPoint,
    IngestedResearchItem,
    IngestedYieldPoint,
)

logger = get_logger("fmip.providers.nigerian")


def _http_headers() -> Dict[str, str]:
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }


def _cbn_get_json(client: httpx.Client, url: str) -> Optional[Any]:
    """Fetch JSON from an official CBN endpoint with single automatic retry on transient TLS timeout."""
    for attempt in range(2):
        try:
            resp = client.get(url)
            if resp.status_code == 200:
                return resp.json()
        except Exception as exc:
            if attempt == 1:
                logger.warning("CBN endpoint fetch note (%s): %s", url, exc)
    return None


def _safe_float(val: Any) -> Optional[float]:
    """Parse numeric string from CBN JSON payloads cleanly."""
    if val is None:
        return None
    s = str(val).replace(",", "").replace("%", "").strip()
    if not s or s in ("-", "N/A", "null", "None"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _parse_cbn_date(date_str: str) -> Optional[datetime]:
    """Parse CBN API date formats ('November-25-2026', '24/11/2026', '2026-11-25', '05/11/2026')."""
    s = (date_str or "").strip()
    if not s:
        return None
    for fmt in ("%B-%d-%Y", "%d/%m/%Y", "%Y-%m-%d", "%b-%d-%Y", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _month_end_utc(year: int, month: int) -> datetime:
    """Return UTC end-of-month datetime for monthly official CBN macro releases."""
    import calendar

    last_day = calendar.monthrange(year, month)[1]
    return datetime(year, month, last_day, 15, 0, 0, tzinfo=timezone.utc)


class CBNDataProvider(BaseMacroDataProvider, BaseMarketDataProvider, BaseRegulatoryProvider):
    """
    Central Bank of Nigeria (CBN) TIER-1 OFFICIAL primary data provider.
    Directly queries CBN's official public JSON REST endpoints:
      - /api/GetAllMoneyMarketIndicators  (MPR, Interbank Call, 91D T-Bill, Lending & Deposit Rates)
      - /api/GetAllInflationRates         (Headline CPI YoY, Food CPI YoY, Core CPI YoY)
      - /api/GetAllNFEM_Rates             (Official NFEM USD/NGN Closing, High, Low, Weighted Avg, Turnover)
      - /api/GetAllReserves               (Daily Gross & Liquid External Reserves in USD)
      - /api/GetAllCrudeOilPrices         (Bonny Light Crude Oil Price, Domestic Production & Exports)
      - /api/GetAllSecuritiesNTB          (Primary Market Nigerian Treasury Bill 91D/182D/364D Auctions)
      - /api/GetAllCirculars              (Official CBN Regulatory Circulars with Reference Numbers & PDFs)
    """

    provider_code = "CBN_OFFICIAL"
    provider_name = "Central Bank of Nigeria (CBN)"
    regulator_code = "CBN"
    reliability_tier = "TIER_1_OFFICIAL"

    def fetch_macro_indicators(self, months_limit: int = 24) -> List[IngestedMacroPoint]:
        """Retrieve live official CBN MPR, Lending Rates, Inflation (Headline/Food/Core), External Reserves, and Crude Production."""
        results: List[IngestedMacroPoint] = []
        base = settings.CBN_BASE_URL.rstrip("/")

        with create_http_client(
            timeout=25,
            headers=_http_headers(),
            follow_redirects=True,
        ) as client:
            # 1. Official CBN Money Market Indicators -> MPR, Prime Lending, Max Lending
            rows = _cbn_get_json(client, f"{base}/api/GetAllMoneyMarketIndicators")
            if isinstance(rows, list):
                valid_rows = [
                    r for r in rows
                    if isinstance(r, dict) and r.get("tyear") and r.get("tmonth")
                ]
                valid_rows.sort(key=lambda r: (int(r["tyear"]), int(r["tmonth"])))
                recent = valid_rows[-months_limit:]

                prev_map: Dict[str, Optional[float]] = {}
                for row in recent:
                    yr, mo = int(row["tyear"]), int(row["tmonth"])
                    dt = _month_end_utc(yr, mo)
                    period_str = f"{yr:04d}-{mo:02d}"

                    field_specs = [
                        ("mpr", "NG_CBN_MPR", "CBN Monetary Policy Rate (MPR)", "MONETARY_POLICY", "PERCENT", "EVENT_DRIVEN"),
                        ("primeLending", "NG_PRIME_LENDING_RATE", "CBN Commercial Banks Prime Lending Rate", "MONETARY_POLICY", "PERCENT", "MONTHLY"),
                        ("maxLending", "NG_MAX_LENDING_RATE", "CBN Commercial Banks Maximum Lending Rate", "MONETARY_POLICY", "PERCENT", "MONTHLY"),
                        ("savingsDeposit", "NG_SAVINGS_DEPOSIT_RATE", "CBN Average Savings Deposit Rate", "MONETARY_POLICY", "PERCENT", "MONTHLY"),
                    ]
                    for field_key, code, name, cat, unit, freq in field_specs:
                        val = _safe_float(row.get(field_key))
                        if val is not None and val > 0:
                            results.append(
                                IngestedMacroPoint(
                                    indicator_code=code,
                                    indicator_name=name,
                                    country="NIGERIA",
                                    category=cat,
                                    value=val,
                                    previous_value=prev_map.get(code),
                                    currency_or_unit=unit,
                                    reporting_period=period_str,
                                    publication_date=dt,
                                    effective_date=dt,
                                    source_code=self.provider_code,
                                    source_url=f"{base}/rates/mnymktind.html",
                                    source_tier="TIER_1_OFFICIAL",
                                    confidence_score=99.0,
                                    is_archival_baseline=False,
                                    data_frequency=freq,
                                    verification_status="VERIFIED",
                                )
                            )
                            prev_map[code] = val

            # 2. Official CBN/NBS Inflation Rates -> Headline, Food, Core CPI YoY
            inf_rows = _cbn_get_json(client, f"{base}/api/GetAllInflationRates")
            if isinstance(inf_rows, list):
                valid_inf = [
                    r for r in inf_rows
                    if isinstance(r, dict) and r.get("tyear") and r.get("tmonth")
                ]
                valid_inf.sort(key=lambda r: (int(r["tyear"]), int(r["tmonth"])))
                recent_inf = valid_inf[-months_limit:]

                prev_inf: Dict[str, Optional[float]] = {}
                for row in recent_inf:
                    yr, mo = int(row["tyear"]), int(row["tmonth"])
                    dt = _month_end_utc(yr, mo)
                    period_str = f"{yr:04d}-{mo:02d}"
                    inf_specs = [
                        ("allItemsYearOn", "NG_CPI_HEADLINE_YOY", "Nigeria Headline Consumer Price Inflation (YoY)"),
                        ("foodYearOn", "NG_CPI_FOOD_YOY", "Nigeria Food Inflation Index (YoY)"),
                        ("allItemsLessFrmProdAndEnergyYearOn", "NG_CPI_CORE_YOY", "Nigeria Core Inflation Ex-Farm & Energy (YoY)"),
                    ]
                    for fkey, code, name in inf_specs:
                        val = _safe_float(row.get(fkey))
                        if val is not None and val > 0:
                            results.append(
                                IngestedMacroPoint(
                                    indicator_code=code,
                                    indicator_name=name,
                                    country="NIGERIA",
                                    category="INFLATION",
                                    value=val,
                                    previous_value=prev_inf.get(code),
                                    currency_or_unit="PERCENT",
                                    reporting_period=period_str,
                                    publication_date=dt,
                                    effective_date=dt,
                                    source_code=self.provider_code,
                                    source_url=f"{base}/rates/inflrates.html",
                                    source_tier="TIER_1_OFFICIAL",
                                    confidence_score=99.0,
                                    is_archival_baseline=False,
                                    data_frequency="MONTHLY",
                                    verification_status="VERIFIED",
                                )
                            )
                            prev_inf[code] = val

            # 3. Official CBN Daily Gross External Reserves (converted from USD to USD Billions)
            res_rows = _cbn_get_json(client, f"{base}/api/GetAllReserves")
            if isinstance(res_rows, list):
                parsed_res: List[tuple[datetime, float]] = []
                for row in res_rows[:90]:
                    dt = _parse_cbn_date(str(row.get("moveDate", "")))
                    gross_usd = _safe_float(row.get("gross"))
                    if dt and gross_usd and gross_usd > 1_000_000_000:
                        parsed_res.append((dt, round(gross_usd / 1_000_000_000.0, 4)))
                parsed_res.sort(key=lambda x: x[0])
                prev_r: Optional[float] = None
                for dt, val_bn in parsed_res[-45:]:
                    results.append(
                        IngestedMacroPoint(
                            indicator_code="NG_FX_RESERVES_USD",
                            indicator_name="CBN Gross External Reserves (Official Daily)",
                            country="NIGERIA",
                            category="EXTERNAL_RESERVES",
                            value=val_bn,
                            previous_value=prev_r,
                            currency_or_unit="USD_BILLION",
                            reporting_period=dt.strftime("%Y-%m-%d"),
                            publication_date=dt,
                            effective_date=dt,
                            source_code=self.provider_code,
                            source_url=f"{base}/IntOps/reserve.html",
                            source_tier="TIER_1_OFFICIAL",
                            confidence_score=99.0,
                            is_archival_baseline=False,
                            data_frequency="DAILY",
                            verification_status="VERIFIED",
                        )
                    )
                    prev_r = val_bn

            # 4. Official CBN Domestic Crude Oil Production (mbpd)
            oil_rows = _cbn_get_json(client, f"{base}/api/GetAllCrudeOilPrices")
            if isinstance(oil_rows, list):
                valid_oil = [
                    r for r in oil_rows
                    if isinstance(r, dict) and r.get("tyear") and r.get("tmonth")
                ]
                valid_oil.sort(key=lambda r: (int(r["tyear"]), int(r["tmonth"])))
                prev_prod: Optional[float] = None
                for row in valid_oil[-18:]:
                    yr, mo = int(row["tyear"]), int(row["tmonth"])
                    dt = _month_end_utc(yr, mo)
                    prod = _safe_float(row.get("domProd"))
                    if prod is not None and prod > 0:
                        results.append(
                            IngestedMacroPoint(
                                indicator_code="NG_CRUDE_PRODUCTION_MBPD",
                                indicator_name="Nigeria Domestic Crude Oil Production (CBN)",
                                country="NIGERIA",
                                category="ENERGY_OUTPUT",
                                value=prod,
                                previous_value=prev_prod,
                                currency_or_unit="MBPD",
                                reporting_period=f"{yr:04d}-{mo:02d}",
                                publication_date=dt,
                                effective_date=dt,
                                source_code=self.provider_code,
                                source_url=f"{base}/rates/crudeoil.html",
                                source_tier="TIER_1_OFFICIAL",
                                confidence_score=98.0,
                                is_archival_baseline=False,
                                data_frequency="MONTHLY",
                                verification_status="VERIFIED",
                            )
                        )
                        prev_prod = prod

        return results

    def fetch_market_timeseries(
        self, symbols: Optional[List[str]] = None
    ) -> List[IngestedMarketPoint]:
        """
        Fetch live official CBN market time-series:
        - NFEM / NAFEM Official USD/NGN Closing, High, Low, Turnover (`/api/GetAllNFEM_Rates`)
        - Official Bonny Light Crude Oil Price (`/api/GetAllCrudeOilPrices`)
        - Official CBN Interbank Call Rate (`/api/GetAllMoneyMarketIndicators`)
        """
        points: List[IngestedMarketPoint] = []
        base = settings.CBN_BASE_URL.rstrip("/")

        with create_http_client(
            timeout=25,
            headers=_http_headers(),
            follow_redirects=True,
        ) as client:
            # 1. Official CBN NFEM USD/NGN Rates (last 60 business days)
            fx_rows = _cbn_get_json(client, f"{base}/api/GetAllNFEM_Rates")
            if isinstance(fx_rows, list):
                parsed_fx: List[tuple[datetime, Dict[str, Any]]] = []
                for row in fx_rows[:90]:
                    dt = _parse_cbn_date(str(row.get("ratedate", "")))
                    close_val = _safe_float(row.get("closingrate")) or _safe_float(row.get("weightedAvgRate"))
                    if dt and close_val and close_val > 100:
                        parsed_fx.append((dt, row))
                parsed_fx.sort(key=lambda x: x[0])
                for dt, row in parsed_fx[-60:]:
                    close_val = _safe_float(row.get("closingrate")) or _safe_float(row.get("weightedAvgRate"))
                    if close_val is None:
                        continue
                    points.append(
                        IngestedMarketPoint(
                            symbol="NGNUSD.NAFEM",
                            indicator_name="CBN Official NFEM (NAFEM) USD/NGN Closing Rate",
                            asset_class="FX",
                            market_region="NIGERIA",
                            value=close_val,
                            open_value=_safe_float(row.get("weightedAvgRate")),
                            high_value=_safe_float(row.get("highestrate")),
                            low_value=_safe_float(row.get("lowestrate")),
                            close_value=close_val,
                            volume=_safe_float(row.get("nfeM_Total_Turnover")),
                            currency_or_unit="NGN_PER_USD",
                            reporting_period=dt.strftime("%Y-%m-%d"),
                            publication_date=dt,
                            effective_date=dt,
                            source_code=self.provider_code,
                            source_url=f"{base}/rates/ExchRateByCurrency.html",
                            source_tier="TIER_1_OFFICIAL",
                            confidence_score=99.0,
                            is_archival_baseline=False,
                            data_frequency="DAILY",
                            verification_status="VERIFIED",
                        )
                    )

            # 2. Official CBN Bonny Light Crude Oil Price (last 24 months)
            oil_rows = _cbn_get_json(client, f"{base}/api/GetAllCrudeOilPrices")
            if isinstance(oil_rows, list):
                valid_oil = [
                    r for r in oil_rows
                    if isinstance(r, dict) and r.get("tyear") and r.get("tmonth")
                ]
                valid_oil.sort(key=lambda r: (int(r["tyear"]), int(r["tmonth"])))
                for row in valid_oil[-24:]:
                    yr, mo = int(row["tyear"]), int(row["tmonth"])
                    dt = _month_end_utc(yr, mo)
                    px = _safe_float(row.get("crudeOilPrice"))
                    if px and px > 10:
                        points.append(
                            IngestedMarketPoint(
                                symbol="BONNYLIGHT",
                                indicator_name="Nigerian Bonny Light Crude Oil (Official CBN)",
                                asset_class="COMMODITY",
                                market_region="NIGERIA",
                                value=px,
                                close_value=px,
                                currency_or_unit="USD_PER_BBL",
                                reporting_period=f"{yr:04d}-{mo:02d}",
                                publication_date=dt,
                                effective_date=dt,
                                source_code=self.provider_code,
                                source_url=f"{base}/rates/crudeoil.html",
                                source_tier="TIER_1_OFFICIAL",
                                confidence_score=98.0,
                                is_archival_baseline=False,
                                data_frequency="MONTHLY",
                                verification_status="VERIFIED",
                            )
                        )

            # 3. Official CBN Interbank Call Rate -> NG_OPR_RATE (last 24 months)
            mm_rows = _cbn_get_json(client, f"{base}/api/GetAllMoneyMarketIndicators")
            if isinstance(mm_rows, list):
                valid_mm = [
                    r for r in mm_rows
                    if isinstance(r, dict) and r.get("tyear") and r.get("tmonth")
                ]
                valid_mm.sort(key=lambda r: (int(r["tyear"]), int(r["tmonth"])))
                for row in valid_mm[-24:]:
                    yr, mo = int(row["tyear"]), int(row["tmonth"])
                    dt = _month_end_utc(yr, mo)
                    ib_val = _safe_float(row.get("interBankCallRate"))
                    if ib_val and ib_val > 0:
                        points.append(
                            IngestedMarketPoint(
                                symbol="NG_OPR_RATE",
                                indicator_name="CBN Official Interbank Call / Money Market Rate",
                                asset_class="MONEY_MARKET",
                                market_region="NIGERIA",
                                value=ib_val,
                                close_value=ib_val,
                                currency_or_unit="PERCENT",
                                reporting_period=f"{yr:04d}-{mo:02d}",
                                publication_date=dt,
                                effective_date=dt,
                                source_code=self.provider_code,
                                source_url=f"{base}/rates/mnymktind.html",
                                source_tier="TIER_1_OFFICIAL",
                                confidence_score=98.0,
                                is_archival_baseline=False,
                                data_frequency="MONTHLY",
                                verification_status="VERIFIED",
                            )
                        )

        return points

    def fetch_yield_curves(self) -> List[IngestedYieldPoint]:
        """
        Fetch live Primary Market Nigerian Treasury Bill (91D / 182D / 364D) auctions
        from `/api/GetAllSecuritiesNTB` with true stop rates and bid-to-cover ratios.
        """
        points: List[IngestedYieldPoint] = []
        base = settings.CBN_BASE_URL.rstrip("/")

        tenor_map = {
            "91": ("91D", 91, round(91.0 / 365.0, 4)),
            "182": ("182D", 182, round(182.0 / 365.0, 4)),
            "364": ("364D", 364, 1.0),
        }

        with create_http_client(
            timeout=25,
            headers=_http_headers(),
            follow_redirects=True,
        ) as client:
            rows = _cbn_get_json(client, f"{base}/api/GetAllSecuritiesNTB")
            if isinstance(rows, list):
                for row in rows[:30]:
                    dt = _parse_cbn_date(str(row.get("auctionDate", "")))
                    rate_val = _safe_float(row.get("rate"))
                    if not dt or rate_val is None or rate_val <= 0:
                        continue
                    tenor_raw = re.sub(r"[^0-9]", "", str(row.get("tenor", "")))
                    if tenor_raw not in tenor_map:
                        continue
                    t_lbl, t_days, t_yrs = tenor_map[tenor_raw]
                    sub = _safe_float(row.get("totalSubscription"))
                    offered = _safe_float(row.get("amtOffered"))
                    btc = round(sub / offered, 2) if (sub and offered and offered > 0) else None
                    points.append(
                        IngestedYieldPoint(
                            curve_name="NGN_SOVEREIGN_FMDQ",
                            instrument_type="NTB",
                            tenor_label=t_lbl,
                            tenor_days=t_days,
                            tenor_years=t_yrs,
                            indicator_name=f"CBN Primary Auction NTB {t_lbl} Stop Rate",
                            value=rate_val,
                            bid_to_cover=btc,
                            currency_or_unit="PERCENT",
                            reporting_period=dt.strftime("%Y-%m-%d"),
                            publication_date=dt,
                            effective_date=dt,
                            source_code=self.provider_code,
                            source_url=f"{base}/rates/GovtSecurities.html",
                            source_tier="TIER_1_OFFICIAL",
                            confidence_score=99.0,
                            is_archival_baseline=False,
                            data_frequency="BIWEEKLY",
                            verification_status="VERIFIED",
                        )
                    )
        return points

    def fetch_regulatory_publications(self) -> List[IngestedResearchItem]:
        """Fetch official CBN circulars from `/api/GetAllCirculars` with real documentDate, refNo & PDF URLs."""
        items: List[IngestedResearchItem] = []
        base = settings.CBN_BASE_URL.rstrip("/")

        with create_http_client(
            timeout=25,
            headers=_http_headers(),
            follow_redirects=True,
        ) as client:
            rows = _cbn_get_json(client, f"{base}/api/GetAllCirculars")
            if isinstance(rows, list):
                for row in rows[:12]:
                    title = str(row.get("title", "")).strip()
                    link = str(row.get("link", "")).strip()
                    ref_no = str(row.get("refNo", "")).strip()
                    desc = str(row.get("description", "")).strip()
                    doc_dt = _parse_cbn_date(str(row.get("documentDate", ""))) or datetime.now(timezone.utc)
                    if len(title) < 10:
                        continue
                    full_url = urljoin(base + "/", link.lstrip("/")) if link else f"{base}/Documents/circulars.html"
                    raw_summary = f"[{ref_no}] {title}. {desc}".strip()
                    sanitized = PromptInjectionSanitizer.sanitize(
                        raw_summary, source_id=self.provider_code, source_url=full_url
                    )
                    items.append(
                        IngestedResearchItem(
                            source_code=self.provider_code,
                            source_name=self.provider_name,
                            publication_title=sanitized.clean_text[:300],
                            publication_date=doc_dt,
                            url=full_url,
                            raw_content=sanitized.wrapped_evidence_block,
                            relevant_finding=sanitized.clean_text,
                            document_type="REGULATORY_CIRCULAR",
                            issuer="Central Bank of Nigeria (CBN)",
                            reference_number=ref_no or None,
                            reliability_classification=self.reliability_tier,
                            epistemic_type="FACT",
                            verification_status="VERIFIED",
                        )
                    )
        return items




class NGXDataProvider(BaseMarketDataProvider):
    """
    Nigerian Exchange Group (NGX) market data provider for the NGX All-Share Index (ASI),
    sector indices, and major Nigerian listed equities.
    """

    provider_code = "NGX_OFFICIAL"
    provider_name = "Nigerian Exchange Group (NGX)"
    reliability_tier = "TIER_1_OFFICIAL"

    def fetch_market_timeseries(
        self, symbols: Optional[List[str]] = None
    ) -> List[IngestedMarketPoint]:
        """Attempt live NGX market snapshot ingestion from ngxgroup.com."""
        points: List[IngestedMarketPoint] = []
        now_utc = datetime.now(timezone.utc)
        try:
            with create_http_client(
                timeout=settings.DATA_PROVIDER_TIMEOUT_SECONDS,
                headers=_http_headers(),
                follow_redirects=True,
            ) as client:
                resp = client.get(settings.NGX_BASE_URL)
                if resp.status_code == 200 and resp.text:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    text_blob = soup.get_text(" ", strip=True)
                    asi_match = re.search(
                        r"All[- ]Share\s+Index[^0-9]{0,25}([\d,]+\.\d{2})",
                        text_blob,
                        re.IGNORECASE,
                    )
                    if asi_match:
                        asi_val = float(asi_match.group(1).replace(",", ""))
                        if asi_val > 10_000:
                            points.append(
                                IngestedMarketPoint(
                                    symbol="NGXASI",
                                    indicator_name="NGX All-Share Index (ASI)",
                                    asset_class="INDEX",
                                    market_region="NIGERIA",
                                    value=asi_val,
                                    close_value=asi_val,
                                    currency_or_unit="INDEX_POINTS",
                                    reporting_period=now_utc.strftime("%Y-%m-%d"),
                                    publication_date=now_utc,
                                    source_code=self.provider_code,
                                    source_url=settings.NGX_BASE_URL,
                                    data_frequency="DAILY",
                                    verification_status="VERIFIED",
                                )
                            )
        except Exception as exc:
            logger.info("NGX live snapshot fetch note: %s", exc)
        return points


class FMDQDMODataProvider(BaseMarketDataProvider):
    """
    FMDQ Securities Exchange & Debt Management Office (DMO) provider for
    Nigerian sovereign yield curves (NTB 91D/182D/364D, FGN Bonds 2Y-30Y),
    NAFEM FX rate, and money market indicators (OPR/OVN).
    """

    provider_code = "FMDQ_OFFICIAL"
    provider_name = "FMDQ Securities Exchange"
    reliability_tier = "TIER_1_OFFICIAL"

    def fetch_market_timeseries(
        self, symbols: Optional[List[str]] = None
    ) -> List[IngestedMarketPoint]:
        """Attempt live NAFEM FX and money market fetch from fmdqgroup.com."""
        points: List[IngestedMarketPoint] = []
        now_utc = datetime.now(timezone.utc)
        try:
            with create_http_client(
                timeout=settings.DATA_PROVIDER_TIMEOUT_SECONDS,
                headers=_http_headers(),
                follow_redirects=True,
            ) as client:
                resp = client.get(settings.FMDQ_BASE_URL)
                if resp.status_code == 200 and resp.text:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    text_blob = soup.get_text(" ", strip=True)
                    fx_match = re.search(
                        r"(?:NAFEM|NFEM|USD/NGN)[^0-9]{0,25}(1,\d{3}\.\d{2}|\d{4}\.\d{2})",
                        text_blob,
                        re.IGNORECASE,
                    )
                    if fx_match:
                        fx_val = float(fx_match.group(1).replace(",", ""))
                        points.append(
                            IngestedMarketPoint(
                                symbol="NGNUSD.NAFEM",
                                indicator_name="Nigerian Autonomous Foreign Exchange Market (NAFEM) USD/NGN Closing Rate",
                                asset_class="FX",
                                market_region="NIGERIA",
                                value=fx_val,
                                close_value=fx_val,
                                currency_or_unit="NGN_PER_USD",
                                reporting_period=now_utc.strftime("%Y-%m-%d"),
                                publication_date=now_utc,
                                source_code=self.provider_code,
                                source_url=settings.FMDQ_BASE_URL,
                                data_frequency="DAILY",
                                verification_status="VERIFIED",
                            )
                        )
        except Exception as exc:
            logger.info("FMDQ live snapshot fetch note: %s", exc)
        return points


class NigerianRegulatorsMonitorProvider(BaseRegulatoryProvider):
    """
    Monitors official announcements from SEC Nigeria, PenCom, NAICOM, and DMO.
    Prioritizes official publications and sanitizes all external HTML text.
    """

    provider_code = "SEC_NIGERIA"
    provider_name = "Securities and Exchange Commission (SEC Nigeria)"
    regulator_code = "SEC_NG"
    reliability_tier = "TIER_1_OFFICIAL"

    REGULATOR_TARGETS = [
        ("SEC_NIGERIA", "Securities and Exchange Commission (SEC Nigeria)", "SEC_NG", settings.SEC_NIGERIA_BASE_URL),
        ("PENCOM", "National Pension Commission (PenCom)", "PENCOM", settings.PENCOM_BASE_URL),
        ("NAICOM", "National Insurance Commission (NAICOM)", "NAICOM", settings.NAICOM_BASE_URL),
        ("DMO_OFFICIAL", "Debt Management Office (DMO)", "FMF_NG", settings.DMO_BASE_URL),
    ]

    def fetch_regulatory_publications(self) -> List[IngestedResearchItem]:
        items: List[IngestedResearchItem] = []
        now_utc = datetime.now(timezone.utc)
        with create_http_client(
            timeout=settings.DATA_PROVIDER_TIMEOUT_SECONDS,
            headers=_http_headers(),
            follow_redirects=True,
        ) as client:
            for src_code, src_name, reg_code, base_url in self.REGULATOR_TARGETS:
                try:
                    resp = client.get(base_url)
                    if resp.status_code != 200 or not resp.text:
                        continue
                    soup = BeautifulSoup(resp.text, "html.parser")
                    count = 0
                    for a_tag in soup.find_all("a", href=True):
                        title = a_tag.get_text(" ", strip=True)
                        href = str(a_tag["href"])
                        if len(title) >= 25 and any(
                            kw in title.lower()
                            for kw in (
                                "circular",
                                "guideline",
                                "regulation",
                                "directive",
                                "auction",
                                "bond",
                                "pension",
                                "capital",
                                "notice",
                                "framework",
                            )
                        ):
                            full_url = urljoin(base_url, href)
                            sanitized = PromptInjectionSanitizer.sanitize(
                                title, source_id=src_code, source_url=full_url
                            )
                            items.append(
                                IngestedResearchItem(
                                    source_code=src_code,
                                    source_name=src_name,
                                    publication_title=sanitized.clean_text[:300],
                                    publication_date=now_utc,
                                    url=full_url,
                                    raw_content=sanitized.wrapped_evidence_block,
                                    relevant_finding=sanitized.clean_text,
                                    document_type="REGULATORY_CIRCULAR",
                                    issuer=src_name,
                                    reliability_classification="TIER_1_OFFICIAL",
                                    epistemic_type="FACT",
                                    verification_status="VERIFIED",
                                )
                            )
                            count += 1
                            if count >= 4:
                                break
                except Exception as exc:
                    logger.info("Regulator monitor note for %s: %s", src_code, exc)
        return items


class FinancialStatementPDFExtractor:
    """
    Section 4 Mandate (#5): 'Extract relevant information from annual reports and financial statements.'
    Parses PDF financial statements or raw text transcripts, sanitizes untrusted text against
    prompt injection, and extracts verifiable financial metrics without fabricating missing fields.
    """

    METRIC_PATTERNS: Dict[str, re.Pattern[str]] = {
        "revenue": re.compile(
            r"(?:Gross\s+Earnings|Revenue|Turnover)\s*[:\-]?\s*(?:NGN|N|\$)?\s*([\d,]+(?:\.\d+)?)",
            re.IGNORECASE,
        ),
        "profit_after_tax": re.compile(
            r"(?:Profit\s+After\s+Tax|Net\s+Income|PAT)\s*[:\-]?\s*(?:NGN|N|\$)?\s*([\d,]+(?:\.\d+)?)",
            re.IGNORECASE,
        ),
        "total_assets": re.compile(
            r"Total\s+Assets\s*[:\-]?\s*(?:NGN|N|\$)?\s*([\d,]+(?:\.\d+)?)",
            re.IGNORECASE,
        ),
        "shareholders_equity": re.compile(
            r"(?:Total\s+Equity|Shareholders['’]?\s+Funds|Book\s+Value\s+of\s+Equity)\s*[:\-]?\s*(?:NGN|N|\$)?\s*([\d,]+(?:\.\d+)?)",
            re.IGNORECASE,
        ),
        "eps": re.compile(
            r"(?:Earnings\s+Per\s+Share|Basic\s+EPS)\s*[:\-]?\s*(?:NGN|N|\$|Kobo)?\s*([\d,]+(?:\.\d+)?)",
            re.IGNORECASE,
        ),
        "capital_adequacy_ratio_pct": re.compile(
            r"Capital\s+Adequacy\s+Ratio(?:\s*\(CAR\))?\s*[:\-]?\s*(\d{1,2}(?:\.\d+)?)\s*%",
            re.IGNORECASE,
        ),
        "npl_ratio_pct": re.compile(
            r"(?:Non[- ]Performing\s+Loan(?:s)?\s+Ratio|NPL\s+Ratio)\s*[:\-]?\s*(\d{1,2}(?:\.\d+)?)\s*%",
            re.IGNORECASE,
        ),
    }

    @classmethod
    def extract_from_text(
        cls,
        raw_text: str,
        issuer: str,
        reporting_period: str,
        source_url: str = "local://financial_statement",
    ) -> IngestedResearchItem:
        """
        Extract structured financial statement figures from annual report text.
        Missing metrics are left absent rather than estimated.
        """
        sanitized = PromptInjectionSanitizer.sanitize(
            raw_text, source_id="ANNUAL_REPORT_EXTRACTOR", source_url=source_url
        )

        extracted: Dict[str, Any] = {
            "issuer": issuer,
            "reporting_period": reporting_period,
            "metrics": {},
            "missing_metrics_flagged": [],
        }

        for metric_key, pattern in cls.METRIC_PATTERNS.items():
            match = pattern.search(sanitized.clean_text)
            if match:
                extracted["metrics"][metric_key] = float(match.group(1).replace(",", ""))
            else:
                extracted["missing_metrics_flagged"].append(metric_key)

        finding_summary = (
            f"Extracted {len(extracted['metrics'])} verified financial statement figures for "
            f"{issuer} ({reporting_period}): {extracted['metrics']}. "
            f"Unreported/unmatched fields flagged: {extracted['missing_metrics_flagged']}."
        )

        return IngestedResearchItem(
            source_code="NGX_OFFICIAL",
            source_name=f"{issuer} Audited Financial Statement / Annual Report",
            publication_title=f"{issuer} Financial Statement ({reporting_period})",
            publication_date=datetime.now(timezone.utc),
            url=source_url,
            raw_content=sanitized.wrapped_evidence_block,
            relevant_finding=finding_summary,
            document_type="FINANCIAL_STATEMENT",
            issuer=issuer,
            reliability_classification="TIER_1_OFFICIAL",
            epistemic_type="FACT",
            verification_status="VERIFIED" if extracted["metrics"] else "FLAGGED_UNVERIFIED",
            structured_extract=extracted,
        )

    @classmethod
    def extract_from_pdf(
        cls,
        pdf_path: str | Path,
        issuer: str,
        reporting_period: str,
    ) -> IngestedResearchItem:
        """Read text from a PDF annual report / financial statement and extract structured figures."""
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF financial statement not found: {path}")

        reader = PdfReader(str(path))
        pages_text = [page.extract_text() or "" for page in reader.pages[:40]]
        full_text = "\n".join(pages_text)
        return cls.extract_from_text(
            raw_text=full_text,
            issuer=issuer,
            reporting_period=reporting_period,
            source_url=f"file:///{path.as_posix()}",
        )
