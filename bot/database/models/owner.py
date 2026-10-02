"""Owner model — bot owners/admins."""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    BigInteger, DateTime, Enum, String
)
from sqlalchemy.orm import (
    Mapped, mapped_column
)

from bot.database.base import Base


class OwnerRole(str, PyEnum):
    """Owner role enum."""
    SUPERADMIN = "superadmin"
    ADMIN = "admin"


class Owner(Base):
    """Bot owner model."""

    __tablename__ = "owners"

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True
    )
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True,
        nullable=False, index=True
    )
    username: Mapped[Optional[str]] = (
        mapped_column(String(64), nullable=True)
    )
    role: Mapped[OwnerRole] = mapped_column(
        Enum(OwnerRole),
        default=OwnerRole.ADMIN,
        nullable=False
    )
    added_date: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<Owner(tg_id={self.telegram_id}, "
            f"role={self.role.value})>"
        )