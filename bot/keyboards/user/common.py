"""Common user keyboards."""

from aiogram.types import InlineKeyboardMarkup

from bot.keyboards.builder import (
    blue, build_kb
)
from bot.locales.i18n import i18n


def get_back_menu_kb(
    lang: str = "en"
) -> InlineKeyboardMarkup:
    """Simple back to menu button."""
    return build_kb([
        [
            blue(
                i18n.get("btn_back_menu", lang),
                "menu:main"
            )
        ]
    ])


def get_back_kb(
    callback_data: str = "menu:main",
    lang: str = "en"
) -> InlineKeyboardMarkup:
    """Simple back button."""
    return build_kb([
        [
            blue(
                i18n.get("btn_back", lang),
                callback_data
            )
        ]
    ])