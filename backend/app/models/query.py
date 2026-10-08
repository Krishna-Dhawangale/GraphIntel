import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimeStampedUUIDModel, utc_now

if TYPE_CHECKING:
    from app.models.chunk import DocumentChunk
    from app.models.user import User


class Query(TimeStampedUUIDModel):
    __tablename__ = "queries"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tenant_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    retrieval_time_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    llm_time_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="queries")
    sources: Mapped[List["Source"]] = relationship(
        "Source", back_populates="query", cascade="all, delete-orphan"
    )


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True
    )
    query_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("queries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("document_chunks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    citation_order: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    # Relationships
    query: Mapped["Query"] = relationship("Query", back_populates="sources")
    chunk: Mapped[Optional["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="sources"
    )
