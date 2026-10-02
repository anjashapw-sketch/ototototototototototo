"""Analytics keyboards."""

from aiogram.types import InlineKeyboardMarkup

from bot.keyboards.builder import (
    blue, build_kb
)


def get_analytics_kb() -> InlineKeyboardMarkup:
    """Analytics period selector."""
    return build_kb([
        [
            blue("📅 Daily", "own:stats:1"),
            blue("📅 Weekly", "own:stats:7")
        ],
        [
            blue("📅 Monthly", "own:stats:30"),
            blue(
                "📅 All Time",
                "own:stats:all"
            )
        ],
        [
            blue("🔙 Dashboard", "own:dashboard")
        ]
    ])