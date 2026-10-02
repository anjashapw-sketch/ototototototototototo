"""Account repository — stock management."""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import (
    Account,
    AccountStatus,
)


class AccountRepository:
    """Repository for Account operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(
        self, acc_id: int
    ) -> Optional[Account]:
        """Get account by ID."""
        result = await self.session.execute(
            select(Account).where(
                Account.id == acc_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_phone(
        self, phone: str
    ) -> Optional[Account]:
        """Get account by phone (any status)."""
        result = await self.session.execute(
            select(Account).where(
                Account.phone == phone
            )
        )
        return result.scalar_one_or_none()

    async def get_active_by_phone(
        self, phone: str
    ) -> Optional[Account]:
        """
        Get account by phone — only if IN_STOCK
        and session alive.
        Sold/dead accounts return None
        so they can be re-added.
        """
        result = await self.session.execute(
            select(Account).where(
                and_(
                    Account.phone == phone,
                    Account.status ==
                    AccountStatus.IN_STOCK,
                    Account.session_alive == True,
                )
            )
        )
        return result.scalar_one_or_none()

    async def delete_old_record(
        self, phone: str
    ) -> bool:
        """
        Delete old sold/dead account record
        so the phone can be re-added.
        """
        from sqlalchemy import delete

        result = await self.session.execute(
            delete(Account).where(
                Account.phone == phone
            )
        )
        await self.session.flush()
        return result.rowcount > 0

    async def create(
        self,
        phone: str,
        country_code: str,
        country_name: str,
        session_string: str,
        twofa_password: str,
        price: Decimal,
        added_by: int,
        device_fingerprint: Optional[str] = None,
    ) -> Account:
        """Create new account in stock."""
        account = Account(
            phone=phone,
            country_code=country_code,
            country_name=country_name,
            session_string=session_string,
            twofa_password=twofa_password,
            price=price,
            added_by=added_by,
            device_fingerprint=device_fingerprint,
        )
        self.session.add(account)
        await self.session.flush()
        return account

    async def get_available_by_country(
        self, country_code: str
    ) -> Optional[Account]:
        """Get one available account for country."""
        result = await self.session.execute(
            select(Account)
            .where(
                and_(
                    Account.country_code ==
                    country_code,
                    Account.status ==
                    AccountStatus.IN_STOCK,
                    Account.session_alive == True,
                )
            )
            .order_by(Account.added_date)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def mark_as_sold(
        self,
        acc_id: int,
        sold_to: int,
    ) -> None:
        """Mark account as sold to user."""
        await self.session.execute(
            update(Account)
            .where(Account.id == acc_id)
            .values(
                status=AccountStatus.SOLD,
                sold_to=sold_to,
                sold_date=datetime.utcnow(),
            )
        )

    async def mark_session_dead(
        self, acc_id: int
    ) -> None:
        """Mark session as dead."""
        await self.session.execute(
            update(Account)
            .where(Account.id == acc_id)
            .values(session_alive=False)
        )

    async def get_stock_by_country(
        self,
    ) -> List[Tuple[str, str, int]]:
        """Get stock count by country."""
        result = await self.session.execute(
            select(
                Account.country_code,
                Account.country_name,
                func.count(Account.id),
            )
            .where(
                and_(
                    Account.status ==
                    AccountStatus.IN_STOCK,
                    Account.session_alive == True,
                )
            )
            .group_by(
                Account.country_code,
                Account.country_name,
            )
            .order_by(
                func.count(Account.id).desc()
            )
        )
        return list(result.all())

    async def get_user_accounts(
        self, user_id: int
    ) -> List[Account]:
        """Get all accounts purchased by user."""
        result = await self.session.execute(
            select(Account)
            .where(Account.sold_to == user_id)
            .order_by(Account.sold_date.desc())
        )
        return list(result.scalars().all())

    async def count_in_stock(self) -> int:
        """Total accounts in stock."""
        result = await self.session.execute(
            select(func.count(Account.id)).where(
                Account.status ==
                AccountStatus.IN_STOCK
            )
        )
        return result.scalar() or 0

    async def count_sold(self) -> int:
        """Total accounts sold."""
        result = await self.session.execute(
            select(func.count(Account.id)).where(
                Account.status ==
                AccountStatus.SOLD
            )
        )
        return result.scalar() or 0

    async def count_dead_sessions(self) -> int:
        """Count dead session accounts."""
        result = await self.session.execute(
            select(func.count(Account.id)).where(
                and_(
                    Account.status ==
                    AccountStatus.IN_STOCK,
                    Account.session_alive == False,
                )
            )
        )
        return result.scalar() or 0

    async def get_all_alive_sessions(
        self,
    ) -> List[Account]:
        """Get all in-stock alive sessions."""
        result = await self.session.execute(
            select(Account).where(
                and_(
                    Account.status ==
                    AccountStatus.IN_STOCK,
                    Account.session_alive == True,
                )
            )
        )
        return list(result.scalars().all())

    async def get_sold_history(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Account]:
        """Get sold accounts (paginated)."""
        result = await self.session.execute(
            select(Account)
            .where(
                Account.status ==
                AccountStatus.SOLD
            )
            .order_by(Account.sold_date.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def delete(
        self, acc_id: int
    ) -> bool:
        """Delete account permanently."""
        from sqlalchemy import delete

        result = await self.session.execute(
            delete(Account).where(
                Account.id == acc_id
            )
        )
        return result.rowcount > 0