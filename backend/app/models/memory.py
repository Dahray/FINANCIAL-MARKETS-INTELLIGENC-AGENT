"""
Institutional Historical Research Memory, Verification Governance, Forecast Outcomes,
and Knowledge Graph ORM Models (Parts 1, 2, 3, 5, 6 & Ultimate Product Vision).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, JSONVariant
from app.models.user import new_uuid_str, utc_now


class DataDiscrepancy(Base):
    """
    Automated Cross-Source Discrepancy Log (Part 1.5).
    Preserves conflicting readings across providers/sources, applies Tier 1 > Tier 2 > Tier 3
    and publication/effective date precedence, and flags unresolved material divergences.
    """

    __tablename__ = "data_discrepancies"
    __table_args__ = (
        Index("ix_discrepancy_indicator_status", "indicator_code", "resolution_status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid_str)
    indicator_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    indicator_name: Mapped[str] = mapped_column(String(255), nullable=False)
    reporting_period: Mapped[str] = mapped_column(String(64), nullable=False)

    # Primary (winning / official) observation
    primary_source: Mapped[str] = mapped_column(String(128), nullable=False)
    primary_source_tier: Mapped[str] = mapped_column(String(32), nullable=False)
    primary_value: Mapped[float] = mapped_column(Numeric(20, 6), nullable=False)
    primary_publication_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    primary_effective_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Conflicting observation
    conflicting_source: Mapped[str] = mapped_column(String(128), nullable=False)
    conflicting_source_tier: Mapped[str] = mapped_column(String(32), nullable=False)
    conflicting_value: Mapped[float] = mapped_column(Numeric(20, 6), nullable=False)
    conflicting_publication_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    variance_abs: Mapped[float] = mapped_column(Numeric(20, 6), nullable=False)
    variance_pct: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)

    authoritative_value: Mapped[float] = mapped_column(Numeric(20, 6), nullable=False)
    authoritative_source: Mapped[str] = mapped_column(String(128), nullable=False)
    resolution_rule: Mapped[str] = mapped_column(Text, nullable=False)
    resolution_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="RESOLVED_BY_HIERARCHY",
        index=True,
    )  # RESOLVED_BY_HIERARCHY | DISPUTED_NEEDS_REVIEW | SUPERSEDED_BY_NEWER_OFFICIAL
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )


class IntelligenceChangeLog(Base):
    """
    Immutable Governance & Intelligence Change Audit Trail (Part 5E & Part 6).
    Tracks updated financial indicators, corrected figures, new research findings,
    changed forecasts, invalidated opportunities, and regulatory updates.
    """

    __tablename__ = "intelligence_change_log"
    __table_args__ = (
        Index("ix_change_log_type_date", "change_category", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid_str)
    change_category: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )  # DATA_UPDATE | DATA_CORRECTION | NEW_FINDING | FORECAST_EVALUATION | OPPORTUNITY_STATUS | REGULATORY_UPDATE | RECOMMENDATION_REVIEW
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    previous_state_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONVariant, nullable=False, default=dict
    )
    new_state_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONVariant, nullable=False, default=dict
    )
    source_or_actor: Mapped[str] = mapped_column(String(128), nullable=False, default="SYSTEM_VERIFIER")
    evidence_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )


class ResearchFinding(Base):
    """
    Structured Persistent Research Finding (Part 2.2).
    Each finding carries a unique `finding_code` tracked continuously across weekly,
    monthly, and quarterly reporting periods so institutional knowledge accumulates over time.
    """

    __tablename__ = "research_findings"
    __table_args__ = (
        Index("ix_research_findings_domain_status", "domain", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid_str)
    finding_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    market_region: Mapped[str] = mapped_column(String(64), nullable=False, default="NIGERIA")
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    epistemic_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="VERIFIED_FACT"
    )
    confidence_level_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=85.0)
    assumptions_json: Mapped[List[str]] = mapped_column(JSONVariant, nullable=False, default=list)
    supporting_metrics_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONVariant, nullable=False, default=dict
    )
    source_register_ids: Mapped[List[str]] = mapped_column(
        JSONVariant, nullable=False, default=list
    )
    first_report_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    last_report_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="ACTIVE"
    )  # ACTIVE | STRENGTHENED | WEAKENED | INVALIDATED | RESOLVED
    evolution_notes_json: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONVariant, nullable=False, default=list
    )
    first_identified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class StrategicRecommendation(Base):
    """
    Persistent Strategic Business Recommendation Tracker (Part 2.6).
    Tracks original recommendation, supporting market evidence, expected business benefits,
    risks, required next steps, review date, and subsequent periodic re-assessments.
    """

    __tablename__ = "strategic_recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid_str)
    recommendation_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    target_business_line: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    original_recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    supporting_evidence_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONVariant, nullable=False, default=dict
    )
    expected_business_benefits: Mapped[str] = mapped_column(Text, nullable=False)
    identified_risks: Mapped[str] = mapped_column(Text, nullable=False)
    required_next_steps_json: Mapped[List[str]] = mapped_column(
        JSONVariant, nullable=False, default=list
    )
    preliminary_business_case_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONVariant, nullable=False, default=dict
    )
    first_report_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="ACTIVE_ATTRACTIVE", index=True
    )  # ACTIVE_ATTRACTIVE | UNDER_INVESTIGATION | LESS_ATTRACTIVE | IMPLEMENTED | INVALIDATED | EXPIRED
    review_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reassessment_history_json: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONVariant, nullable=False, default=list
    )
    source_register_ids: Mapped[List[str]] = mapped_column(
        JSONVariant, nullable=False, default=list
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class IdentifiedRisk(Base):
    """
    Persistent Institutional Risk Register (Part 2.2 & Part 3).
    Tracks macro, market, credit, FX, regulatory, and competitive risks across weeks
    to answer whether risks identified 3 months ago remain relevant or have materialised.
    """

    __tablename__ = "identified_risks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid_str)
    risk_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    trigger_indicator_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    trigger_threshold: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, default="HIGH")
    likelihood: Mapped[str] = mapped_column(String(32), nullable=False, default="MEDIUM")
    mitigation_strategy: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="ACTIVE", index=True
    )  # ACTIVE | ESCALATED | MATERIALISED | MITIGATED | RETIRED
    first_report_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    last_reviewed_report_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source_register_ids: Mapped[List[str]] = mapped_column(
        JSONVariant, nullable=False, default=list
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class ForecastOutcome(Base):
    """
    Immutable Realized Forecast Outcome Evaluation Record (Part 2.3 & Part 2.4).
    Strictly separate from `quant_forecasts` — original predictions are NEVER overwritten.
    Evaluates matured forecasts against verified official market outcomes.
    """

    __tablename__ = "forecast_outcomes"
    __table_args__ = (
        Index("ix_forecast_outcomes_status_target", "outcome_status", "target_code"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid_str)
    forecast_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("quant_forecasts.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    target_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    agent_name: Mapped[str] = mapped_column(String(64), nullable=False, default="AGENT_6_QUANT")
    forecast_horizon_label: Mapped[str] = mapped_column(String(64), nullable=False)

    # Immutable snapshot of the original forecast
    original_baseline_value: Mapped[float] = mapped_column(Numeric(20, 6), nullable=False)
    predicted_value: Mapped[float] = mapped_column(Numeric(20, 6), nullable=False)
    predicted_direction: Mapped[str] = mapped_column(String(16), nullable=False)
    forecast_generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    forecast_target_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Realized market outcome (null while PENDING)
    actual_value: Mapped[Optional[float]] = mapped_column(Numeric(20, 6), nullable=True)
    actual_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_source: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    actual_direction: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)

    # Quantitative Error Metrics
    absolute_error: Mapped[Optional[float]] = mapped_column(Numeric(20, 6), nullable=True)
    squared_error: Mapped[Optional[float]] = mapped_column(Numeric(24, 6), nullable=True)
    percentage_error_pct: Mapped[Optional[float]] = mapped_column(Numeric(12, 4), nullable=True)
    direction_correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    within_bull_bear_band: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    outcome_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="PENDING", index=True
    )  # PENDING | CORRECT | PARTIALLY_CORRECT | INCORRECT
    assumptions_validity_review: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    influencing_factors: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    model_oversights: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class ResearchPerformanceEvaluation(Base):
    """
    Periodic Research Quality Assurance & Continuous Improvement Snapshot (Part 2.2 & Vision #5/#7).
    """

    __tablename__ = "research_performance_evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid_str)
    period_label: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    report_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    total_forecasts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    evaluated_forecasts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pending_forecasts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mae: Mapped[Optional[float]] = mapped_column(Numeric(20, 6), nullable=True)
    rmse: Mapped[Optional[float]] = mapped_column(Numeric(20, 6), nullable=True)
    mape_pct: Mapped[Optional[float]] = mapped_column(Numeric(12, 4), nullable=True)
    directional_accuracy_pct: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    qa_scorecard_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONVariant, nullable=False, default=dict
    )
    lessons_learned: Mapped[List[str]] = mapped_column(JSONVariant, nullable=False, default=list)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )


class OpportunityEvaluation(Base):
    """
    Historical Lifecycle Evaluation & 14-Point Business Case for Tracked Opportunities (Part 2.5 & Vision #2).
    """

    __tablename__ = "opportunity_evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid_str)
    opportunity_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    report_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    previous_status: Mapped[str] = mapped_column(String(48), nullable=False)
    new_status: Mapped[str] = mapped_column(
        String(48), nullable=False, index=True
    )  # NEWLY_IDENTIFIED | UNDER_INVESTIGATION | MONITORING | ACTIVE_OPPORTUNITY | OPPORTUNITY_MATERIALISED | OPPORTUNITY_INVALIDATED | EXPIRED
    thesis_still_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    what_changed: Mapped[str] = mapped_column(Text, nullable=False)
    catalysts_status_json: Mapped[List[str]] = mapped_column(
        JSONVariant, nullable=False, default=list
    )
    business_case_14pt_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONVariant, nullable=False, default=dict
    )
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )


class KnowledgeGraphNode(Base):
    """Institutional Knowledge Graph Node (Vision #3)."""

    __tablename__ = "knowledge_graph_nodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid_str)
    node_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    node_type: Mapped[str] = mapped_column(
        String(48), nullable=False, index=True
    )  # INDICATOR | MARKET_EVENT | REGULATORY_EVENT | COMPETITOR | OPPORTUNITY | FORECAST | RECOMMENDATION | RISK
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    attributes_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONVariant, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class KnowledgeGraphEdge(Base):
    """Institutional Knowledge Graph Directed Relationship Edge (Vision #3)."""

    __tablename__ = "knowledge_graph_edges"
    __table_args__ = (
        Index("ix_kg_edge_source_target", "source_node_id", "target_node_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid_str)
    source_node_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_graph_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_node_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_graph_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relationship_type: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )  # DRIVES | REGULATES | CREATES_OPPORTUNITY | THREATENS | VALIDATES | INVALIDATES | CORRELATES_WITH | SUPERSEDES
    evidence_summary: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=85.0)
    source_register_ids: Mapped[List[str]] = mapped_column(
        JSONVariant, nullable=False, default=list
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
