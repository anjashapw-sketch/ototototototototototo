"""User repository — DB queries for users."""

from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import User


class UserRepository:
    """Repository for User operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_telegram_id(
        self, telegram_id: int
    ) -> Optional[User]:
        """Get user by Telegram ID."""
        result = await self.session.execute(
            select(User).where(
                User.telegram_id == telegram_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(
        self, user_id: int
    ) -> Optional[User]:
        """Get user by internal ID."""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        language_code: str = "en"
    ) -> User:
        """Create new user."""
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            language_code=language_code
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def get_or_create(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None
    ) -> User:
        """Get existing or create new user."""
        user = await self.get_by_telegram_id(
            telegram_id
        )
        if user is None:
            user = await self.create(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name
            )
        return user

    async def update_balance(
        self,
        user_id: int,
        amount: Decimal
    ) -> None:
        """
        Update wallet balance (add/subtract).
        Use negative amount for deduction.
        """
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                wallet_balance=(
                    User.wallet_balance + amount
                )
            )
        )

    async def set_language(
        self, user_id: int, language: str
    ) -> None:
        """Update user language."""
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(language_code=language)
        )

    async def ban(self, user_id: int) -> None:
        """Ban user."""
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(is_banned=True)
        )

    async def unban(self, user_id: int) -> None:
        """Unban user."""
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(is_banned=False)
        )

    async def get_all(
        self, limit: int = 100, offset: int = 0
    ) -> List[User]:
        """Get all users with pagination."""
        result = await self.session.execute(
            select(User)
            .order_by(User.joined_date.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_all(self) -> int:
        """Count total users."""
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count(User.id))
        )
        return result.scalar() or 0

    async def count_banned(self) -> int:
        """Count banned users."""
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count(User.id))
            .where(User.is_banned == True)
        )
        return result.scalar() or 0

    async def get_all_active_ids(
        self,
    ) -> List[int]:
        """
        Get all non-banned user Telegram IDs
        for broadcast.
        """
        result = await self.session.execute(
            select(User.telegram_id)
            .where(User.is_banned == False)
        )
        return list(result.scalars().all())