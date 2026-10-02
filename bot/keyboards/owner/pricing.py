"""Pricing keyboards."""

from typing import List

from aiogram.types import InlineKeyboardMarkup

from bot.database.models import Pricing
from bot.keyboards.builder import (
    blue, build_kb
)
from bot.utils.flag_emoji import get_flag


def get_pricing_overview_kb(
    prices: List[Pricing]
) -> InlineKeyboardMarkup:
    """Pricing list keyboard."""
    rows = []

    for p in prices:
        flag = (
            "🌍" if p.country_code == "DEFAULT"
            else get_flag(p.country_code)
        )
        text = (
            f"{flag} {p.country_name} "
            f"→ ₹{p.price}"
        )
        rows.append([
            blue(
                text,
                f"own:price_edit:{p.country_code}"
            )
        ])

    rows.append([
        blue(
            "✏️ Set Country Price",
            "own:price_set"
        )
    ])
    rows.append([
        blue(
            "✏️ Set Default Price",
            "own:price_default"
        )
    ])
    rows.append([
        blue("🔙 Dashboard", "own:dashboard")
    ])

    return build_kb(rows)