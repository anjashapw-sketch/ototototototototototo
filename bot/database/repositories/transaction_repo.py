"""Transaction repository."""

from decimal import Decimal
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import (
    Transaction, TransactionType
)


class TransactionRepository:
    """Repository for Transaction operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: int,
        type: TransactionType,
        amount: Decimal,
        description: str,
        done_by: Optional[int] = None
    ) -> Transaction:
        """Log a new transaction."""
        txn = Transaction(
            user_id=user_id,
            type=type,
            amount=amount,
            description=description,
            done_by=done_by
        )
        self.session.add(txn)
        await self.session.flush()
        return txn

    async def get_user_transactions(
        self,
        user_id: int,
        limit: int = 20
    ) -> List[Transaction]:
        """Get user's transaction history."""
        result = await self.session.execute(
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(
                Transaction.created_at.desc()
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_total_spent(
        self, user_id: int
    ) -> Decimal:
        """Total amount spent by user."""
        result = await self.session.execute(
            select(func.sum(Transaction.amount))
            .where(
                Transaction.user_id == user_id,
                Transaction.type ==
                TransactionType.DEBIT
            )
        )
        return result.scalar() or Decimal("0.00")