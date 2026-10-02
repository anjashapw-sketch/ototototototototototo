"""Country-wise pricing model."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime, Numeric, String
)
from sqlalchemy.orm import (
    Mapped, mapped_column
)

from bot.database.base import Base


class Pricing(Base):
    """Per-country pricing."""

    __tablename__ = "pricing"

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True
    )
    country_code: Mapped[str] = mapped_column(
        String(5), unique=True,
        nullable=False, index=True
    )
    country_name: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<Pricing("
            f"{self.country_code}={self.price})>"
        )