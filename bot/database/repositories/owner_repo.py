"""Owner repository — admin DB queries."""

from typing import List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Owner
from bot.database.models.owner import OwnerRole


class OwnerRepository:
    """Repository for Owner operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_telegram_id(
        self, telegram_id: int
    ) -> Optional[Owner]:
        """Get owner by Telegram ID."""
        result = await self.session.execute(
            select(Owner).where(
                Owner.telegram_id == telegram_id
            )
        )
        return result.scalar_one_or_none()

    async def is_owner(
        self, telegram_id: int
    ) -> bool:
        """Check if user is owner."""
        owner = await self.get_by_telegram_id(
            telegram_id
        )
        return owner is not None

    async def is_superadmin(
        self, telegram_id: int
    ) -> bool:
        """Check if user is superadmin."""
        owner = await self.get_by_telegram_id(
            telegram_id
        )
        return (
            owner is not None
            and owner.role == OwnerRole.SUPERADMIN
        )

    async def create(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        role: OwnerRole = OwnerRole.ADMIN
    ) -> Owner:
        """Create new owner."""
        owner = Owner(
            telegram_id=telegram_id,
            username=username,
            role=role
        )
        self.session.add(owner)
        await self.session.flush()
        return owner

    async def delete(
        self, telegram_id: int
    ) -> bool:
        """Remove owner."""
        result = await self.session.execute(
            delete(Owner).where(
                Owner.telegram_id == telegram_id
            )
        )
        return result.rowcount > 0

    async def get_all(self) -> List[Owner]:
        """Get all owners."""
        result = await self.session.execute(
            select(Owner).order_by(
                Owner.added_date
            )
        )
        return list(result.scalars().all())

    async def get_all_admins(self) -> List[Owner]:
        """Get only admin role owners."""
        result = await self.session.execute(
            select(Owner).where(
                Owner.role == OwnerRole.ADMIN
            )
        )
        return list(result.scalars().all())

    async def get_all_superadmins(
        self
    ) -> List[Owner]:
        """Get only superadmin owners."""
        result = await self.session.execute(
            select(Owner).where(
                Owner.role == OwnerRole.SUPERADMIN
            )
        )
        return list(result.scalars().all())