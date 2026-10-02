"""Owner main menu (reply keyboard)."""

from aiogram.types import ReplyKeyboardMarkup

from bot.keyboards.builder import build_reply_kb


# ━━━ OWNER MENU LABELS ━━━
OWNER_MENU = {
    "dashboard": "👑 Dashboard",
    "add_account": "➕ Add Account",
    "bulk_upload": "📦 Bulk Upload",
    "stock": "📊 Stock",
    "users": "👥 Users",
    "wallets": "💰 Wallets",
    "admins": "🛡️ Admins",
    "pricing": "💲 Pricing",
    "analytics": "📈 Analytics",
    "settings": "⚙️ Settings",
    "notifications": "🔔 Notifications",
    "force_sub": "🔐 Force Sub",
    "sold_history": "📋 Sold History",
    "broadcast": "📢 Broadcast",
    "user_mode": "🔄 User Mode"
}


def get_owner_main_menu() -> ReplyKeyboardMarkup:
    """Build owner main menu keyboard."""
    return build_reply_kb(
        rows=[
            [
                OWNER_MENU["dashboard"],
                OWNER_MENU["stock"]
            ],
            [
                OWNER_MENU["add_account"],
                OWNER_MENU["bulk_upload"]
            ],
            [
                OWNER_MENU["users"],
                OWNER_MENU["wallets"]
            ],
            [
                OWNER_MENU["pricing"],
                OWNER_MENU["analytics"]
            ],
            [
                OWNER_MENU["admins"],
                OWNER_MENU["settings"]
            ],
            [
                OWNER_MENU["notifications"],
                OWNER_MENU["force_sub"]
            ],
            [
                OWNER_MENU["sold_history"],
                OWNER_MENU["broadcast"]
            ],
            [
                OWNER_MENU["user_mode"]
            ]
        ]
    )