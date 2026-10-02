"""
Wallet service.
Handles balance ops and transactions atomically.
"""

from decimal import Decimal
from typing import Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import TransactionType
from bot.database.models.wallet_request import (
    PaymentMethod,
    WalletRequest,
    WalletRequestStatus,
)
from bot.database.repositories import (
    TransactionRepository,
    UserRepository,
)
from bot.database.repositories.wallet_repo import (
    WalletRequestRepository,
)
from bot.utils.logger import log


class WalletService:
    """Service for wallet operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.txn_repo = TransactionRepository(session)
        self.req_repo = WalletRequestRepository(session)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # BALANCE OPS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def credit(
        self,
        user_id: int,
        amount: Decimal,
        description: str,
        done_by: Optional[int] = None,
    ) -> Tuple[bool, str]:
        """
        Add balance to user wallet.

        Returns:
            (success, message)
        """
        if amount <= 0:
            return False, "Invalid amount"

        try:
            await self.user_repo.update_balance(
                user_id, amount
            )
            await self.txn_repo.create(
                user_id=user_id,
                type=TransactionType.CREDIT,
                amount=amount,
                description=description,
                done_by=done_by,
            )
            log.info(
                f"💰 Credit: user={user_id}, "
                f"amount={amount}"
            )
            return True, "Credited"

        except Exception as e:
            log.error(f"❌ Credit failed: {e}")
            return False, str(e)

    async def debit(
        self,
        user_id: int,
        amount: Decimal,
        description: str,
    ) -> Tuple[bool, str]:
        """
        Deduct from wallet with balance check.

        Returns:
            (success, message)
        """
        if amount <= 0:
            return False, "Invalid amount"

        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return False, "User not found"

        if user.wallet_balance < amount:
            return False, "Insufficient balance"

        try:
            await self.user_repo.update_balance(
                user_id, -amount
            )
            await self.txn_repo.create(
                user_id=user_id,
                type=TransactionType.DEBIT,
                amount=amount,
                description=description,
            )
            log.info(
                f"💸 Debit: user={user_id}, "
                f"amount={amount}"
            )
            return True, "Debited"

        except Exception as e:
            log.error(f"❌ Debit failed: {e}")
            return False, str(e)

    async def get_balance(
        self,
        user_id: int,
    ) -> Decimal:
        """Get current wallet balance."""

        user = await self.user_repo.get_by_id(user_id)
        return (
            user.wallet_balance
            if user
            else Decimal("0.00")
        )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # DEPOSIT REQUEST OPS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def approve_request(
        self,
        request_id: int,
        approved_by: int,
        admin_note: Optional[str] = None,
    ) -> Tuple[bool, str, Optional[WalletRequest]]:
        """
        Approve deposit request and credit wallet.

        Returns:
            (success, message, request)
        """
        req = await self.req_repo.get_by_id(request_id)

        if not req:
            return False, "Request not found", None

        if req.status != WalletRequestStatus.PENDING:
            return (
                False,
                f"Already {req.status.value}",
                req,
            )

        amount = Decimal(str(req.amount_inr))
        method = req.payment_method.value.upper()

        success, msg = await self.credit(
            user_id=req.user_id,
            amount=amount,
            description=f"Deposit via {method} approved",
            done_by=approved_by,
        )

        if not success:
            return False, msg, req

        req = await self.req_repo.approve(
            request_id=request_id,
            processed_by=approved_by,
            admin_note=admin_note,
        )

        log.info(
            f"✅ Deposit approved: req={request_id}, "
            f"user={req.user_id}, amount={amount}"
        )
        return True, "Approved", req

    async def reject_request(
        self,
        request_id: int,
        rejected_by: int,
        admin_note: Optional[str] = None,
    ) -> Tuple[bool, str, Optional[WalletRequest]]:
        """
        Reject deposit request.

        Returns:
            (success, message, request)
        """
        req = await self.req_repo.get_by_id(request_id)

        if not req:
            return False, "Request not found", None

        if req.status != WalletRequestStatus.PENDING:
            return (
                False,
                f"Already {req.status.value}",
                req,
            )

        # Use processed_by (not rejected_by)
        req = await self.req_repo.reject(
            request_id=request_id,
            processed_by=rejected_by,
            admin_note=admin_note,
        )

        log.info(
            f"❌ Deposit rejected: req={request_id}, "
            f"user={req.user_id}"
        )
        return True, "Rejected", req