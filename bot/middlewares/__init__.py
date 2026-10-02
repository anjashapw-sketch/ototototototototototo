"""Middlewares registration."""

from aiogram import Dispatcher

from bot.middlewares.logging import (
    LoggingMiddleware
)
from bot.middlewares.throttling import (
    ThrottlingMiddleware
)
from bot.middlewares.auth import AuthMiddleware
from bot.middlewares.ban_check import (
    BanCheckMiddleware
)
from bot.middlewares.language import (
    LanguageMiddleware
)
from bot.middlewares.force_sub import (
    ForceSubMiddleware
)


def register_all_middlewares(
    dp: Dispatcher
) -> None:
    """
    Register all middlewares in order.

    ORDER MATTERS:
    1. Logging       (log everything)
    2. Throttling    (rate limit)
    3. Auth          (register user)
    4. Ban Check     (block banned)
    5. Language      (inject lang)
    6. Force Sub     (check channels)
    """
    # Message middlewares
    dp.message.middleware(LoggingMiddleware())
    dp.message.middleware(ThrottlingMiddleware())
    dp.message.middleware(AuthMiddleware())
    dp.message.middleware(BanCheckMiddleware())
    dp.message.middleware(LanguageMiddleware())
    dp.message.middleware(ForceSubMiddleware())

    # Callback middlewares
    dp.callback_query.middleware(
        LoggingMiddleware()
    )
    dp.callback_query.middleware(
        ThrottlingMiddleware()
    )
    dp.callback_query.middleware(
        AuthMiddleware()
    )
    dp.callback_query.middleware(
        BanCheckMiddleware()
    )
    dp.callback_query.middleware(
        LanguageMiddleware()
    )
    dp.callback_query.middleware(
        ForceSubMiddleware()
    )


__all__ = [
    "register_all_middlewares",
    "LoggingMiddleware",
    "ThrottlingMiddleware",
    "AuthMiddleware",
    "BanCheckMiddleware",
    "LanguageMiddleware",
    "ForceSubMiddleware"
]