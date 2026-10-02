"""Filter: User is admin (not superadmin)."""

from aiogram.filters import BaseFilter
from aiogram.types import (
    CallbackQuery, Message
)

from bot.database.engine import get_session
from bot.database.models.owner import OwnerRole
from bot.database.repositories import (
    OwnerRepository
)


class IsAdmin(BaseFilter):
    """
    Filter that passes if user is
    specifically an admin (not superadmin).
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
            owner = await repo.get_by_telegram_id(
                user.id
            )
            return (
                owner is not None
                and owner.role == OwnerRole.ADMIN
            )