"""User wallet keyboards."""

from aiogram.types import InlineKeyboardMarkup

from bot.keyboards.builder import (
    blue, build_kb, green, red
)
from bot.locales.i18n import i18n


def get_wallet_kb(
    lang: str = "en",
) -> InlineKeyboardMarkup:
    """Main wallet screen keyboard."""

    return build_kb([
        [
            green(
                "➕ Add Balance",
                "wallet:deposit",
            )
        ],
        [
            blue("🔄 Refresh", "wallet:view")
        ],
        [
            blue(
                i18n.get("btn_back_menu", lang),
                "menu:main",
            )
        ],
    ])


def get_cancel_kb() -> InlineKeyboardMarkup:
    """Simple cancel keyboard."""
    return build_kb([
        [
            red(
                "❌ Cancel",
                "wallet:cancel_request",
            )
        ]
    ])


def get_request_cancel_kb(
    lang: str = "en",
) -> InlineKeyboardMarkup:
    """Legacy cancel keyboard."""
    return build_kb([
        [
            red(
                i18n.get("btn_cancel", lang),
                "wallet:cancel_request",
            )
        ]
    ])