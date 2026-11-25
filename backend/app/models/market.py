"""MarketTimeseries and YieldCurvePoint ORM models (TimescaleDB-ready time-series tables)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, JSONVariant
from app.models.user import new_uuid_str, utc_now


class MarketTimeseries(Base):
    """
    Time-series market data table (NGX equities, global indices, FX rates, money markets, commodities).
    Enforces all 9 mandatory Section 4 provenance fields plus deduplication hash.
    """

    __tablename__ = "market_timeseries"
    __table_args__ = (
        Index("ix_market_ts_symbol_pubdate", "symbol", "publication_date"),
        Index("ix_market_ts_asset_region", "asset_class", "market_region"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid_str)
    symbol: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    indicator_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    asset_class: Mapped[str] = mapped_column(String(64), nullable=False)
    market_region: Mapped[str] = mapped_column(String(64), nullable=False, default="NIGERIA")

    # Primary value & optional OHLCV fields
    value: Mapped[float] = mapped_column(Numeric(20, 6), nullable=False)
    open_value: Mapped[Optional[float]] = mapped_column(Numeric(20, 6), nullable=True)
    high_value: Mapped[Optional[float]] = mapped_column(Numeric(20, 6), nullable=True)
    low_value: Mapped[Optional[float]] = mapped_column(Numeric(20, 6), nullable=True)
    close_value: Mapped[Optional[float]] = mapped_column(Numeric(20, 6), nullable=True)
    volume: Mapped[Optional[float]] = mapped_column(Numeric(24, 4), nullable=True)
    market_cap: Mapped[Optional[float]] = mapped_column(Numeric(24, 2), nullable=True)

    # Mandatory Section 4 Provenance Metadata
    currency_or_unit: Mapped[str] = mapped_column(String(64), nullable=False)
    reporting_period: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    publication_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, nullable=False, index=True
    )
    retrieval_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    source_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    data_frequency: Mapped[str] = mapped_column(String(32), nullable=False, default="DAILY")
    verification_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="VERIFIED", index=True
    )

    quality_flags: Mapped[Dict[str, Any]] = mapped_column(
        JSONVariant, nullable=False, default=dict
    )
    dedup_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)


class YieldCurvePoint(Base):
    """
    Fixed-income yield curve observations (Nigerian Treasury Bills 91D/182D/364D,
    OMO bills, FGN Bonds 2Y-30Y, US Treasury benchmarks).
    Enforces all 9 mandatory Section 4 provenance fields.
    """

    __tablename__ = "yield_curve_points"
    __table_args__ = (
        Index("ix_yield_curve_name_date", "curve_name", "publication_date"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid_str)
    curve_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    instrument_type: Mapped[str] = mapped_column(String(64), nullable=False)
    tenor_label: Mapped[str] = mapped_column(String(32), nullable=False)
    tenor_days: Mapped[int] = mapped_column(Integer, nullable=False)
    tenor_years: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)

    # Mandatory Section 4 Provenance Metadata
    indicator_name: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False)
    coupon_rate: Mapped[Optional[float]] = mapped_column(Numeric(12, 6), nullable=True)
    bid_to_cover: Mapped[Optional[float]] = mapped_column(Numeric(12, 4), nullable=True)
    currency_or_unit: Mapped[str] = mapped_column(String(32), nullable=False, default="PERCENT")
    reporting_period: Mapped[str] = mapped_column(String(64), nullable=False)
    publication_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, nullable=False, index=True
    )
    retrieval_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    source_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    data_frequency: Mapped[str] = mapped_column(String(32), nullable=False, default="DAILY")
    verification_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="VERIFIED"
    )
    dedup_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
