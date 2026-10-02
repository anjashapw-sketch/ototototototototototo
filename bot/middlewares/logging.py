"""Logging middleware."""

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import (
    CallbackQuery, Message, TelegramObject
)

from bot.utils.logger import log


class LoggingMiddleware(BaseMiddleware):
    """Logs all incoming updates."""

    async def __call__(
        self,
        handler: Callable[
            [TelegramObject, Dict[str, Any]],
            Awaitable[Any]
        ],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = event.from_user
        user_info = (
            f"@{user.username}({user.id})"
            if user else "Unknown"
        )

        if isinstance(event, Message):
            text = (event.text or "")[:50]
            log.debug(
                f"📨 MSG from {user_info}: "
                f"{text}"
            )
        elif isinstance(event, CallbackQuery):
            log.debug(
                f"🔘 CB from {user_info}: "
                f"{event.data}"
            )

        return await handler(event, data)