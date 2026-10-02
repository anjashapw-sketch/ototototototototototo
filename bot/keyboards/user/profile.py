"""Profile keyboards."""

from aiogram.types import InlineKeyboardMarkup

from bot.keyboards.builder import (
    blue, build_kb
)
from bot.locales.i18n import i18n


def get_profile_kb(
    lang: str = "en"
) -> InlineKeyboardMarkup:
    """Profile screen keyboard."""
    return build_kb([
        [
            blue(
                i18n.get(
                    "btn_change_language", lang
                ),
                "profile:lang"
            )
        ],
        [
            blue(
                i18n.get("btn_back_menu", lang),
                "menu:main"
            )
        ]
    ])