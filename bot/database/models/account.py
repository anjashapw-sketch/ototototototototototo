"""Account model — Telegram accounts in stock."""

from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, DateTime,
    Enum, ForeignKey, Numeric, String, Text
)
from sqlalchemy.orm import (
    Mapped, mapped_column
)

from bot.database.base import Base


class AccountStatus(str, PyEnum):
    """Account status enum."""
    IN_STOCK = "instock"
    SOLD = "sold"


class Account(Base):
    """Telegram account model."""

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True
    )
    phone: Mapped[str] = mapped_column(
        String(20), unique=True,
        nullable=False, index=True
    )
    country_code: Mapped[str] = mapped_column(
        String(5), nullable=False, index=True
    )
    country_name: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    session_string: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    twofa_password: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    status: Mapped[AccountStatus] = mapped_column(
        Enum(AccountStatus),
        default=AccountStatus.IN_STOCK,
        nullable=False, index=True
    )
    price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    added_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("owners.id"),
        nullable=False
    )
    added_date: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    sold_to: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=True
    )
    sold_date: Mapped[Optional[datetime]] = (
        mapped_column(DateTime, nullable=True)
    )
    session_alive: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    device_fingerprint: Mapped[Optional[str]] = (
        mapped_column(Text, nullable=True)
    )

    def __repr__(self) -> str:
        return (
            f"<Account(phone={self.phone}, "
            f"status={self.status.value})>"
        )