"""MacroIndicator ORM model (TimescaleDB-ready macroeconomic time-series table)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import new_uuid_str, utc_now


class MacroIndicator(Base):
    """
    Macroeconomic indicator observations (Inflation CPI, GDP, MPR, CRR, Reserves,
    Debt, Fiscal balance, Employment, Manufacturing PMI, Trade balance, Global macro).
    Enforces all 9 mandatory Section 4 provenance fields.
    """

    __tablename__ = "macro_indicators"
    __table_args__ = (
        Index("ix_macro_code_country_date", "indicator_code", "country", "publication_date"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid_str)
    indicator_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    indicator_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    country: Mapped[str] = mapped_column(String(64), nullable=False, default="NIGERIA", index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Values
    value: Mapped[float] = mapped_column(Numeric(20, 6), nullable=False)
    previous_value: Mapped[Optional[float]] = mapped_column(Numeric(20, 6), nullable=True)
    consensus_estimate: Mapped[Optional[float]] = mapped_column(Numeric(20, 6), nullable=True)

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
    data_frequency: Mapped[str] = mapped_column(String(32), nullable=False, default="MONTHLY")
    verification_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="VERIFIED"
    )
    dedup_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
