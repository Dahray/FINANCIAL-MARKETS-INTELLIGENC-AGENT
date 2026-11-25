"""Database engine, session factory, and TimescaleDB/pgvector initialization."""

from __future__ import annotations

from pathlib import Path
from typing import Generator, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import PROJECT_ROOT, settings
from app.core.logging import get_logger
from app.db.base import Base

logger = get_logger("fmip.db")

_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker[Session]] = None


def _can_connect_postgres(url: str) -> bool:
    """Test whether PostgreSQL is reachable within a short connect timeout."""
    try:
        test_engine = create_engine(
            url,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 2},
        )
        with test_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        test_engine.dispose()
        return True
    except Exception:
        return False


def get_engine(override_url: Optional[str] = None) -> Engine:
    """
    Return the active SQLAlchemy engine.
    Connects to PostgreSQL (TimescaleDB + pgvector) by default.
    If PostgreSQL container is not yet running during local dev/test, logs a clear notice
    and falls back to a local persistent database file so development/testing never crashes.
    """
    global _engine
    if override_url:
        if override_url.startswith("sqlite"):
            return create_engine(
                override_url,
                connect_args={"check_same_thread": False},
            )
        return create_engine(override_url, pool_pre_ping=True)

    if _engine is not None:
        return _engine

    pg_url = settings.effective_database_url
    if pg_url.startswith("sqlite"):
        _engine = create_engine(
            pg_url,
            connect_args={"check_same_thread": False},
        )
        return _engine

    if _can_connect_postgres(pg_url):
        logger.info("Connected to PostgreSQL + TimescaleDB + pgvector database.")
        _engine = create_engine(
            pg_url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
        return _engine

    fallback_path = PROJECT_ROOT / "storage" / "fmip_local.db"
    fallback_path.parent.mkdir(parents=True, exist_ok=True)
    fallback_url = f"sqlite:///{fallback_path}"
    logger.warning(
        "PostgreSQL daemon is not reachable at %s:%s. Using local persistent SQL database (%s) until Docker PostgreSQL container is started.",
        settings.POSTGRES_HOST,
        settings.POSTGRES_PORT,
        fallback_path,
    )
    _engine = create_engine(
        fallback_url,
        connect_args={"check_same_thread": False},
    )
    return _engine


def get_session_factory(engine: Optional[Engine] = None) -> sessionmaker[Session]:
    """Return a configured SQLAlchemy sessionmaker."""
    global _SessionLocal
    if engine is not None:
        return sessionmaker(autocommit=False, autoflush=False, bind=engine)
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine(),
        )
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a database session."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


def init_database_schema(engine: Optional[Engine] = None) -> None:
    """
    Initialize all 18 ORM tables and configure PostgreSQL extensions
    (TimescaleDB hypertables + pgvector) when running on PostgreSQL.
    """
    import app.models  # noqa: F401 - ensure all models are registered on Base.metadata

    target_engine = engine or get_engine()
    if target_engine.dialect.name == "postgresql":
        with target_engine.begin() as conn:
            for ext in ("timescaledb", "vector", "uuid-ossp", "pg_trgm"):
                try:
                    conn.execute(text(f'CREATE EXTENSION IF NOT EXISTS "{ext}" CASCADE;'))
                except Exception as exc:
                    logger.warning("Extension %s setup note: %s", ext, exc)

    Base.metadata.create_all(bind=target_engine)

    if target_engine.dialect.name == "postgresql":
        hypertables = [
            ("market_timeseries", "publication_date"),
            ("yield_curve_points", "publication_date"),
            ("macro_indicators", "publication_date"),
        ]
        for table_name, time_col in hypertables:
            try:
                with target_engine.begin() as conn:
                    conn.execute(
                        text(
                            f"SELECT create_hypertable('{table_name}', '{time_col}', "
                            f"if_not_exists => TRUE, migrate_data => TRUE);"
                        )
                    )
            except Exception as exc:
                logger.info(
                    "Standard PostgreSQL table active for %s (TimescaleDB hypertable note: %s)",
                    table_name,
                    exc,
                )
