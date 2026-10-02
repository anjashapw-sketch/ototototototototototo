"""
Wallet request model.
Supports UPI (manual + FamGateway auto) and USDT BEP20.
"""

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

# ✅ FIXED: Base is at bot.database.base
from bot.database.base import Base


class PaymentMethod(str, Enum):
    UPI = "upi"
    USDT_BEP20 = "usdt_bep20"
    FAMGATEWAY = "famgateway"


class WalletRequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    AUTO_APPROVED = "auto_approved"


class WalletRequest(Base):
    """Wallet deposit request."""

    __tablename__ = "wallet_requests"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), index=True
    )

    amount_inr: Mapped[float] = mapped_column(
        Numeric(12, 2), nullable=False
    )

    payment_method: Mapped[PaymentMethod] = mapped_column(
        SAEnum(PaymentMethod), nullable=False
    )
    status: Mapped[WalletRequestStatus] = mapped_column(
        SAEnum(WalletRequestStatus),
        default=WalletRequestStatus.PENDING,
        index=True,
        nullable=False,
    )

    # Manual UPI / USDT
    utr_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    screenshot_file_id: Mapped[str | None] = mapped_column(
        String(256), nullable=True
    )
    amount_usdt: Mapped[float | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    usdt_rate: Mapped[float | None] = mapped_column(
        Numeric(12, 4), nullable=True
    )

    # Admin actions
    processed_by: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    admin_note: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # FamGateway fields
    fam_order_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True, index=True
    )
    fam_qr_url: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )
    fam_upi_intent: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )
    fam_checkout_url: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )
    fam_utr: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    fam_sender_name: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    fam_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    auto_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    user = relationship("User", back_populates="wallet_requests")