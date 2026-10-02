"""Language injection middleware."""

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from bot.config import settings
from bot.locales.i18n import i18n


class LanguageMiddleware(BaseMiddleware):
    """
    Inject user language into handler data.
    Falls back to Telegram language or default.
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
        # Already injected by auth middleware
        lang = data.get("db_user_lang")

        if not lang:
            tg_user = event.from_user
            if tg_user and tg_user.language_code:
                lang_code = (
                    tg_user.language_code[:2]
                    .lower()
                )
                if i18n.is_supported(lang_code):
                    lang = lang_code

        if not lang:
            lang = settings.default_language

        data["lang"] = lang

        return await handler(event, data)