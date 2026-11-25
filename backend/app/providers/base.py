"""
Provider Abstraction Interfaces & Validated Ingestion DTOs (Section 2 & Section 4).
Allows financial data providers to be swapped or added without modifying agent or quant logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class IngestedMarketPoint(BaseModel):
    """Validated DTO for a single financial market time-series observation (Section 4 contract)."""

    symbol: str = Field(..., min_length=1, max_length=64)
    indicator_name: str = Field(..., min_length=1, max_length=255)
    asset_class: str = Field(..., description="EQUITY | INDEX | FX | FIXED_INCOME | MONEY_MARKET | COMMODITY")
    market_region: str = Field(default="NIGERIA", description="NIGERIA | AFRICA | GLOBAL")
    value: float
    open_value: Optional[float] = None
    high_value: Optional[float] = None
    low_value: Optional[float] = None
    close_value: Optional[float] = None
    volume: Optional[float] = None
    market_cap: Optional[float] = None

    # Mandatory Section 4 Provenance Fields
    currency_or_unit: str = Field(..., min_length=1, max_length=64)
    reporting_period: str = Field(..., min_length=1, max_length=64)
    publication_date: datetime
    retrieval_date: datetime = Field(default_factory=utc_now)
    source_code: str = Field(..., min_length=1, max_length=64)
    source_url: str = Field(default="")
    data_frequency: str = Field(default="DAILY")
    verification_status: str = Field(default="VERIFIED")
    quality_flags: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("value")
    @classmethod
    def check_finite_value(cls, v: float) -> float:
        import math

        if v is None or math.isnan(v) or math.isinf(v):
            raise ValueError("Missing, NaN, or infinite financial values are prohibited by Section 4.")
        return float(v)


class IngestedYieldPoint(BaseModel):
    """Validated DTO for a sovereign or corporate yield curve observation."""

    curve_name: str = Field(..., min_length=1, max_length=64)
    instrument_type: str = Field(..., description="NTB | OMO_BILL | FGN_BOND | US_TREASURY")
    tenor_label: str = Field(..., min_length=1, max_length=32)
    tenor_days: int = Field(..., gt=0)
    tenor_years: float = Field(..., gt=0)
    indicator_name: str = Field(..., min_length=1, max_length=255)
    value: float
    coupon_rate: Optional[float] = None
    bid_to_cover: Optional[float] = None
    currency_or_unit: str = Field(default="PERCENT")
    reporting_period: str = Field(..., min_length=1, max_length=64)
    publication_date: datetime
    retrieval_date: datetime = Field(default_factory=utc_now)
    source_code: str = Field(..., min_length=1, max_length=64)
    source_url: str = Field(default="")
    data_frequency: str = Field(default="DAILY")
    verification_status: str = Field(default="VERIFIED")

    @field_validator("value")
    @classmethod
    def check_finite_yield(cls, v: float) -> float:
        import math

        if v is None or math.isnan(v) or math.isinf(v):
            raise ValueError("Missing or NaN yield values are prohibited.")
        return float(v)


class IngestedMacroPoint(BaseModel):
    """Validated DTO for a macroeconomic indicator observation."""

    indicator_code: str = Field(..., min_length=1, max_length=64)
    indicator_name: str = Field(..., min_length=1, max_length=255)
    country: str = Field(default="NIGERIA")
    category: str = Field(..., min_length=1, max_length=64)
    value: float
    previous_value: Optional[float] = None
    consensus_estimate: Optional[float] = None
    currency_or_unit: str = Field(..., min_length=1, max_length=64)
    reporting_period: str = Field(..., min_length=1, max_length=64)
    publication_date: datetime
    retrieval_date: datetime = Field(default_factory=utc_now)
    source_code: str = Field(..., min_length=1, max_length=64)
    source_url: str = Field(default="")
    data_frequency: str = Field(default="MONTHLY")
    verification_status: str = Field(default="VERIFIED")

    @field_validator("value")
    @classmethod
    def check_finite_macro(cls, v: float) -> float:
        import math

        if v is None or math.isnan(v) or math.isinf(v):
            raise ValueError("Missing or NaN macroeconomic values are prohibited.")
        return float(v)


class IngestedResearchItem(BaseModel):
    """Validated DTO for financial news, regulatory circulars, or extracted annual report documents."""

    source_code: str
    source_name: str
    publication_title: str
    publication_date: datetime
    retrieval_date: datetime = Field(default_factory=utc_now)
    url: str
    raw_content: str
    relevant_finding: str
    document_type: str = Field(
        default="MARKET_NEWS",
        description="REGULATORY_CIRCULAR | ANNUAL_REPORT | FINANCIAL_STATEMENT | MARKET_NEWS | MACRO_BULLETIN",
    )
    issuer: Optional[str] = None
    reference_number: Optional[str] = None
    reliability_classification: str = Field(default="TIER_1_OFFICIAL")
    epistemic_type: str = Field(default="FACT")
    verification_status: str = Field(default="VERIFIED")
    structured_extract: Dict[str, Any] = Field(default_factory=dict)


# ------------------------------------------------------------------------------
# Abstract Provider Interfaces
# ------------------------------------------------------------------------------
class BaseMarketDataProvider(ABC):
    """Abstract interface for financial market data providers (NGX, FMDQ, FMP, Alpha Vantage)."""

    provider_code: str
    provider_name: str
    reliability_tier: str = "TIER_1_OFFICIAL"

    @abstractmethod
    def fetch_market_timeseries(
        self, symbols: Optional[List[str]] = None
    ) -> List[IngestedMarketPoint]:
        """Fetch latest and historical market time-series observations."""
        raise NotImplementedError

    def fetch_yield_curves(self) -> List[IngestedYieldPoint]:
        """Optional override for fixed-income yield curve providers."""
        return []


class BaseMacroDataProvider(ABC):
    """Abstract interface for macroeconomic data providers (CBN, NBS, DMO, FRED)."""

    provider_code: str
    provider_name: str
    reliability_tier: str = "TIER_1_OFFICIAL"

    @abstractmethod
    def fetch_macro_indicators(self) -> List[IngestedMacroPoint]:
        """Fetch macroeconomic indicator releases."""
        raise NotImplementedError


class BaseRegulatoryProvider(ABC):
    """Abstract interface for regulatory announcement & circular monitors (CBN, SEC, NGX, PenCom, NAICOM)."""

    provider_code: str
    provider_name: str
    regulator_code: str
    reliability_tier: str = "TIER_1_OFFICIAL"

    @abstractmethod
    def fetch_regulatory_publications(self) -> List[IngestedResearchItem]:
        """Fetch official regulatory circulars, directives, and policy announcements."""
        raise NotImplementedError


class BaseSearchProvider(ABC):
    """Abstract interface for financial research and news search providers (Tavily, Google Search)."""

    provider_code: str
    provider_name: str
    reliability_tier: str = "TIER_3_FINANCIAL_PRESS"

    @abstractmethod
    def search_financial_intelligence(
        self, query: str, max_results: int = 5
    ) -> List[IngestedResearchItem]:
        """Execute targeted financial intelligence search and return sanitized items."""
        raise NotImplementedError
