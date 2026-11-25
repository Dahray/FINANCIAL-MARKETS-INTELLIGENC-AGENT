"""Initial FMIP 18-table institutional schema with TimescaleDB hypertables and pgvector.

Revision ID: 001_initial_fmip_schema
Revises: None
Create Date: 2026-11-25
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.db.base import Base
import app.models  # noqa: F401

revision: str = "001_initial_fmip_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create extensions, all 18 production tables, and TimescaleDB hypertables."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute('CREATE EXTENSION IF NOT EXISTS "timescaledb" CASCADE;')
        op.execute('CREATE EXTENSION IF NOT EXISTS "vector";')
        op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
        op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm";')

    Base.metadata.create_all(bind=bind)

    if bind.dialect.name == "postgresql":
        for table_name in ("market_timeseries", "yield_curve_points", "macro_indicators"):
            op.execute(
                sa.text(
                    f"SELECT create_hypertable('{table_name}', 'publication_date', "
                    f"if_not_exists => TRUE, migrate_data => TRUE);"
                )
            )


def downgrade() -> None:
    """Drop all FMIP tables in reverse dependency order."""
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
