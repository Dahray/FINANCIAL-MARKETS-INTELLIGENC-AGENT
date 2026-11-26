"""
Unified Data Ingestion, Validation, Deduplication, and Persistence Service (Section 4).
Coordinates all Nigerian, Global, Macroeconomic, Regulatory, and Search providers.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.models.document import DocumentChunk, ResearchDocument
from app.models.macro import MacroIndicator
from app.models.market import MarketTimeseries, YieldCurvePoint
from app.models.source import DataSource, SourceRegister
from app.providers.base import (
    IngestedMacroPoint,
    IngestedMarketPoint,
    IngestedResearchItem,
    IngestedYieldPoint,
)
from app.providers.global_markets.global_providers import (
    AlphaVantageDataProvider,
    FMPDataProvider,
    FREDDataProvider,
)
from app.providers.nigerian.nigerian_providers import (
    CBNDataProvider,
    FMDQDMODataProvider,
    NGXDataProvider,
    NigerianRegulatorsMonitorProvider,
)
from app.providers.quality import DataQualityGate
from app.providers.search.search_providers import (
    GoogleCustomSearchProvider,
    PublicFinancialRSSProvider,
    TavilySearchProvider,
)

logger = get_logger("fmip.services.ingestion")


APPROVED_SOURCES_CATALOG: List[Dict[str, str]] = [
    {
        "code": "CBN_OFFICIAL",
        "name": "Central Bank of Nigeria (CBN)",
        "category": "REGULATOR",
        "country": "NIGERIA",
        "base_url": "https://www.cbn.gov.ng",
        "reliability_tier": "TIER_1_OFFICIAL",
    },
    {
        "code": "NGX_OFFICIAL",
        "name": "Nigerian Exchange Group (NGX)",
        "category": "EXCHANGE",
        "country": "NIGERIA",
        "base_url": "https://ngxgroup.com",
        "reliability_tier": "TIER_1_OFFICIAL",
    },
    {
        "code": "FMDQ_OFFICIAL",
        "name": "FMDQ Securities Exchange",
        "category": "EXCHANGE",
        "country": "NIGERIA",
        "base_url": "https://fmdqgroup.com",
        "reliability_tier": "TIER_1_OFFICIAL",
    },
    {
        "code": "DMO_OFFICIAL",
        "name": "Debt Management Office (DMO Nigeria)",
        "category": "REGULATOR",
        "country": "NIGERIA",
        "base_url": "https://www.dmo.gov.ng",
        "reliability_tier": "TIER_1_OFFICIAL",
    },
    {
        "code": "NBS_OFFICIAL",
        "name": "National Bureau of Statistics (NBS Nigeria)",
        "category": "STATISTICAL_BUREAU",
        "country": "NIGERIA",
        "base_url": "https://nigerianstat.gov.ng",
        "reliability_tier": "TIER_1_OFFICIAL",
    },
    {
        "code": "SEC_NIGERIA",
        "name": "Securities and Exchange Commission (SEC Nigeria)",
        "category": "REGULATOR",
        "country": "NIGERIA",
        "base_url": "https://sec.gov.ng",
        "reliability_tier": "TIER_1_OFFICIAL",
    },
    {
        "code": "PENCOM",
        "name": "National Pension Commission (PenCom)",
        "category": "REGULATOR",
        "country": "NIGERIA",
        "base_url": "https://www.pencom.gov.ng",
        "reliability_tier": "TIER_1_OFFICIAL",
    },
    {
        "code": "NAICOM",
        "name": "National Insurance Commission (NAICOM)",
        "category": "REGULATOR",
        "country": "NIGERIA",
        "base_url": "https://naicom.gov.ng",
        "reliability_tier": "TIER_1_OFFICIAL",
    },
    {
        "code": "FMP_API",
        "name": "Financial Modeling Prep (FMP)",
        "category": "MARKET_DATA_API",
        "country": "GLOBAL",
        "base_url": "https://financialmodelingprep.com",
        "reliability_tier": "TIER_2_INSTITUTIONAL",
    },
    {
        "code": "ALPHA_VANTAGE",
        "name": "Alpha Vantage Financial API",
        "category": "MARKET_DATA_API",
        "country": "GLOBAL",
        "base_url": "https://www.alphavantage.co",
        "reliability_tier": "TIER_2_INSTITUTIONAL",
    },
    {
        "code": "FRED_API",
        "name": "Federal Reserve Economic Data (FRED - St. Louis Fed)",
        "category": "STATISTICAL_BUREAU",
        "country": "GLOBAL",
        "base_url": "https://fred.stlouisfed.org",
        "reliability_tier": "TIER_1_OFFICIAL",
    },
    {
        "code": "TAVILY_SEARCH",
        "name": "Tavily AI Research Search API",
        "category": "FINANCIAL_PRESS",
        "country": "GLOBAL",
        "base_url": "https://tavily.com",
        "reliability_tier": "TIER_3_FINANCIAL_PRESS",
    },
    {
        "code": "GOOGLE_SEARCH",
        "name": "Google Custom Search Engine",
        "category": "FINANCIAL_PRESS",
        "country": "GLOBAL",
        "base_url": "https://programmablesearchengine.google.com",
        "reliability_tier": "TIER_3_FINANCIAL_PRESS",
    },
    {
        "code": "NIGERIAN_FINANCIAL_PRESS",
        "name": "Nigerian Institutional Financial Press",
        "category": "FINANCIAL_PRESS",
        "country": "NIGERIA",
        "base_url": "https://nairametrics.com",
        "reliability_tier": "TIER_3_FINANCIAL_PRESS",
    },
]


def compute_text_embedding_768(text_content: str) -> List[float]:
    """
    Compute a 768-dimensional semantic embedding vector.
    Uses Google Gemini `gemini-embedding-001` REST endpoint (`outputDimensionality=768`)
    whenever a valid Gemini API key (`AIza...` or `AQ....`) is configured;
    falls back to a deterministic L2-normalized 768-dim token feature hash vector
    so pgvector similarity search always works.
    """
    key = (settings.GEMINI_API_KEY or "").strip()
    if len(key) > 10 and not any(tok in key.lower() for tok in ("your-", "placeholder", "changeme")):
        try:
            from app.core.ssl_helper import create_http_client

            model_id = settings.GEMINI_EMBEDDING_MODEL.replace("models/", "").strip()
            if model_id in ("", "text-embedding-004", "embedding-001"):
                model_id = "gemini-embedding-001"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:embedContent"
            with create_http_client(timeout=15) as client:
                resp = client.post(
                    url,
                    params={"key": key},
                    json={
                        "model": f"models/{model_id}",
                        "content": {"parts": [{"text": text_content[:6000]}]},
                        "outputDimensionality": 768,
                    },
                )
                if resp.status_code == 200:
                    vals = resp.json().get("embedding", {}).get("values", [])
                    if len(vals) == 768:
                        return [float(x) for x in vals]
        except Exception as exc:
            logger.info("Gemini embedding fallback activated: %s", exc)

    # Deterministic 768-dim semantic token projection
    vec = np.zeros(768, dtype=float)
    tokens = [t.strip(".,;:!?()[]\"'").lower() for t in text_content.split() if len(t) > 2]
    for tok in tokens:
        digest = hashlib.sha256(tok.encode("utf-8")).digest()
        idx1 = int.from_bytes(digest[0:2], "big") % 768
        idx2 = int.from_bytes(digest[2:4], "big") % 768
        sign = 1.0 if (digest[4] % 2 == 0) else -1.0
        vec[idx1] += sign
        vec[idx2] += sign * 0.5
    norm = float(np.linalg.norm(vec))
    if norm > 1e-9:
        vec = vec / norm
    return [round(float(x), 6) for x in vec.tolist()]


class IngestionService:
    """
    Orchestrates data retrieval from approved providers, enforces data quality checks,
    detects duplicates, maintains historical records, and populates the Source Register.
    """

    @staticmethod
    def ensure_default_data_sources(db: Session) -> Dict[str, DataSource]:
        """Ensure all approved data sources exist in `data_sources` and return a map by `code`."""
        existing = {
            ds.code: ds for ds in db.execute(select(DataSource)).scalars().all()
        }
        for spec in APPROVED_SOURCES_CATALOG:
            if spec["code"] not in existing:
                ds = DataSource(
                    code=spec["code"],
                    name=spec["name"],
                    category=spec["category"],
                    country=spec["country"],
                    base_url=spec["base_url"],
                    reliability_tier=spec["reliability_tier"],
                    is_active=True,
                )
                db.add(ds)
                db.flush()
                existing[ds.code] = ds
        db.commit()
        return existing

    @classmethod
    def ingest_market_points(
        cls,
        db: Session,
        points: Sequence[IngestedMarketPoint],
    ) -> Dict[str, int]:
        """Validate, deduplicate, and persist market time-series observations."""
        sources_map = cls.ensure_default_data_sources(db)
        added = 0
        skipped_duplicates = 0
        flagged = 0

        for pt in points:
            ds = sources_map.get(pt.source_code) or sources_map["NGX_OFFICIAL"]
            # Load trailing LIVE historical values for outlier check (never compare live Tier-1 against stale archival baselines)
            hist_rows = (
                db.execute(
                    select(MarketTimeseries.value)
                    .where(
                        MarketTimeseries.symbol == pt.symbol,
                        MarketTimeseries.is_archival_baseline == False,  # noqa: E712
                    )
                    .order_by(MarketTimeseries.publication_date.desc())
                    .limit(30)
                )
                .scalars()
                .all()
            )
            hist_vals = [float(v) for v in hist_rows if v is not None]

            validated_pt, dedup_hash = DataQualityGate.validate_market_point(
                point=pt,
                historical_values=hist_vals,
                source_reliability_tier=ds.reliability_tier,
            )
            if validated_pt.source_tier == "TIER_1_OFFICIAL" and not validated_pt.is_archival_baseline:
                validated_pt.verification_status = "VERIFIED"


            exists = db.execute(
                select(MarketTimeseries.id).where(MarketTimeseries.dedup_hash == dedup_hash)
            ).scalar_one_or_none()
            if exists:
                skipped_duplicates += 1
                continue

            if validated_pt.verification_status != "VERIFIED":
                flagged += 1

            record = MarketTimeseries(
                symbol=validated_pt.symbol,
                indicator_name=validated_pt.indicator_name,
                asset_class=validated_pt.asset_class,
                market_region=validated_pt.market_region,
                value=validated_pt.value,
                open_value=validated_pt.open_value,
                high_value=validated_pt.high_value,
                low_value=validated_pt.low_value,
                close_value=validated_pt.close_value or validated_pt.value,
                volume=validated_pt.volume,
                market_cap=validated_pt.market_cap,
                currency_or_unit=validated_pt.currency_or_unit,
                reporting_period=validated_pt.reporting_period,
                publication_date=validated_pt.publication_date,
                effective_date=validated_pt.effective_date or validated_pt.publication_date,
                retrieval_date=validated_pt.retrieval_date,
                source_id=ds.id,
                source_url=validated_pt.source_url or ds.base_url,
                source_tier=(
                    "ARCHIVAL_BASELINE"
                    if validated_pt.is_archival_baseline
                    else (validated_pt.source_tier or ds.reliability_tier)
                ),
                confidence_score=(
                    45.0 if validated_pt.is_archival_baseline else validated_pt.confidence_score
                ),
                is_authoritative=not validated_pt.is_archival_baseline,
                is_archival_baseline=validated_pt.is_archival_baseline,
                data_frequency=validated_pt.data_frequency,
                verification_status=validated_pt.verification_status,
                quality_flags=validated_pt.quality_flags,
                dedup_hash=dedup_hash,
            )
            db.add(record)
            ds.last_successful_fetch_at = datetime.now(timezone.utc)
            added += 1

        db.commit()
        return {
            "market_points_added": added,
            "duplicates_skipped": skipped_duplicates,
            "flagged_count": flagged,
        }

    @classmethod
    def ingest_yield_points(
        cls,
        db: Session,
        points: Sequence[IngestedYieldPoint],
    ) -> Dict[str, int]:
        """Validate, deduplicate, and persist fixed-income yield curve points."""
        sources_map = cls.ensure_default_data_sources(db)
        added = 0
        skipped_duplicates = 0
        flagged = 0

        for pt in points:
            ds = sources_map.get(pt.source_code) or sources_map["FMDQ_OFFICIAL"]
            validated_pt, dedup_hash = DataQualityGate.validate_yield_point(
                point=pt,
                source_reliability_tier=ds.reliability_tier,
            )

            exists = db.execute(
                select(YieldCurvePoint.id).where(YieldCurvePoint.dedup_hash == dedup_hash)
            ).scalar_one_or_none()
            if exists:
                skipped_duplicates += 1
                continue

            if validated_pt.verification_status != "VERIFIED":
                flagged += 1

            record = YieldCurvePoint(
                curve_name=validated_pt.curve_name,
                instrument_type=validated_pt.instrument_type,
                tenor_label=validated_pt.tenor_label,
                tenor_days=validated_pt.tenor_days,
                tenor_years=validated_pt.tenor_years,
                indicator_name=validated_pt.indicator_name,
                value=validated_pt.value,
                coupon_rate=validated_pt.coupon_rate,
                bid_to_cover=validated_pt.bid_to_cover,
                currency_or_unit=validated_pt.currency_or_unit,
                reporting_period=validated_pt.reporting_period,
                publication_date=validated_pt.publication_date,
                effective_date=validated_pt.effective_date or validated_pt.publication_date,
                retrieval_date=validated_pt.retrieval_date,
                source_id=ds.id,
                source_url=validated_pt.source_url or ds.base_url,
                source_tier=(
                    "ARCHIVAL_BASELINE"
                    if validated_pt.is_archival_baseline
                    else (validated_pt.source_tier or ds.reliability_tier)
                ),
                confidence_score=(
                    45.0 if validated_pt.is_archival_baseline else validated_pt.confidence_score
                ),
                is_authoritative=not validated_pt.is_archival_baseline,
                is_archival_baseline=validated_pt.is_archival_baseline,
                data_frequency=validated_pt.data_frequency,
                verification_status=validated_pt.verification_status,
                dedup_hash=dedup_hash,
            )
            db.add(record)
            ds.last_successful_fetch_at = datetime.now(timezone.utc)
            added += 1

        db.commit()
        return {
            "yield_points_added": added,
            "duplicates_skipped": skipped_duplicates,
            "flagged_count": flagged,
        }

    @classmethod
    def ingest_macro_points(
        cls,
        db: Session,
        points: Sequence[IngestedMacroPoint],
    ) -> Dict[str, int]:
        """Validate, deduplicate, and persist macroeconomic indicator points."""
        sources_map = cls.ensure_default_data_sources(db)
        added = 0
        skipped_duplicates = 0
        flagged = 0

        for pt in points:
            ds = sources_map.get(pt.source_code) or sources_map["CBN_OFFICIAL"]
            validated_pt, dedup_hash = DataQualityGate.validate_macro_point(
                point=pt,
                source_reliability_tier=ds.reliability_tier,
            )

            exists = db.execute(
                select(MacroIndicator.id).where(MacroIndicator.dedup_hash == dedup_hash)
            ).scalar_one_or_none()
            if exists:
                skipped_duplicates += 1
                continue

            if validated_pt.verification_status != "VERIFIED":
                flagged += 1

            record = MacroIndicator(
                indicator_code=validated_pt.indicator_code,
                indicator_name=validated_pt.indicator_name,
                country=validated_pt.country,
                category=validated_pt.category,
                value=validated_pt.value,
                previous_value=validated_pt.previous_value,
                consensus_estimate=validated_pt.consensus_estimate,
                currency_or_unit=validated_pt.currency_or_unit,
                reporting_period=validated_pt.reporting_period,
                publication_date=validated_pt.publication_date,
                effective_date=validated_pt.effective_date or validated_pt.publication_date,
                retrieval_date=validated_pt.retrieval_date,
                source_id=ds.id,
                source_url=validated_pt.source_url or ds.base_url,
                source_tier=(
                    "ARCHIVAL_BASELINE"
                    if validated_pt.is_archival_baseline
                    else (validated_pt.source_tier or ds.reliability_tier)
                ),
                confidence_score=(
                    45.0 if validated_pt.is_archival_baseline else validated_pt.confidence_score
                ),
                is_authoritative=not validated_pt.is_archival_baseline,
                is_archival_baseline=validated_pt.is_archival_baseline,
                data_frequency=validated_pt.data_frequency,
                verification_status=validated_pt.verification_status,
                dedup_hash=dedup_hash,
            )
            db.add(record)
            ds.last_successful_fetch_at = datetime.now(timezone.utc)
            added += 1

        db.commit()
        return {
            "macro_points_added": added,
            "duplicates_skipped": skipped_duplicates,
            "flagged_count": flagged,
        }


    @classmethod
    def ingest_research_items(
        cls,
        db: Session,
        items: Sequence[IngestedResearchItem],
    ) -> Dict[str, Any]:
        """
        Deduplicate and persist research items into `source_register`,
        `research_documents`, and `document_chunks` (with 768-dim vector embeddings).
        """
        sources_map = cls.ensure_default_data_sources(db)
        added_ids: List[str] = []
        skipped_duplicates = 0

        for item in items:
            ds = sources_map.get(item.source_code) or sources_map["NIGERIAN_FINANCIAL_PRESS"]
            pub_utc = (
                item.publication_date
                if item.publication_date.tzinfo is not None
                else item.publication_date.replace(tzinfo=timezone.utc)
            )
            canonical_hash = DataQualityGate.compute_document_canonical_hash(
                item.url, item.publication_title, pub_utc
            )

            existing_sr = db.execute(
                select(SourceRegister).where(SourceRegister.canonical_hash == canonical_hash)
            ).scalar_one_or_none()
            if existing_sr:
                skipped_duplicates += 1
                added_ids.append(existing_sr.id)
                continue

            sr = SourceRegister(
                source_id=ds.id,
                source_name=item.source_name,
                publication_title=item.publication_title,
                publication_date=pub_utc,
                retrieval_date=item.retrieval_date,
                url=item.url,
                canonical_hash=canonical_hash,
                relevant_finding=item.relevant_finding,
                reliability_classification=item.reliability_classification,
                epistemic_type=item.epistemic_type,
                verification_status=item.verification_status,
                metadata_json={"document_type": item.document_type, "issuer": item.issuer},
            )
            db.add(sr)
            db.flush()

            content_hash = hashlib.sha256(
                f"{canonical_hash}|{item.raw_content[:2000]}".encode("utf-8")
            ).hexdigest()

            doc = ResearchDocument(
                source_register_id=sr.id,
                document_type=item.document_type,
                title=item.publication_title,
                issuer=item.issuer or item.source_name,
                published_at=pub_utc,
                retrieved_at=item.retrieval_date,
                raw_text=item.raw_content,
                structured_extract=item.structured_extract,
                content_hash=content_hash,
            )
            db.add(doc)
            db.flush()

            # Chunk text & generate 768-dim embedding for pgvector semantic retrieval
            chunk_body = f"{item.publication_title}\n{item.relevant_finding}"
            embedding_vec = compute_text_embedding_768(chunk_body)
            chunk = DocumentChunk(
                document_id=doc.id,
                chunk_index=0,
                chunk_text=chunk_body,
                embedding=embedding_vec,
                metadata_json={
                    "source_register_id": sr.id,
                    "source_name": item.source_name,
                    "publication_date": pub_utc.isoformat(),
                    "document_type": item.document_type,
                    "reliability_tier": item.reliability_classification,
                    "url": item.url,
                },
            )
            db.add(chunk)
            added_ids.append(sr.id)

        db.commit()
        return {
            "research_items_added": len(added_ids) - skipped_duplicates,
            "duplicates_skipped": skipped_duplicates,
            "source_register_ids": added_ids,
        }

    _last_live_sweep_ts: float = 0.0
    _last_live_sweep_result: Optional[Dict[str, Any]] = None
    _runtime_quota_profile: Optional[Dict[str, Any]] = None

    QUOTA_TIER_PRESETS: Dict[str, Dict[str, Any]] = {
        "FREE_STARTER": {
            "quota_tier": "FREE_STARTER",
            "label": "Free-Tier Starter Protection (Default)",
            "description": "Protects free API limits (Alpha Vantage 25/day, FMP 250/day, Tavily 1,000/month) with a 15-min cooldown and targeted batch sizes.",
            "cooldown_seconds": 900,
            "search_queries_limit": 2,
            "max_search_results_per_query": 3,
            "rss_max_results": 6,
            "fred_history_limit": 15,
            "fmp_symbols_count": 6,
            "alpha_vantage_pairs_count": 1,
        },
        "STANDARD_PAID": {
            "quota_tier": "STANDARD_PAID",
            "label": "Standard Institutional Research (Expanded Quota)",
            "description": "Balanced expansion for upgraded API plans: 3-min cooldown, 5 sector search queries (8 articles each), 14 FMP symbols, 3 FX pairs, and 60 FRED history points.",
            "cooldown_seconds": 180,
            "search_queries_limit": 5,
            "max_search_results_per_query": 8,
            "rss_max_results": 15,
            "fred_history_limit": 60,
            "fmp_symbols_count": 14,
            "alpha_vantage_pairs_count": 3,
        },
        "ENTERPRISE_UNLIMITED": {
            "quota_tier": "ENTERPRISE_UNLIMITED",
            "label": "Enterprise High-Frequency Coverage (Unrestricted)",
            "description": "Maximum institutional depth: zero cooldown, 8 deep Nigerian/African search queries (15 articles each), 20 FMP global/African symbols, 5 FX pairs, and 250 FRED observations.",
            "cooldown_seconds": 0,
            "search_queries_limit": 8,
            "max_search_results_per_query": 15,
            "rss_max_results": 30,
            "fred_history_limit": 250,
            "fmp_symbols_count": 20,
            "alpha_vantage_pairs_count": 5,
        },
    }

    INSTITUTIONAL_SEARCH_QUERY_POOL: List[str] = [
        "Nigerian Exchange NGX equities fixed income FMDQ Treasury bills CBN monetary policy",
        "Nigeria asset management commercial banks fintech SEC PenCom regulatory developments",
        "Nigerian sovereign Eurobonds DMO bond auction stop rates NAFEM FX turnover liquidity",
        "Nigeria corporate commercial paper issuances FMDQ private credit infrastructure funds",
        "Central Bank of Nigeria MPC OMO auction CRR liquidity ratio banking recapitalization",
        "Nigerian pension fund administrators PFA asset allocation PenCom investment guidelines",
        "Stanbic IBTC Chapel Hill Denham CardinalStone Meristem United Capital asset management Nigeria",
        "West Africa sovereign fixed income Ghana Kenya South Africa Eurobond yields commodity prices",
    ]

    @classmethod
    def get_quota_profile(cls) -> Dict[str, Any]:
        """Return active API quota and ingestion depth profile."""
        if cls._runtime_quota_profile is None:
            tier = (settings.INGESTION_QUOTA_TIER or "FREE_STARTER").upper()
            preset = dict(
                cls.QUOTA_TIER_PRESETS.get(tier, cls.QUOTA_TIER_PRESETS["FREE_STARTER"])
            )
            preset["cooldown_seconds"] = settings.INGESTION_COOLDOWN_SECONDS
            preset["max_search_results_per_query"] = (
                settings.INGESTION_MAX_SEARCH_RESULTS_PER_QUERY
            )
            preset["search_queries_limit"] = settings.INGESTION_SEARCH_QUERIES_LIMIT
            preset["rss_max_results"] = settings.INGESTION_RSS_MAX_RESULTS
            preset["fred_history_limit"] = settings.INGESTION_FRED_HISTORY_LIMIT
            cls._runtime_quota_profile = preset
        return {
            **cls._runtime_quota_profile,
            "available_tiers": list(cls.QUOTA_TIER_PRESETS.values()),
        }

    @classmethod
    def update_quota_profile(
        cls,
        quota_tier: str,
        cooldown_seconds: Optional[int] = None,
        search_queries_limit: Optional[int] = None,
        max_search_results_per_query: Optional[int] = None,
        rss_max_results: Optional[int] = None,
        fred_history_limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Switch API quota tier (`FREE_STARTER`, `STANDARD_PAID`, `ENTERPRISE_UNLIMITED`)
        or customize individual ingestion depth parameters at runtime.
        """
        tier_key = quota_tier.upper().strip()
        if tier_key not in cls.QUOTA_TIER_PRESETS:
            tier_key = "FREE_STARTER"

        profile = dict(cls.QUOTA_TIER_PRESETS[tier_key])
        if cooldown_seconds is not None:
            profile["cooldown_seconds"] = max(0, int(cooldown_seconds))
        if search_queries_limit is not None:
            profile["search_queries_limit"] = max(
                1, min(len(cls.INSTITUTIONAL_SEARCH_QUERY_POOL), int(search_queries_limit))
            )
        if max_search_results_per_query is not None:
            profile["max_search_results_per_query"] = max(
                1, min(25, int(max_search_results_per_query))
            )
        if rss_max_results is not None:
            profile["rss_max_results"] = max(1, min(50, int(rss_max_results)))
        if fred_history_limit is not None:
            profile["fred_history_limit"] = max(5, min(500, int(fred_history_limit)))

        cls._runtime_quota_profile = profile
        return cls.get_quota_profile()

    @classmethod
    def run_live_ingestion_cycle(
        cls,
        db: Session,
        search_queries: Optional[List[str]] = None,
        force: bool = False,
        cooldown_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Execute a full ingestion sweep across Nigerian, Global, Macro, Regulatory,
        and Search providers, persisting all validated records to the database.
        Dynamically scales depth and cooldown according to the active API Quota Profile.
        """
        import time

        profile = cls.get_quota_profile()
        effective_cooldown = (
            cooldown_seconds
            if cooldown_seconds is not None
            else int(profile.get("cooldown_seconds", 900))
        )
        active_tier = str(profile.get("quota_tier", "FREE_STARTER"))
        max_search_res = int(profile.get("max_search_results_per_query", 3))
        queries_limit = int(profile.get("search_queries_limit", 2))
        rss_limit = int(profile.get("rss_max_results", 6))
        fred_limit = int(profile.get("fred_history_limit", 15))

        now_ts = time.time()
        if (
            not force
            and effective_cooldown > 0
            and cls._last_live_sweep_result is not None
            and (now_ts - cls._last_live_sweep_ts) < effective_cooldown
        ):
            cached = dict(cls._last_live_sweep_result)
            cached["quota_guard_cached"] = True
            cached["active_quota_tier"] = active_tier
            cached["cooldown_seconds"] = effective_cooldown
            cached["seconds_since_last_sweep"] = round(now_ts - cls._last_live_sweep_ts, 1)
            return cached

        cls.ensure_default_data_sources(db)

        cbn = CBNDataProvider()
        ngx = NGXDataProvider()
        fmdq = FMDQDMODataProvider()
        reg_monitor = NigerianRegulatorsMonitorProvider()
        fmp = FMPDataProvider()
        av = AlphaVantageDataProvider()
        fred = FREDDataProvider()
        tavily = TavilySearchProvider()
        gsearch = GoogleCustomSearchProvider()
        rss = PublicFinancialRSSProvider()

        market_pts: List[IngestedMarketPoint] = []
        market_pts.extend(cbn.fetch_market_timeseries())
        market_pts.extend(ngx.fetch_market_timeseries())
        market_pts.extend(fmdq.fetch_market_timeseries())
        market_pts.extend(fmp.fetch_market_timeseries(symbol_tier=active_tier))
        market_pts.extend(av.fetch_market_timeseries(quota_tier=active_tier))
        market_pts.extend(fred.fetch_market_timeseries(history_limit=fred_limit))

        yield_pts: List[IngestedYieldPoint] = []
        yield_pts.extend(cbn.fetch_yield_curves())
        yield_pts.extend(fred.fetch_yield_curves(history_limit=fred_limit))

        macro_pts: List[IngestedMacroPoint] = []
        macro_pts.extend(cbn.fetch_macro_indicators())
        macro_pts.extend(fred.fetch_macro_indicators(history_limit=fred_limit))

        research_items: List[IngestedResearchItem] = []
        research_items.extend(cbn.fetch_regulatory_publications())
        research_items.extend(reg_monitor.fetch_regulatory_publications())
        research_items.extend(rss.search_financial_intelligence(max_results=rss_limit))

        queries = search_queries or cls.INSTITUTIONAL_SEARCH_QUERY_POOL[:queries_limit]
        for q in queries:
            research_items.extend(
                tavily.search_financial_intelligence(q, max_results=max_search_res)
            )
            research_items.extend(
                gsearch.search_financial_intelligence(q, max_results=max_search_res)
            )

        m_stats = cls.ingest_market_points(db, market_pts)
        y_stats = cls.ingest_yield_points(db, yield_pts)
        mac_stats = cls.ingest_macro_points(db, macro_pts)
        doc_stats = cls.ingest_research_items(db, research_items)

        # Stage 2 Verification Engine: Reclassify legacy seed baselines & resolve cross-source discrepancies
        from app.services.verification_service import FinancialDataVerificationEngine

        hygiene_stats = FinancialDataVerificationEngine.mark_legacy_seed_records_as_archival(db)
        discrepancy_stats = FinancialDataVerificationEngine.run_discrepancy_detection_and_resolution(db)

        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "quota_guard_cached": False,
            "active_quota_tier": active_tier,
            "cooldown_seconds": effective_cooldown,
            "queries_executed": len(queries),
            "max_search_results_per_query": max_search_res,
            "fred_history_limit": fred_limit,
            "market_ingestion": m_stats,
            "yield_curve_ingestion": y_stats,
            "macro_ingestion": mac_stats,
            "research_and_regulatory_ingestion": doc_stats,
            "verification_hygiene": hygiene_stats,
            "discrepancy_audit": discrepancy_stats,
        }
        cls._last_live_sweep_ts = now_ts
        cls._last_live_sweep_result = result
        return result


