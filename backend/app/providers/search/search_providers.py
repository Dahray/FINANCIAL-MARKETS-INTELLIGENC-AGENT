"""
Search & Financial News Intelligence Providers:
- Tavily Search API (`TavilySearchProvider`)
- Google Custom Search JSON API (`GoogleCustomSearchProvider`)
- Public Financial RSS Provider (`PublicFinancialRSSProvider`)
All retrieved external content is sanitized via `PromptInjectionSanitizer` before returning.
"""

from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import List
import xml.etree.ElementTree as ET

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import PromptInjectionSanitizer
from app.core.ssl_helper import create_http_client
from app.providers.base import BaseSearchProvider, IngestedResearchItem

logger = get_logger("fmip.providers.search")


def _classify_domain_reliability(url: str) -> str:
    """Assign institutional source reliability classification based on domain."""
    u = url.lower()
    if any(
        d in u
        for d in (
            "cbn.gov.ng",
            "sec.gov.ng",
            "ngxgroup.com",
            "fmdqgroup.com",
            "dmo.gov.ng",
            "nigerianstat.gov.ng",
            "pencom.gov.ng",
            "naicom.gov.ng",
            "federalreserve.gov",
            "imf.org",
            "worldbank.org",
        )
    ):
        return "TIER_1_OFFICIAL"
    if any(
        d in u
        for d in (
            "reuters.com",
            "bloomberg.com",
            "ft.com",
            "wsj.com",
            "S&P",
            "moodys.com",
            "fitchratings.com",
        )
    ):
        return "TIER_2_INSTITUTIONAL"
    if any(
        d in u
        for d in (
            "businessday.ng",
            "nairametrics.com",
            "proshare.co",
            "thisdaylive.com",
            "punchng.com",
            "guardian.ng",
            "cnbc.com",
        )
    ):
        return "TIER_3_FINANCIAL_PRESS"
    return "TIER_3_FINANCIAL_PRESS"


class TavilySearchProvider(BaseSearchProvider):
    """
    Tavily Search API integration for deep Nigerian, African, and global financial research.
    """

    provider_code = "TAVILY_SEARCH"
    provider_name = "Tavily AI Research Search API"
    reliability_tier = "TIER_3_FINANCIAL_PRESS"
    API_URL = "https://api.tavily.com/search"

    def search_financial_intelligence(
        self, query: str, max_results: int = 5
    ) -> List[IngestedResearchItem]:
        if not settings.TAVILY_API_KEY:
            logger.info("TAVILY_API_KEY not configured in .env; skipping Tavily API call.")
            return []

        items: List[IngestedResearchItem] = []
        now_utc = datetime.now(timezone.utc)
        try:
            with create_http_client(timeout=settings.DATA_PROVIDER_TIMEOUT_SECONDS) as client:
                resp = client.post(
                    self.API_URL,
                    json={
                        "api_key": settings.TAVILY_API_KEY,
                        "query": query,
                        "search_depth": "advanced",
                        "include_answer": False,
                        "max_results": max_results,
                    },
                )
                if resp.status_code == 200:
                    for res in resp.json().get("results", []):
                        url = str(res.get("url", ""))
                        title = str(res.get("title", "Financial Intelligence Result"))
                        content = str(res.get("content", ""))
                        if not url or not content:
                            continue
                        sanitized = PromptInjectionSanitizer.sanitize(
                            content, source_id=self.provider_code, source_url=url
                        )
                        rel_tier = _classify_domain_reliability(url)
                        items.append(
                            IngestedResearchItem(
                                source_code=self.provider_code,
                                source_name=self.provider_name,
                                publication_title=title[:300],
                                publication_date=now_utc,
                                url=url,
                                raw_content=sanitized.wrapped_evidence_block,
                                relevant_finding=sanitized.clean_text[:1000],
                                document_type="MARKET_NEWS",
                                reliability_classification=rel_tier,
                                epistemic_type="FACT" if rel_tier == "TIER_1_OFFICIAL" else "OPINION",
                                verification_status="VERIFIED",
                            )
                        )
        except Exception as exc:
            logger.warning("TavilySearchProvider error: %s", exc)
        return items


