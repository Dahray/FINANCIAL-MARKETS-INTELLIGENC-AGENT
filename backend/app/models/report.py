"""AgentRun, EditorialReview, and WeeklyReport ORM models."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, JSONVariant
from app.models.user import new_uuid_str, utc_now


class AgentRun(Base):
    """Execution log for multi-agent research cycles."""

    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid_str)
    run_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    reporting_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reporting_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="RUNNING", index=True)
    agent_outputs_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONVariant, nullable=False, default=dict
    )
    revision_iterations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class EditorialReview(Base):
    """
    Agent 8 (Chief Research Editor) quality-gate review record.
    Captures identified contradictions, challenged assumptions, removed unsupported claims,
    missing research gaps, numeric audit results, and citation verification results.
    """

    __tablename__ = "editorial_reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid_str)
    agent_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    iteration_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    contradictions_identified: Mapped[List[str]] = mapped_column(
        JSONVariant, nullable=False, default=list
    )
    weak_assumptions_challenged: Mapped[List[str]] = mapped_column(
        JSONVariant, nullable=False, default=list
    )
    unverified_claims_removed: Mapped[List[str]] = mapped_column(
        JSONVariant, nullable=False, default=list
    )
    missing_research_gaps: Mapped[List[str]] = mapped_column(
        JSONVariant, nullable=False, default=list
    )
    numeric_audit_passed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    citation_audit_passed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    editor_verdict: Mapped[str] = mapped_column(
        String(32), nullable=False, default="APPROVED_FOR_PUBLICATION"
    )
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class WeeklyReport(Base):
    """
    Friday-to-Friday Comprehensive Weekly Financial Markets Intelligence Report
    containing all 16 mandatory institutional sections, answers to the 5 Core Strategic Questions,
    and links to the generated PDF, Excel workbook, and Google Drive archives.
    """

    __tablename__ = "weekly_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid_str)
    agent_run_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    report_code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    period_start_friday: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    period_end_friday: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    five_strategic_questions_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONVariant, nullable=False, default=dict
    )
    sections_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONVariant, nullable=False, default=dict
    )
    pdf_file_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    excel_file_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    google_drive_pdf_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    google_drive_excel_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email_delivery_status: Mapped[str] = mapped_column(
        String(64), nullable=False, default="PENDING"
    )
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )
