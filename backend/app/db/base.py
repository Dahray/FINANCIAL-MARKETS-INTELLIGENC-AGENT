"""SQLAlchemy 2.0 Declarative Base and cross-dialect pgvector/JSON type decorators."""

from __future__ import annotations

import json
from typing import Any, List, Optional

from sqlalchemy import JSON, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import TypeDecorator


class Base(DeclarativeBase):
    """Base class for all FMIP SQLAlchemy 2.0 ORM models."""

    pass


# Dialect-aware JSONB type (uses native PostgreSQL JSONB on Postgres, JSON elsewhere)
JSONVariant = JSON().with_variant(JSONB(), "postgresql")


class EmbeddingVector(TypeDecorator):
    """
    768-dimensional embedding vector column type.
    Uses pgvector `Vector(dim)` on PostgreSQL and JSON array serialization on fallback dialects.
    """

    impl = Text
    cache_ok = True

    def __init__(self, dim: int = 768, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.dim = dim

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            try:
                from pgvector.sqlalchemy import Vector

                return dialect.type_descriptor(Vector(self.dim))
            except ImportError:
                return dialect.type_descriptor(Text())
        return dialect.type_descriptor(Text())

    def process_bind_param(
        self, value: Optional[List[float]], dialect
    ) -> Optional[Any]:
        if value is None:
            return None
        if dialect.name == "postgresql":
            try:
                import pgvector  # noqa: F401

                return [float(x) for x in value]
            except ImportError:
                return json.dumps([float(x) for x in value])
        return json.dumps([float(x) for x in value])

    def process_result_value(
        self, value: Optional[Any], dialect
    ) -> Optional[List[float]]:
        if value is None:
            return None
        if isinstance(value, list):
            return [float(x) for x in value]
        if hasattr(value, "tolist"):
            return [float(x) for x in value.tolist()]
        if isinstance(value, str):
            return [float(x) for x in json.loads(value)]
        return list(value)
