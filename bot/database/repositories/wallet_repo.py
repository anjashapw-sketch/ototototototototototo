"""Wallet request repository."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.wallet_request import (
    PaymentMethod,
    WalletRequest,
    WalletRequestStatus,
)


class WalletRequestRepository:
    """Repository for wallet top-up requests."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CREATE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def create(
        self,
        user_id: int,
        amount_inr: Decimal,
        payment_method: PaymentMethod,
        amount_usdt: Optional[Decimal] = None,
        usdt_rate: Optional[Decimal] = None,
        screenshot_file_id: Optional[str] = None,
        utr_id: Optional[str] = None,
    ) -> WalletRequest:
        """Create a new wallet request."""

        req = WalletRequest(
            user_id=user_id,
            amount_inr=amount_inr,
            amount_usdt=amount_usdt,
            usdt_rate=usdt_rate,
            payment_method=payment_method,
            screenshot_file_id=screenshot_file_id,
            utr_id=utr_id,
            status=WalletRequestStatus.PENDING,
        )

        self.session.add(req)
        await self.session.flush()
        return req

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # GETTERS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def get_by_id(
        self,
        request_id: int,
    ) -> Optional[WalletRequest]:
        """Get request by ID."""

        result = await self.session.execute(
            select(WalletRequest).where(
                WalletRequest.id == request_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_fam_order_id(
        self,
        order_id: str,
    ) -> Optional[WalletRequest]:
        """Get request by FamGateway order ID."""

        result = await self.session.execute(
            select(WalletRequest).where(
                WalletRequest.fam_order_id == order_id
            )
        )
        return result.scalar_one_or_none()

    async def get_pending(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> list[WalletRequest]:
        """
        Get all pending MANUAL requests.
        (FamGateway auto-orders excluded — they show in
         get_pending_fam_orders instead.)
        """

        result = await self.session.execute(
            select(WalletRequest)
            .where(
                WalletRequest.status
                == WalletRequestStatus.PENDING,
                WalletRequest.payment_method
                != PaymentMethod.FAMGATEWAY,
            )
            .order_by(WalletRequest.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_pending_fam_orders(
        self,
        limit: int = 50,
    ) -> list[WalletRequest]:
        """Get active FamGateway orders for polling."""

        result = await self.session.execute(
            select(WalletRequest)
            .where(
                WalletRequest.status
                == WalletRequestStatus.PENDING,
                WalletRequest.payment_method
                == PaymentMethod.FAMGATEWAY,
                WalletRequest.fam_order_id.isnot(None),
            )
            .order_by(WalletRequest.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_user_requests(
        self,
        user_id: int,
        limit: int = 10,
    ) -> list[WalletRequest]:
        """Get requests for a specific user."""

        result = await self.session.execute(
            select(WalletRequest)
            .where(WalletRequest.user_id == user_id)
            .order_by(WalletRequest.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_pending_count(self) -> int:
        """Count pending requests (all types)."""

        result = await self.session.execute(
            select(func.count()).where(
                WalletRequest.status
                == WalletRequestStatus.PENDING
            )
        )
        return result.scalar() or 0

    async def get_today_auto_approved_amount(
        self,
        user_id: int,
    ) -> float:
        """
        Total amount auto-approved for a user today.
        Used for daily auto-approve limit check.
        """

        today_start = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        result = await self.session.execute(
            select(
                func.coalesce(
                    func.sum(WalletRequest.amount_inr), 0
                )
            ).where(
                WalletRequest.user_id == user_id,
                WalletRequest.auto_verified == True,  # noqa
                WalletRequest.created_at >= today_start,
            )
        )
        return float(result.scalar() or 0)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STATUS UPDATES
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def approve(
        self,
        request_id: int,
        processed_by: int,
        admin_note: Optional[str] = None,
    ) -> Optional[WalletRequest]:
        """Approve a wallet request."""

        await self.session.execute(
            update(WalletRequest)
            .where(WalletRequest.id == request_id)
            .values(
                status=WalletRequestStatus.APPROVED,
                processed_by=processed_by,
                admin_note=admin_note,
                approved_at=datetime.utcnow(),
            )
        )
        await self.session.flush()
        return await self.get_by_id(request_id)

    async def reject(
        self,
        request_id: int,
        processed_by: int,
        admin_note: Optional[str] = None,
    ) -> Optional[WalletRequest]:
        """Reject a wallet request."""

        await self.session.execute(
            update(WalletRequest)
            .where(WalletRequest.id == request_id)
            .values(
                status=WalletRequestStatus.REJECTED,
                processed_by=processed_by,
                admin_note=admin_note,
            )
        )
        await self.session.flush()
        return await self.get_by_id(request_id)

    async def expire_stale_fam_orders(
        self,
        minutes: int = 5,
    ) -> int:
        """
        Mark FamGateway orders as EXPIRED if older than
        `minutes`. Returns count of expired orders.
        """

        cutoff = datetime.utcnow() - timedelta(minutes=minutes)

        result = await self.session.execute(
            update(WalletRequest)
            .where(
                WalletRequest.payment_method
                == PaymentMethod.FAMGATEWAY,
                WalletRequest.status
                == WalletRequestStatus.PENDING,
                WalletRequest.created_at < cutoff,
            )
            .values(status=WalletRequestStatus.EXPIRED)
        )
        await self.session.flush()
        return result.rowcount or 0

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # VALIDATION
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def has_pending(
        self,
        user_id: int,
    ) -> bool:
        """Check if user has a pending request."""

        result = await self.session.execute(
            select(func.count()).where(
                WalletRequest.user_id == user_id,
                WalletRequest.status
                == WalletRequestStatus.PENDING,
            )
        )
        return (result.scalar() or 0) > 0