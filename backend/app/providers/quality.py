"""
Data Quality Gate, Deduplication Hashing, Outlier Detection, and Provenance Verification
(Section 4 Mandate: 'Never silently substitute missing data with estimated figures.
Where information cannot be verified, flag it.').
"""

from __future__ import annotations

import hashlib
import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from app.providers.base import (
    IngestedMacroPoint,
    IngestedMarketPoint,
    IngestedResearchItem,
    IngestedYieldPoint,
)


class DataQualityGate:
    """
    Validates ingested financial data points and research items before persistence or analysis.
    """

    @staticmethod
    def compute_datapoint_dedup_hash(
        indicator_or_symbol: str,
        reporting_period: str,
        publication_date: datetime,
        source_code: str,
    ) -> str:
        """Compute deterministic SHA-256 deduplication hash for a financial data point."""
        pub_iso = publication_date.astimezone(timezone.utc).strftime("%Y-%m-%d")
        payload = f"{indicator_or_symbol.strip().upper()}|{reporting_period.strip()}|{pub_iso}|{source_code.strip().upper()}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def compute_document_canonical_hash(url: str, title: str, publication_date: datetime) -> str:
        """Compute deterministic SHA-256 canonical hash for a source register or document entry."""
        pub_iso = publication_date.astimezone(timezone.utc).strftime("%Y-%m-%d")
        payload = f"{url.strip().lower()}|{title.strip().lower()}|{pub_iso}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @classmethod
    def validate_market_point(
        cls,
        point: IngestedMarketPoint,
        historical_values: Optional[Sequence[float]] = None,
        source_reliability_tier: str = "TIER_1_OFFICIAL",
    ) -> Tuple[IngestedMarketPoint, str]:
        """
        Validate a market data point, assign `verification_status` and `quality_flags`,
        and return `(validated_point, dedup_hash)`.
        Raises ValueError if mandatory data is missing or invalid.
        """
        if point.value is None or math.isnan(point.value) or math.isinf(point.value):
            raise ValueError(
                f"DataQualityGate rejected {point.symbol}: missing or non-finite value."
            )

        flags: Dict[str, Any] = dict(point.quality_flags or {})
        status = point.verification_status

        # 1. Check for negative prices on equities, FX, or commodities
        if point.asset_class in ("EQUITY", "INDEX", "FX", "COMMODITY") and point.value <= 0:
            flags["non_positive_price"] = True
            status = "FLAGGED_UNVERIFIED"

        # 2. Check OHLC consistency if provided
        if (
            point.high_value is not None
            and point.low_value is not None
            and point.high_value < point.low_value
        ):
            flags["ohlc_high_below_low"] = True
            status = "FLAGGED_UNVERIFIED"

        # 3. Check future publication timestamp (> 24h ahead of UTC now)
        now_utc = datetime.now(timezone.utc)
        pub_utc = (
            point.publication_date
            if point.publication_date.tzinfo is not None
            else point.publication_date.replace(tzinfo=timezone.utc)
        )
        if pub_utc > now_utc + timedelta(hours=24):
            flags["future_publication_date"] = pub_utc.isoformat()
            status = "FLAGGED_UNVERIFIED"

        # 4. Outlier z-score check against historical series (|z| > 4.0)
        if historical_values and len(historical_values) >= 10:
            arr = np.asarray(historical_values, dtype=float)
            mean_val = float(np.mean(arr))
            std_val = float(np.std(arr, ddof=1))
            if std_val > 1e-9:
                z_score = abs(point.value - mean_val) / std_val
                if z_score > 4.0:
                    flags["outlier_z_score"] = round(z_score, 2)
                    if status == "VERIFIED":
                        status = "PENDING_CROSS_CHECK"

        # 5. Source reliability check
        if source_reliability_tier in ("TIER_4_SECONDARY", "UNVERIFIED"):
            flags["unverified_secondary_source"] = source_reliability_tier
            status = "FLAGGED_UNVERIFIED"

        point.publication_date = pub_utc
        point.verification_status = status
        point.quality_flags = flags
        dedup_hash = cls.compute_datapoint_dedup_hash(
            f"{point.symbol}:{point.indicator_name}",
            point.reporting_period,
            pub_utc,
            point.source_code,
        )
        return point, dedup_hash

    @classmethod
    def validate_yield_point(
        cls,
        point: IngestedYieldPoint,
        source_reliability_tier: str = "TIER_1_OFFICIAL",
    ) -> Tuple[IngestedYieldPoint, str]:
        """Validate a yield curve data point and compute its deduplication hash."""
        if point.value is None or math.isnan(point.value) or math.isinf(point.value):
            raise ValueError(f"Rejected yield point {point.indicator_name}: missing value.")

        pub_utc = (
            point.publication_date
            if point.publication_date.tzinfo is not None
            else point.publication_date.replace(tzinfo=timezone.utc)
        )
        point.publication_date = pub_utc

        if point.value < -5.0 or point.value > 100.0:
            point.verification_status = "FLAGGED_UNVERIFIED"
        elif source_reliability_tier in ("TIER_4_SECONDARY", "UNVERIFIED"):
            point.verification_status = "FLAGGED_UNVERIFIED"

        dedup_hash = cls.compute_datapoint_dedup_hash(
            f"{point.curve_name}:{point.tenor_label}",
            point.reporting_period,
            pub_utc,
            point.source_code,
        )
        return point, dedup_hash

    @classmethod
    def validate_macro_point(
        cls,
        point: IngestedMacroPoint,
        source_reliability_tier: str = "TIER_1_OFFICIAL",
    ) -> Tuple[IngestedMacroPoint, str]:
        """Validate a macroeconomic indicator observation and compute its deduplication hash."""
        if point.value is None or math.isnan(point.value) or math.isinf(point.value):
            raise ValueError(f"Rejected macro indicator {point.indicator_code}: missing value.")

        pub_utc = (
            point.publication_date
            if point.publication_date.tzinfo is not None
            else point.publication_date.replace(tzinfo=timezone.utc)
        )
        point.publication_date = pub_utc

        if source_reliability_tier in ("TIER_4_SECONDARY", "UNVERIFIED"):
            point.verification_status = "FLAGGED_UNVERIFIED"

        dedup_hash = cls.compute_datapoint_dedup_hash(
            f"{point.country}:{point.indicator_code}",
            point.reporting_period,
            pub_utc,
            point.source_code,
        )
        return point, dedup_hash
