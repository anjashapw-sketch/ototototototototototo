"""Stats repository — analytics queries."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import (
    Account, AccountStatus, User
)


class StatsRepository:
    """Repository for analytics."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_revenue_in_period(
        self, days: int
    ) -> Decimal:
        """Get total revenue in last N days."""
        since = (
            datetime.utcnow() -
            timedelta(days=days)
        )
        result = await self.session.execute(
            select(func.sum(Account.price))
            .where(
                and_(
                    Account.status ==
                    AccountStatus.SOLD,
                    Account.sold_date >= since
                )
            )
        )
        return result.scalar() or Decimal("0.00")

    async def get_sold_count_in_period(
        self, days: int
    ) -> int:
        """Get sold count in last N days."""
        since = (
            datetime.utcnow() -
            timedelta(days=days)
        )
        result = await self.session.execute(
            select(func.count(Account.id))
            .where(
                and_(
                    Account.status ==
                    AccountStatus.SOLD,
                    Account.sold_date >= since
                )
            )
        )
        return result.scalar() or 0

    async def get_new_users_in_period(
        self, days: int
    ) -> int:
        """Get new users in last N days."""
        since = (
            datetime.utcnow() -
            timedelta(days=days)
        )
        result = await self.session.execute(
            select(func.count(User.id))
            .where(User.joined_date >= since)
        )
        return result.scalar() or 0

    async def get_top_countries(
        self, limit: int = 5
    ) -> List[Tuple[str, str, int]]:
        """Get top selling countries."""
        result = await self.session.execute(
            select(
                Account.country_code,
                Account.country_name,
                func.count(Account.id)
            )
            .where(
                Account.status ==
                AccountStatus.SOLD
            )
            .group_by(
                Account.country_code,
                Account.country_name
            )
            .order_by(
                func.count(Account.id).desc()
            )
            .limit(limit)
        )
        return list(result.all())

    async def get_dashboard_stats(
        self
    ) -> Dict[str, int]:
        """Get all dashboard stats."""
        from bot.database.repositories \
            .account_repo import AccountRepository
        from bot.database.repositories \
            .user_repo import UserRepository

        acc_repo = AccountRepository(self.session)
        user_repo = UserRepository(self.session)

        return {
            "total_stock": (
                await acc_repo.count_in_stock()
            ),
            "dead_sessions": (
                await acc_repo
                .count_dead_sessions()
            ),
            "total_users": (
                await user_repo.count_all()
            ),
            "banned_users": (
                await user_repo.count_banned()
            ),
            "total_sold": (
                await acc_repo.count_sold()
            ),
            "today_sold": (
                await self
                .get_sold_count_in_period(1)
            )
        }