class GoogleCustomSearchProvider(BaseSearchProvider):
    """
    Google Custom Search JSON API integration.
    """

    provider_code = "GOOGLE_SEARCH"
    provider_name = "Google Custom Search Engine"
    reliability_tier = "TIER_3_FINANCIAL_PRESS"
    API_URL = "https://www.googleapis.com/customsearch/v1"

    def search_financial_intelligence(
        self, query: str, max_results: int = 5
    ) -> List[IngestedResearchItem]:
        if not settings.GOOGLE_SEARCH_API_KEY or not settings.GOOGLE_SEARCH_ENGINE_ID:
            return []

        items: List[IngestedResearchItem] = []
        now_utc = datetime.now(timezone.utc)
        try:
            with create_http_client(timeout=settings.DATA_PROVIDER_TIMEOUT_SECONDS) as client:
                resp = client.get(
                    self.API_URL,
                    params={
                        "key": settings.GOOGLE_SEARCH_API_KEY,
                        "cx": settings.GOOGLE_SEARCH_ENGINE_ID,
                        "q": query,
                        "num": min(max_results, 10),
                    },
                )
                if resp.status_code == 200:
                    for res in resp.json().get("items", []):
                        url = str(res.get("link", ""))
                        title = str(res.get("title", ""))
                        snippet = str(res.get("snippet", ""))
                        if not url or not snippet:
                            continue
                        sanitized = PromptInjectionSanitizer.sanitize(
                            snippet, source_id=self.provider_code, source_url=url
                        )
                        rel_tier = _classify_domain_reliability(url)
                        items.append(
                            IngestedResearchItem(
                                source_code=self.provider_code,
                                source_name=self.provider_name,
                                publication_title=title[:300],
                                publication_date=now_utc,
                                url=url,
                                raw_content=sanitized.wrapped_evidence_block,
                                relevant_finding=sanitized.clean_text,
                                document_type="MARKET_NEWS",
                                reliability_classification=rel_tier,
                                epistemic_type="FACT" if rel_tier == "TIER_1_OFFICIAL" else "OPINION",
                                verification_status="VERIFIED",
                            )
                        )
        except Exception as exc:
            logger.warning("GoogleCustomSearchProvider error: %s", exc)
        return items


class PublicFinancialRSSProvider(BaseSearchProvider):
    """
    Zero-credential public RSS/Atom intelligence collector for Nigerian financial press
    (Nairametrics, BusinessDay Nigeria, Proshare) and global macro feeds.
    """

    provider_code = "NIGERIAN_FINANCIAL_PRESS"
    provider_name = "Nigerian Institutional Financial Press RSS"
    reliability_tier = "TIER_3_FINANCIAL_PRESS"

    FEEDS = [
        ("Nairametrics Financial News", "https://nairametrics.com/feed/"),
        ("BusinessDay Nigeria", "https://businessday.ng/feed/"),
    ]

    def search_financial_intelligence(
        self, query: str = "", max_results: int = 6
    ) -> List[IngestedResearchItem]:
        items: List[IngestedResearchItem] = []
        now_utc = datetime.now(timezone.utc)
        q_lower = query.lower().strip()

        with create_http_client(
            timeout=settings.DATA_PROVIDER_TIMEOUT_SECONDS,
            headers={"User-Agent": settings.DATA_PROVIDER_USER_AGENT},
            follow_redirects=True,
        ) as client:
            for feed_name, feed_url in self.FEEDS:
                try:
                    resp = client.get(feed_url)
                    if resp.status_code != 200 or not resp.text:
                        continue
                    root = ET.fromstring(resp.text)
                    for item_el in root.findall(".//item")[:15]:
                        title = (item_el.findtext("title") or "").strip()
                        link = (item_el.findtext("link") or "").strip()
                        desc = (item_el.findtext("description") or "").strip()
                        pub_str = (item_el.findtext("pubDate") or "").strip()
                        if not title or not link:
                            continue
                        if q_lower and (q_lower not in title.lower() and q_lower not in desc.lower()):
                            continue
                        try:
                            pub_dt = parsedate_to_datetime(pub_str).astimezone(timezone.utc)
                        except Exception:
                            pub_dt = now_utc

                        combined = f"{title}. {desc}"
                        sanitized = PromptInjectionSanitizer.sanitize(
                            combined, source_id=self.provider_code, source_url=link
                        )
                        items.append(
                            IngestedResearchItem(
                                source_code=self.provider_code,
                                source_name=feed_name,
                                publication_title=title[:300],
                                publication_date=pub_dt,
                                url=link,
                                raw_content=sanitized.wrapped_evidence_block,
                                relevant_finding=sanitized.clean_text[:800],
                                document_type="MARKET_NEWS",
                                issuer=feed_name,
                                reliability_classification="TIER_3_FINANCIAL_PRESS",
                                epistemic_type="FACT",
                                verification_status="VERIFIED",
                            )
                        )
                        if len(items) >= max_results:
                            return items
                except Exception as exc:
                    logger.info("Public RSS fetch note for %s: %s", feed_name, exc)
        return items
