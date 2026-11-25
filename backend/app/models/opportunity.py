"""Opportunity ORM model for the Continuous Investment & Strategic Business Opportunity Radar."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy import DateTime, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, JSONVariant
from app.models.user import new_uuid_str, utc_now


class Opportunity(Base):
    """
    Section 6 Investment Opportunity Radar & Section 3 (Agent 7) Strategic Business Opportunity record.
    Ranks opportunities across 7 core dimensions and evaluates business opportunities across 10 strategic criteria.
    Enforces an explicit evidence quality gate (never forces recommendations when evidence is insufficient).
    """

    __tablename__ = "opportunities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid_str)
    opportunity_class: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True, default="INVESTMENT_OPPORTUNITY"
    )
    radar_category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_business_line: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    instrument_or_sector: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    geography: Mapped[str] = mapped_column(String(64), nullable=False, default="Nigeria")

    # Thesis, quantitative evidence, assumptions & risk assessment
    thesis: Mapped[str] = mapped_column(Text, nullable=False)
    supporting_quantitative_evidence: Mapped[Dict[str, Any]] = mapped_column(
        JSONVariant, nullable=False, default=dict
    )
    assumptions: Mapped[List[str]] = mapped_column(JSONVariant, nullable=False, default=list)
    risk_assessment: Mapped[str] = mapped_column(Text, nullable=False)

    # 7 Mandatory Investment Radar Ranking Dimensions (0-100 scale)
    score_potential_return: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    score_risk_adjusted: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    score_market_attractiveness: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    score_evidence_quality: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    score_liquidity: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    score_regulatory_feasibility: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    time_horizon: Mapped[str] = mapped_column(
        String(32), nullable=False, default="MEDIUM_TERM_6_18M"
    )

    # 10 Strategic Business Evaluation Criteria (Agent 7 Section 3)
    strategic_evaluation_matrix: Mapped[Dict[str, Any]] = mapped_column(
        JSONVariant, nullable=False, default=dict
    )

    composite_rank_score: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="ACTIVE_HIGH_CONVICTION", index=True
    )
    source_register_ids: Mapped[List[str]] = mapped_column(
        JSONVariant, nullable=False, default=list
    )
    identified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
