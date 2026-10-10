from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimeStampedUUIDModel

if TYPE_CHECKING:
    from app.models.user import User

PASSWORD_RESET_EXPIRE_MINUTES = 30


def _default_expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=PASSWORD_RESET_EXPIRE_MINUTES)


class PasswordResetToken(TimeStampedUUIDModel):
    """Stores short-lived, single-use password reset tokens."""

    __tablename__ = "password_reset_tokens"

    token_hash: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_default_expires_at
    )
    is_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship("User", lazy="joined")

    @property
    def is_expired(self) -> bool:
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > expires_at

    @property
    def is_valid(self) -> bool:
        return not self.is_used and not self.is_expired
