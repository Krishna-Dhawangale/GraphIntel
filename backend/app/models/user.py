import enum
import uuid
from typing import TYPE_CHECKING, List

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimeStampedUUIDModel

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.query import Query


class UserRole(str, enum.Enum):
    USER = "USER"
    ANALYST = "ANALYST"
    ADMIN = "ADMIN"


class User(TimeStampedUUIDModel):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    role: Mapped[str] = mapped_column(String(50), default=UserRole.USER.value, nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(
        String(64), default=lambda: str(uuid.uuid4()), nullable=False, index=True
    )

    # Relationships
    documents: Mapped[List["Document"]] = relationship(
        "Document", back_populates="user", cascade="all, delete-orphan"
    )
    queries: Mapped[List["Query"]] = relationship(
        "Query", back_populates="user", cascade="all, delete-orphan"
    )
