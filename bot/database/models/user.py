"""User model — bot users (buyers)."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, DateTime,
    Numeric, String
)
from sqlalchemy.orm import (
    Mapped, mapped_column, relationship
)

from bot.database.base import Base


class User(Base):
    """Bot user (buyer) model."""

    __tablename__ = "users"

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
    first_name: Mapped[Optional[str]] = (
        mapped_column(String(128), nullable=True)
    )
    wallet_balance: Mapped[Decimal] = (
        mapped_column(
            Numeric(12, 2),
            default=Decimal("0.00"),
            nullable=False
        )
    )
    language_code: Mapped[str] = mapped_column(
        String(5), default="en", nullable=False
    )
    is_banned: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    joined_date: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    # ── Relationships ──
    wallet_requests = relationship(
        "WalletRequest",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<User(tg_id={self.telegram_id}, "
            f"balance={self.wallet_balance})>"
        )