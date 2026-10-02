"""Filter: User is superadmin."""

from aiogram.filters import BaseFilter
from aiogram.types import (
    CallbackQuery, Message
)

from bot.database.engine import get_session
from bot.database.repositories import (
    OwnerRepository
)


class IsSuperadmin(BaseFilter):
    """
    Filter that passes only for
    superadmin users.
    """

    async def __call__(
        self,
        event: Message | CallbackQuery
    ) -> bool:
        user = event.from_user
        if not user:
            return False

        async with get_session() as session:
            repo = OwnerRepository(session)
            return await repo.is_superadmin(
                user.id
            )