"""Throttling middleware (anti-spam)."""

import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import (
    CallbackQuery, Message, TelegramObject
)

from bot.config import settings


class ThrottlingMiddleware(BaseMiddleware):
    """
    Rate limit users to prevent spam.
    """

    def __init__(self):
        self._cache: Dict[int, float] = {}
        self._rate = settings.rate_limit_seconds

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
        if not user:
            return await handler(event, data)

        user_id = user.id
        now = time.time()
        last = self._cache.get(user_id, 0)

        if now - last < self._rate:
            # Throttled — silently ignore
            if isinstance(event, CallbackQuery):
                try:
                    await event.answer(
                        "⚠️ Slow down!",
                        show_alert=False
                    )
                except Exception:
                    pass
            return

        self._cache[user_id] = now

        # Cleanup old entries
        if len(self._cache) > 1000:
            cutoff = now - 60
            self._cache = {
                uid: t
                for uid, t in self._cache.items()
                if t > cutoff
            }

        return await handler(event, data)