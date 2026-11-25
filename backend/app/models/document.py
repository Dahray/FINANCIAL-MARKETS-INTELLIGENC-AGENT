"""ResearchDocument and DocumentChunk (pgvector) ORM models."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, EmbeddingVector, JSONVariant
from app.models.user import new_uuid_str, utc_now


class ResearchDocument(Base):
    """
    Sanitized full-text regulatory circulars, annual reports, financial statements,
    market news articles, and archived weekly research reports.
    """

    __tablename__ = "research_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid_str)
    source_register_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("source_register.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    issuer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    structured_extract: Mapped[Dict[str, Any]] = mapped_column(
        JSONVariant, nullable=False, default=dict
    )
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)


class DocumentChunk(Base):
    """
    Semantic chunk with 768-dimensional pgvector embedding for RAG retrieval
    by the Executive AI Research Assistant and research agents.
    """

    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid_str)
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("research_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Optional[List[float]]] = mapped_column(
        EmbeddingVector(768), nullable=True
    )
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONVariant, nullable=False, default=dict
    )
