"""Admin management keyboards."""

from typing import List

from aiogram.types import InlineKeyboardMarkup

from bot.database.models import Owner
from bot.keyboards.builder import (
    blue, build_kb, green, red
)


def get_admins_overview_kb(
    is_superadmin: bool = False
) -> InlineKeyboardMarkup:
    """Admin management overview."""
    rows = []

    if is_superadmin:
        rows.append([
            green("➕ Add Admin", "own:admin_add")
        ])
        rows.append([
            red(
                "❌ Remove Admin",
                "own:admin_rm_list"
            )
        ])

    rows.append([
        blue("🔙 Dashboard", "own:dashboard")
    ])

    return build_kb(rows)


def get_remove_admin_list_kb(
    admins: List[Owner]
) -> InlineKeyboardMarkup:
    """List of admins to remove."""
    rows = []
    for admin in admins:
        name = (
            f"@{admin.username}"
            if admin.username
            else str(admin.telegram_id)
        )
        rows.append([
            red(
                f"❌ {name}",
                f"own:admin_rm:{admin.telegram_id}"
            )
        ])

    rows.append([
        blue("🔙 Back", "own:admins")
    ])

    return build_kb(rows)