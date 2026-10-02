"""Bulk upload batch tracking."""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    BigInteger, DateTime, Enum,
    ForeignKey, Integer
)
from sqlalchemy.orm import (
    Mapped, mapped_column
)

from bot.database.base import Base


class BatchStatus(str, PyEnum):
    """Bulk batch status."""
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    CANCELLED = "cancelled"


class BulkBatch(Base):
    """Bulk upload batch."""

    __tablename__ = "bulk_batches"

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True
    )
    owner_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("owners.id"),
        nullable=False
    )
    total_numbers: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
    successful: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    failed: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    skipped: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    status: Mapped[BatchStatus] = mapped_column(
        Enum(BatchStatus),
        default=BatchStatus.PENDING,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = (
        mapped_column(DateTime, nullable=True)
    )

    def __repr__(self) -> str:
        return (
            f"<BulkBatch(id={self.id}, "
            f"status={self.status.value})>"
        )