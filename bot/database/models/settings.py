"""Settings model — key-value store."""

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import (
    Mapped, mapped_column
)

from bot.database.base import Base


class Setting(Base):
    """Bot settings key-value store."""

    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True
    )
    key: Mapped[str] = mapped_column(
        String(128), unique=True,
        nullable=False, index=True
    )
    value: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<Setting({self.key}={self.value})>"
        )