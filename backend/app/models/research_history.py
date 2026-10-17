from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimeStampedUUIDModel, utc_now

if TYPE_CHECKING:
    from app.models.user import User


class ResearchHistory(TimeStampedUUIDModel):
    """
    Persistent Research Session History model.
    Supports authenticated users (user_id) and isolated guest sessions (guest_session_id).
    """
    __tablename__ = "research_history"

    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    guest_session_id: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, index=True
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    retrieval_mode: Mapped[str] = mapped_column(
        String(32), default="hybrid", nullable=False, index=True
    )
    citations_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    graph_paths_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="SUCCESS", nullable=False)

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", backref="research_histories")

    __table_args__ = (
        Index("ix_research_history_user_created", "user_id", "created_at"),
        Index("ix_research_history_guest_created", "guest_session_id", "created_at"),
    )
