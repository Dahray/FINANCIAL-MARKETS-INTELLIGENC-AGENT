"""Alembic Migration 002: Verification Engine Columns & Institutional Research Memory Tables.

Revision ID: 002_verification_and_memory
Revises: 001_initial_fmip_schema
Create Date: 2026-11-26
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.db.base import Base
import app.models  # noqa: F401


revision = "002_verification_and_memory"
down_revision = "001_initial_fmip_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # 1. Non-destructively add Part 1.2 verification columns to existing time-series tables
    for tbl in ("macro_indicators", "market_timeseries", "yield_curve_points"):
        if tbl in existing_tables:
            cols = {c["name"] for c in inspector.get_columns(tbl)}
            if "effective_date" not in cols:
                op.add_column(tbl, sa.Column("effective_date", sa.DateTime(timezone=True), nullable=True))
            if "source_url" not in cols:
                op.add_column(tbl, sa.Column("source_url", sa.Text(), nullable=True))
            if "source_tier" not in cols:
                op.add_column(tbl, sa.Column("source_tier", sa.String(32), server_default="TIER_1_OFFICIAL", nullable=False))
            if "confidence_score" not in cols:
                op.add_column(tbl, sa.Column("confidence_score", sa.Numeric(5, 2), server_default="98.0", nullable=False))
            if "is_authoritative" not in cols:
                op.add_column(tbl, sa.Column("is_authoritative", sa.Boolean(), server_default=sa.true(), nullable=False))
            if "is_archival_baseline" not in cols:
                op.add_column(tbl, sa.Column("is_archival_baseline", sa.Boolean(), server_default=sa.false(), nullable=False))

    if "quant_forecasts" in existing_tables:
        qcols = {c["name"] for c in inspector.get_columns("quant_forecasts")}
        if "agent_name" not in qcols:
            op.add_column("quant_forecasts", sa.Column("agent_name", sa.String(64), server_default="AGENT_6_QUANT", nullable=False))
        if "predicted_direction" not in qcols:
            op.add_column("quant_forecasts", sa.Column("predicted_direction", sa.String(16), server_default="FLAT", nullable=False))
        if "source_register_ids" not in qcols:
            op.add_column("quant_forecasts", sa.Column("source_register_ids", sa.JSON(), nullable=True))

    # 2. Create all 10 new institutional research memory, discrepancy, forecast outcome & KG tables
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    for tbl in (
        "knowledge_graph_edges",
        "knowledge_graph_nodes",
        "opportunity_evaluations",
        "research_performance_evaluations",
        "forecast_outcomes",
        "identified_risks",
        "strategic_recommendations",
        "research_findings",
        "intelligence_change_log",
        "data_discrepancies",
    ):
        op.drop_table(tbl)
