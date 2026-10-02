"""
SQLAlchemy declarative base.
All models inherit from this.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column
)


class Base(DeclarativeBase):
    """
    Base class for all ORM models.
    Provides common fields & utilities.
    """

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        return {
            col.name: getattr(self, col.name)
            for col in self.__table__.columns
        }

    def __repr__(self) -> str:
        """Readable representation."""
        cls = self.__class__.__name__
        pk = getattr(self, "id", "N/A")
        return f"<{cls}(id={pk})>"


class TimestampMixin:
    """
    Mixin for automatic timestamps.
    Adds created_at field.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )