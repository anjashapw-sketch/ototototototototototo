"""Filter: User is banned."""

from aiogram.filters import BaseFilter
from aiogram.types import (
    CallbackQuery, Message
)

from bot.database.engine import get_session
from bot.database.repositories import (
    UserRepository
)


class IsBanned(BaseFilter):
    """
    Filter that passes if user is banned.
    Used to block all interactions.
    """

    async def __call__(
        self,
        event: Message | CallbackQuery
    ) -> bool:
        user = event.from_user
        if not user:
            return False

        async with get_session() as session:
            repo = UserRepository(session)
            db_user = await repo.get_by_telegram_id(
                user.id
            )
            return (
                db_user is not None
                and db_user.is_banned
            )