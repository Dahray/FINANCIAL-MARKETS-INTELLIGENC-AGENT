"""DataSource and SourceRegister ORM models for complete research traceability."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, JSONVariant
from app.models.user import new_uuid_str, utc_now


class DataSource(Base):
    """Approved financial data providers, exchanges, statistical agencies, and regulators."""

    __tablename__ = "data_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid_str)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    country: Mapped[str] = mapped_column(String(64), nullable=False, default="NIGERIA")
    base_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reliability_tier: Mapped[str] = mapped_column(
        String(32), nullable=False, default="TIER_1_OFFICIAL"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_successful_fetch_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class SourceRegister(Base):
    """
    Immutable citation ledger required by Section 5 & Section 7 (Report Section 16).
    Tracks every source, publication date, URL, relevant finding, reliability classification,
    and epistemic distinction (FACT, ESTIMATE, OPINION, AI_INTERPRETATION).
    """

    __tablename__ = "source_register"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid_str)
    source_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    publication_title: Mapped[str] = mapped_column(Text, nullable=False)
    publication_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    retrieval_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    relevant_finding: Mapped[str] = mapped_column(Text, nullable=False)
    reliability_classification: Mapped[str] = mapped_column(
        String(32), nullable=False, default="TIER_1_OFFICIAL"
    )
    epistemic_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="FACT"
    )
    verification_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="VERIFIED"
    )
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONVariant, nullable=False, default=dict
    )
