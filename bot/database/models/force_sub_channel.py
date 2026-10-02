"""Force subscription channel model."""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, DateTime,
    Enum, ForeignKey, String, Text
)
from sqlalchemy.orm import (
    Mapped, mapped_column
)

from bot.database.base import Base


class ChannelType(str, PyEnum):
    """Channel type enum."""
    PUBLIC = "public"
    PRIVATE = "private"


class ForceSubChannel(Base):
    """Force subscription channel."""

    __tablename__ = "force_sub_channels"

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(
        String(128), nullable=False
    )
    type: Mapped[ChannelType] = mapped_column(
        Enum(ChannelType), nullable=False
    )
    chat_id: Mapped[int] = mapped_column(
        BigInteger, unique=True,
        nullable=False, index=True
    )
    username: Mapped[Optional[str]] = (
        mapped_column(String(64), nullable=True)
    )
    invite_link: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    is_bot_admin: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
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

    def __repr__(self) -> str:
        return (
            f"<ForceSubChannel("
            f"name={self.name}, "
            f"type={self.type.value})>"
        )