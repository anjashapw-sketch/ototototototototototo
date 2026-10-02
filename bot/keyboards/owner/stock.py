"""Stock management keyboards."""

from typing import List, Tuple

from aiogram.types import InlineKeyboardMarkup

from bot.keyboards.builder import (
    blue, build_kb, red
)
from bot.utils.flag_emoji import get_flag


def get_stock_overview_kb(
    countries: List[Tuple[str, str, int]]
) -> InlineKeyboardMarkup:
    """Stock overview by country."""
    rows = []
    row = []

    for code, name, count in countries:
        flag = get_flag(code)
        text = f"{flag} {name} ({count})"
        row.append(
            blue(text, f"own:stock_c:{code}")
        )
        if len(row) == 2:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    rows.append([
        blue("🔄 Refresh All", "own:stock"),
        red("❌ Dead Only", "own:stock_dead")
    ])

    rows.append([
        blue("🔙 Dashboard", "own:dashboard")
    ])

    return build_kb(rows)


def get_country_stock_kb(
    country_code: str,
    accounts: list
) -> InlineKeyboardMarkup:
    """List accounts for a country."""
    rows = []
    for acc in accounts[:20]:
        from bot.utils.formatters import (
            format_phone_masked
        )
        masked = format_phone_masked(acc.phone)
        rows.append([
            blue(
                f"📱 {masked}",
                f"own:acc_view:{acc.id}"
            )
        ])

    rows.append([
        blue("🔙 Stock", "own:stock")
    ])

    return build_kb(rows)


def get_account_view_kb(
    acc_id: int
) -> InlineKeyboardMarkup:
    """Single account view (owner)."""
    return build_kb([
        [
            blue(
                "🔄 Check Session",
                f"own:acc_check:{acc_id}"
            )
        ],
        [
            red(
                "🗑 Remove Account",
                f"own:acc_remove:{acc_id}"
            )
        ],
        [
            blue("🔙 Back", "own:stock")
        ]
    ])


def get_remove_account_confirm_kb(
    acc_id: int
) -> InlineKeyboardMarkup:
    """Confirm remove account."""
    return build_kb([
        [
            red(
                "✅ Yes, Remove",
                f"own:acc_rm_yes:{acc_id}"
            ),
            blue(
                "❌ Cancel",
                f"own:acc_view:{acc_id}"
            )
        ]
    ])