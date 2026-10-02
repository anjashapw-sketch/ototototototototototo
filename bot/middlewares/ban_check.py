"""Ban check middleware."""

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import (
    CallbackQuery, Message, TelegramObject
)

from bot.locales.i18n import i18n


class BanCheckMiddleware(BaseMiddleware):
    """
    Block all interactions from banned users.
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
        is_banned = data.get(
            "db_user_banned", False
        )

        if is_banned:
            lang = data.get(
                "db_user_lang", "en"
            )
            msg = i18n.get(
                "error_banned", lang=lang
            )

            try:
                if isinstance(event, Message):
                    await event.answer(msg)
                elif isinstance(
                    event, CallbackQuery
                ):
                    await event.answer(
                        msg, show_alert=True
                    )
            except Exception:
                pass

            return  # Block handler

        return await handler(event, data)