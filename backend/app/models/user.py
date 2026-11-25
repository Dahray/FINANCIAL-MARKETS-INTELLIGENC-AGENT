"""User, AuditLog, and AlertPreference ORM models."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, JSONVariant


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_uuid_str() -> str:
    return str(uuid.uuid4())


class User(Base):
    """Institutional platform user with Role-Based Access Control (RBAC)."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid_str)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="RESEARCH_ANALYST")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class AuditLog(Base):
    """Immutable security, governance, and operation audit trail."""

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid_str)
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    details: Mapped[Dict[str, Any]] = mapped_column(JSONVariant, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )


class AlertPreference(Base):
    """User-configurable scheduling, reporting frequency, and alert routing preferences."""

    __tablename__ = "alert_preferences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid_str)
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    report_day_of_week: Mapped[str] = mapped_column(String(16), default="FRI", nullable=False)
    report_time_wat: Mapped[str] = mapped_column(String(16), default="16:30", nullable=False)
    report_frequency: Mapped[str] = mapped_column(String(32), default="WEEKLY", nullable=False)
    email_recipients: Mapped[List[str]] = mapped_column(JSONVariant, nullable=False, default=list)
    enable_daily_macro_alerts: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enable_regulatory_circular_alerts: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enable_high_conviction_opportunity_alerts: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    min_opportunity_score_threshold: Mapped[float] = mapped_column(
        Numeric(5, 2), default=75.00, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
