"""Purchase confirmation keyboards."""

from aiogram.types import InlineKeyboardMarkup

from bot.keyboards.builder import (
    blue, build_kb, green, red
)
from bot.locales.i18n import i18n


def get_purchase_confirm_kb(
    country_code: str,
    lang: str = "en"
) -> InlineKeyboardMarkup:
    """Purchase confirm/cancel keyboard."""
    return build_kb([
        [
            green(
                i18n.get("btn_confirm", lang),
                f"buy:confirm:{country_code}"
            ),
            red(
                i18n.get("btn_cancel", lang),
                "buy:cancel"
            )
        ]
    ])


def get_accept_view_kb(
    acc_id: int,
    lang: str = "en"
) -> InlineKeyboardMarkup:
    """Accept disclaimer & view details kb."""
    return build_kb([
        [
            green(
                i18n.get(
                    "btn_accept_view", lang
                ),
                f"acc:view:{acc_id}"
            )
        ]
    ])