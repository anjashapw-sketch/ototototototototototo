"""
Auth middleware.
Auto-registers users in database.
"""

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from bot.database.engine import get_session
from bot.database.repositories import (
    UserRepository
)


class AuthMiddleware(BaseMiddleware):
    """
    Auto-register users on first interaction.
    Injects 'db_user' into handler data.
    """

    async def __call__(
        self,
        handler: Callable[
            [TelegramObject, Dict[str, Any]],
            Awaitable[Any]
        ],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        tg_user = event.from_user
        if not tg_user:
            return await handler(event, data)

        # Skip bots
        if tg_user.is_bot:
            return await handler(event, data)

        async with get_session() as session:
            repo = UserRepository(session)
            db_user = await repo.get_or_create(
                telegram_id=tg_user.id,
                username=tg_user.username,
                first_name=tg_user.first_name
            )
            # Detach from session for use later
            data["db_user_id"] = db_user.id
            data["db_user_balance"] = (
                db_user.wallet_balance
            )
            data["db_user_lang"] = (
                db_user.language_code
            )
            data["db_user_banned"] = (
                db_user.is_banned
            )

        return await handler(event, data)