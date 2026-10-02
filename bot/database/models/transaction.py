"""Transaction model — wallet ops log."""

from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    BigInteger, DateTime, Enum,
    ForeignKey, Numeric, Text
)
from sqlalchemy.orm import (
    Mapped, mapped_column
)

from bot.database.base import Base


class TransactionType(str, PyEnum):
    """Transaction type enum."""
    CREDIT = "credit"
    DEBIT = "debit"


class Transaction(Base):
    """Wallet transaction log."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False, index=True
    )
    type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    description: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    done_by: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("owners.id"),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False, index=True
    )

    def __repr__(self) -> str:
        return (
            f"<Transaction("
            f"user={self.user_id}, "
            f"type={self.type.value}, "
            f"amount={self.amount})>"
        )