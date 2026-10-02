"""Language selection keyboard."""

from aiogram.types import InlineKeyboardMarkup

from bot.keyboards.builder import (
    blue, build_kb
)
from bot.locales.i18n import i18n


def get_language_kb(
    lang: str = "en"
) -> InlineKeyboardMarkup:
    """Language picker keyboard (2 per row)."""
    languages = i18n.SUPPORTED_LANGUAGES
    rows = []
    row = []

    for code in languages:
        name = i18n.get_language_name(code)
        row.append(
            blue(name, f"lang:set:{code}")
        )
        if len(row) == 2:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    rows.append([
        blue(
            i18n.get("btn_back", lang),
            "profile:back"
        )
    ])

    return build_kb(rows)