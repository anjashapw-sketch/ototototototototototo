"""Owner dashboard keyboards."""

from aiogram.types import InlineKeyboardMarkup

from bot.keyboards.builder import (
    blue, build_kb, green
)


def get_dashboard_kb() -> InlineKeyboardMarkup:
    """Owner dashboard inline keyboard."""
    return build_kb([
        [
            green(
                "➕ Add Account",
                "own:add_acc"
            ),
            blue(
                "📊 Stock",
                "own:stock"
            )
        ],
        [
            blue(
                "👥 Users",
                "own:users"
            ),
            blue(
                "💰 Wallets",
                "own:wallets"
            )
        ],
        [
            blue(
                "📈 Analytics",
                "own:analytics"
            ),
            blue(
                "💲 Pricing",
                "own:pricing"
            )
        ],
        [
            blue(
                "🛡️ Admins",
                "own:admins"
            ),
            blue(
                "⚙️ Settings",
                "own:settings"
            )
        ],
        [
            blue(
                "🔐 Force Sub",
                "own:fsub"
            ),
            blue(
                "📋 Sold History",
                "own:sold"
            )
        ]
    ])