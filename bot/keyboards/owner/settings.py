"""Settings keyboards."""

from aiogram.types import InlineKeyboardMarkup

from bot.keyboards.builder import (
    blue,
    build_kb,
    green,
    red,
)


def get_settings_kb(
    settings_dict: dict,
) -> InlineKeyboardMarkup:
    """Settings toggles keyboard."""

    def toggle_btn(
        key: str,
        label: str,
        value: bool,
    ):
        emoji = "✅ ON" if value else "❌ OFF"
        text = f"{label}: {emoji}"
        cb = f"own:set_toggle:{key}"

        return (
            green(text, cb)
            if value
            else red(text, cb)
        )

    rows = [
        [
            toggle_btn(
                "low_stock_alert",
                "🔔 Low Stock Alert",
                settings_dict.get(
                    "low_stock_alert", True
                ),
            )
        ],
        [
            toggle_btn(
                "session_check_enabled",
                "📊 Session Checker",
                settings_dict.get(
                    "session_check_enabled", True
                ),
            )
        ],
        [
            toggle_btn(
                "sale_notifications",
                "💰 Sale Notifs",
                settings_dict.get(
                    "sale_notifications", True
                ),
            )
        ],
        [
            toggle_btn(
                "daily_report",
                "📊 Daily Report",
                settings_dict.get(
                    "daily_report", True
                ),
            )
        ],
        [
            toggle_btn(
                "balance_req_notif",
                "💳 Balance Req Notif",
                settings_dict.get(
                    "balance_req_notif", True
                ),
            )
        ],
        [
            toggle_btn(
                "new_user_notif",
                "🆕 New User Notif",
                settings_dict.get(
                    "new_user_notif", False
                ),
            )
        ],
        [
            toggle_btn(
                "auto_2fa",
                "🛡️ Auto-2FA",
                settings_dict.get(
                    "auto_2fa", True
                ),
            )
        ],
        [
            blue(
                "📝 Low Stock Threshold",
                "own:set_threshold",
            )
        ],
        [
            blue(
                "💳 Payment Settings",
                "own:payment_settings",
            )
        ],
        [
            blue(
                "👤 Support Username",
                "own:set_support_username",
            )
        ],
        [
            blue(
                "🔙 Dashboard",
                "own:dashboard",
            )
        ],
    ]

    return build_kb(rows)


def get_payment_settings_kb():
    """Payment settings keyboard (USDT only — no UPI)."""

    rows = [
        [
            blue(
                "💲 Set USDT Address",
                "own:set_usdt",
            )
        ],
        [
            blue(
                "⬇️ Set Min Deposit (USD)",
                "own:set_min_dep",
            )
        ],
        [
            blue(
                "⬆️ Set Max Deposit (USD)",
                "own:set_max_dep",
            )
        ],
        [
            blue("🔙 Back", "own:settings")
        ],
    ]

    return build_kb(rows)