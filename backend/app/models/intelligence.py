"""MarketDevelopment (11-question framework), CompetitorProfile, CompetitorEvent, and RegulatoryEvent models."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, JSONVariant
from app.models.user import new_uuid_str, utc_now


class MarketDevelopment(Base):
    """
    Section 5 Research & Intelligence Engine record.
    Stores the mandatory 11-question deep analytical breakdown for every significant development,
    explicitly separating Facts, Estimates, Opinions, and AI-Generated Interpretations.
    """

    __tablename__ = "market_developments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid_str)
    headline: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    market_region: Mapped[str] = mapped_column(String(64), nullable=False, default="NIGERIA", index=True)
    event_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    # Mandatory 11 Questions (Section 5)
    q1_what_happened: Mapped[str] = mapped_column(Text, nullable=False)
    q2_why_it_happened: Mapped[str] = mapped_column(Text, nullable=False)
    q3_what_caused_it: Mapped[str] = mapped_column(Text, nullable=False)
    q4_why_significant: Mapped[str] = mapped_column(Text, nullable=False)
    q5_who_benefits: Mapped[List[str]] = mapped_column(JSONVariant, nullable=False, default=list)
    q6_who_loses: Mapped[List[str]] = mapped_column(JSONVariant, nullable=False, default=list)
    q7_immediate_implications: Mapped[str] = mapped_column(Text, nullable=False)
    q8_long_term_implications: Mapped[str] = mapped_column(Text, nullable=False)
    q9_opportunities_created: Mapped[str] = mapped_column(Text, nullable=False)
    q10_risks_introduced: Mapped[str] = mapped_column(Text, nullable=False)
    q11_management_considerations: Mapped[str] = mapped_column(Text, nullable=False)

    # Quantitative evidence & epistemic classification
    quantitative_evidence: Mapped[Dict[str, Any]] = mapped_column(
        JSONVariant, nullable=False, default=dict
    )
    epistemic_breakdown: Mapped[Dict[str, List[str]]] = mapped_column(
        JSONVariant, nullable=False, default=dict
    )
    significance_score: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False, default=80.0
    )
    verification_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="EDITOR_APPROVED", index=True
    )
    source_register_ids: Mapped[List[str]] = mapped_column(
        JSONVariant, nullable=False, default=list
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class CompetitorProfile(Base):
    """
    Financial services competitor profile across 9 mandatory categories:
    ASSET_MANAGEMENT, COMMERCIAL_BANK, INVESTMENT_BANK, PFA, INSURANCE,
    FINTECH, BROKERAGE, INVESTMENT_PLATFORM, WEALTH_MANAGEMENT.
    """

    __tablename__ = "competitor_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid_str)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    tier: Mapped[str] = mapped_column(String(32), nullable=False, default="TIER_1_LEADER")
    headquarters: Mapped[str] = mapped_column(String(128), nullable=False, default="Lagos, Nigeria")
    key_products: Mapped[List[str]] = mapped_column(JSONVariant, nullable=False, default=list)
    aum_or_capital_estimate: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    competitive_strengths: Mapped[List[str]] = mapped_column(JSONVariant, nullable=False, default=list)
    vulnerabilities: Mapped[List[str]] = mapped_column(JSONVariant, nullable=False, default=list)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class CompetitorEvent(Base):
    """
    Tracked competitive moves: new products, market entry, M&A, partnerships,
    business model innovation, expansion, positioning, pricing changes, strategic investments.
    """

    __tablename__ = "competitor_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid_str)
    competitor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("competitor_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    what_they_are_doing_differently: Mapped[str] = mapped_column(Text, nullable=False)
    implications_for_our_business: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_counter_strategy: Mapped[str] = mapped_column(Text, nullable=False)
    threat_level: Mapped[str] = mapped_column(String(32), nullable=False, default="MODERATE")
    source_register_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("source_register.id", ondelete="RESTRICT"), nullable=False, index=True
    )


class RegulatoryEvent(Base):
    """
    Tracked regulatory circulars, policy changes, and compliance directives from
    CBN, SEC Nigeria, NGX, PenCom, NAICOM, FRC, Federal Ministry of Finance, and global regulators.
    """

    __tablename__ = "regulatory_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid_str)
    regulator_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    regulator_name: Mapped[str] = mapped_column(String(255), nullable=False)
    reference_number: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    issued_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    effective_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    policy_summary: Mapped[str] = mapped_column(Text, nullable=False)
    compliance_implications: Mapped[str] = mapped_column(Text, nullable=False)
    capital_or_operational_impact: Mapped[str] = mapped_column(Text, nullable=False)
    business_opportunities_created: Mapped[str] = mapped_column(Text, nullable=False)
    affected_segments: Mapped[List[str]] = mapped_column(JSONVariant, nullable=False, default=list)
    severity: Mapped[str] = mapped_column(
        String(32), nullable=False, default="MANDATORY_COMPLIANCE", index=True
    )
    is_official_publication: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source_register_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("source_register.id", ondelete="RESTRICT"), nullable=False, index=True
    )
