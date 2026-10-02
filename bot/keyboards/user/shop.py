"""Shop keyboards."""

from typing import List, Tuple

from aiogram.types import InlineKeyboardMarkup

from bot.keyboards.builder import (
    blue, build_kb
)
from bot.locales.i18n import i18n
from bot.utils.flag_emoji import get_flag


def get_countries_kb(
    countries: List[Tuple[str, str, int]],
    lang: str = "en"
) -> InlineKeyboardMarkup:
    """
    Build country selection keyboard.

    Args:
        countries: List of (code, name, count)
        lang: User language

    Returns:
        InlineKeyboardMarkup (2 per row)
    """
    rows = []
    row = []

    for code, name, count in countries:
        flag = get_flag(code)
        text = f"{flag} {name} ({count})"
        row.append(
            blue(text, f"shop:country:{code}")
        )

        if len(row) == 2:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    # Back button
    rows.append([
        blue(
            i18n.get("btn_back_menu", lang),
            "menu:main"
        )
    ])

    return build_kb(rows)


def get_country_details_kb(
    country_code: str,
    stock: int,
    lang: str = "en"
) -> InlineKeyboardMarkup:
    """
    Build country details keyboard with
    buy options.
    """
    rows = []

    if stock > 0:
        from bot.keyboards.builder import green
        rows.append([
            green(
                i18n.get("btn_buy_one", lang),
                f"shop:buy:{country_code}"
            )
        ])

    rows.append([
        blue(
            i18n.get("btn_back_shop", lang),
            "shop:list"
        )
    ])

    return build_kb(rows)