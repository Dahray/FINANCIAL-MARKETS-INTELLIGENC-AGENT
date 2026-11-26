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
        "User-Agent": settings.DATA_PROVIDER_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/json,application/xml;q=0.9,*/*;q=0.8",
    }


class CBNDataProvider(BaseMacroDataProvider, BaseRegulatoryProvider):
    """
    Central Bank of Nigeria (CBN) official provider for monetary policy indicators,
    FX rates, external reserves, and official CBN regulatory circulars.
    """

    provider_code = "CBN_OFFICIAL"
    provider_name = "Central Bank of Nigeria (CBN)"
    regulator_code = "CBN"
    reliability_tier = "TIER_1_OFFICIAL"

    def fetch_macro_indicators(self) -> List[IngestedMacroPoint]:
        """Attempt live retrieval of published CBN monetary indicators from cbn.gov.ng."""
        results: List[IngestedMacroPoint] = []
        now_utc = datetime.now(timezone.utc)
        try:
            with create_http_client(
                timeout=settings.DATA_PROVIDER_TIMEOUT_SECONDS,
                headers=_http_headers(),
                follow_redirects=True,
            ) as client:
                resp = client.get(f"{settings.CBN_BASE_URL}/rates/mnymktind.asp")
                if resp.status_code == 200 and resp.text:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    text_blob = soup.get_text(" ", strip=True)
                    mpr_match = re.search(
                        r"Monetary\s+Policy\s+Rate[^0-9]{0,30}(\d{1,2}\.\d{1,2})\s*%",
                        text_blob,
                        re.IGNORECASE,
                    )
                    if mpr_match:
                        val = float(mpr_match.group(1))
                        results.append(
                            IngestedMacroPoint(
                                indicator_code="NG_CBN_MPR",
                                indicator_name="CBN Monetary Policy Rate (MPR)",
                                country="NIGERIA",
                                category="MONETARY_POLICY",
                                value=val,
                                currency_or_unit="PERCENT",
                                reporting_period=now_utc.strftime("%Y-%m"),
                                publication_date=now_utc,
                                source_code=self.provider_code,
                                source_url=f"{settings.CBN_BASE_URL}/rates/mnymktind.asp",
                                data_frequency="EVENT_DRIVEN",
                                verification_status="VERIFIED",
                            )
                        )
        except Exception as exc:
            logger.info("CBN live macro endpoint fetch note: %s", exc)
        return results

    def fetch_regulatory_publications(self) -> List[IngestedResearchItem]:
        """Fetch official CBN circulars from cbn.gov.ng/Documents/circulars.asp."""
        items: List[IngestedResearchItem] = []
        now_utc = datetime.now(timezone.utc)
        url = f"{settings.CBN_BASE_URL}/Documents/circulars.asp"
        try:
            with create_http_client(
                timeout=settings.DATA_PROVIDER_TIMEOUT_SECONDS,
                headers=_http_headers(),
                follow_redirects=True,
            ) as client:
                resp = client.get(url)
                if resp.status_code == 200 and resp.text:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for link in soup.find_all("a", href=True)[:10]:
                        href = str(link["href"])
                        title = link.get_text(" ", strip=True)
                        if (
                            len(title) > 20
                            and (".pdf" in href.lower() or "circular" in href.lower())
                        ):
                            full_url = urljoin(settings.CBN_BASE_URL, href)
                            sanitized = PromptInjectionSanitizer.sanitize(
                                title, source_id=self.provider_code, source_url=full_url
                            )
                            items.append(
                                IngestedResearchItem(
                                    source_code=self.provider_code,
                                    source_name=self.provider_name,
                                    publication_title=sanitized.clean_text[:300],
                                    publication_date=now_utc,
                                    url=full_url,
                                    raw_content=sanitized.wrapped_evidence_block,
                                    relevant_finding=sanitized.clean_text,
                                    document_type="REGULATORY_CIRCULAR",
                                    issuer="Central Bank of Nigeria (CBN)",
                                    reliability_classification=self.reliability_tier,
                                    epistemic_type="FACT",
                                    verification_status="VERIFIED",
                                )
                            )
        except Exception as exc:
            logger.info("CBN circular scrape note: %s", exc)
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
