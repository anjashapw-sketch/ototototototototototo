"""
Notification toggle keyboards.
Granular control over each notif type.
"""

from aiogram.types import InlineKeyboardMarkup

from bot.keyboards.builder import (
    blue, build_kb, green, red
)


def get_notifications_kb(
    settings_dict: dict
) -> InlineKeyboardMarkup:
    """
    Build notification toggles keyboard.

    Args:
        settings_dict: Current setting values

    Returns:
        InlineKeyboardMarkup
    """

    def toggle_btn(
        key: str, label: str, value: bool
    ):
        emoji = "✅ ON" if value else "❌ OFF"
        text = f"{label}: {emoji}"
        cb = f"own:notif_toggle:{key}"
        return (
            green(text, cb) if value
            else red(text, cb)
        )

    rows = [
        [toggle_btn(
            "low_stock_alert",
            "🔔 Low Stock Alert",
            settings_dict.get(
                "low_stock_alert", True
            )
        )],
        [toggle_btn(
            "session_check_enabled",
            "💀 Session Dead Alert",
            settings_dict.get(
                "session_check_enabled", True
            )
        )],
        [toggle_btn(
            "sale_notifications",
            "💰 Sale Notifications",
            settings_dict.get(
                "sale_notifications", True
            )
        )],
        [toggle_btn(
            "daily_report",
            "📊 Daily Sales Report",
            settings_dict.get(
                "daily_report", True
            )
        )],
        [toggle_btn(
            "balance_req_notif",
            "💳 Balance Requests",
            settings_dict.get(
                "balance_req_notif", True
            )
        )],
        [toggle_btn(
            "new_user_notif",
            "🆕 New User Alerts",
            settings_dict.get(
                "new_user_notif", False
            )
        )],
        [blue(
            "🔙 Dashboard", "own:dashboard"
        )]
    ]

    return build_kb(rows)