"""User management keyboards."""

from aiogram.types import InlineKeyboardMarkup

from bot.keyboards.builder import (
    blue, build_kb, green, red
)


def get_users_overview_kb() -> InlineKeyboardMarkup:
    """User management overview."""
    return build_kb([
        [
            blue(
                "🔍 Search by ID",
                "own:user_search"
            )
        ],
        [
            blue(
                "📋 List All Users",
                "own:user_list:0"
            )
        ],
        [
            blue(
                "🚫 Banned Users",
                "own:user_banned"
            )
        ],
        [
            blue(
                "💰 Top Buyers",
                "own:user_top"
            )
        ],
        [
            blue("🔙 Dashboard", "own:dashboard")
        ]
    ])


def get_users_list_kb(
    users: list,
    page: int = 0,
    page_size: int = 10
) -> InlineKeyboardMarkup:
    """Paginated users list."""
    rows = []
    for user in users:
        name = (
            user.first_name
            or user.username
            or str(user.telegram_id)
        )
        rows.append([
            blue(
                f"👤 {name[:30]}",
                f"own:user_view:{user.id}"
            )
        ])

    nav_row = []
    if page > 0:
        nav_row.append(
            blue(
                "◀️ Prev",
                f"own:user_list:{page - 1}"
            )
        )
    if len(users) == page_size:
        nav_row.append(
            blue(
                "▶️ Next",
                f"own:user_list:{page + 1}"
            )
        )
    if nav_row:
        rows.append(nav_row)

    rows.append([
        blue("🔙 Back", "own:users")
    ])

    return build_kb(rows)


def get_user_view_kb(
    user_id: int,
    is_banned: bool = False
) -> InlineKeyboardMarkup:
    """Single user view keyboard."""
    rows = [
        [
            green(
                "💰 Add Balance",
                f"own:user_addbal:{user_id}"
            ),
            blue(
                "📦 View Accounts",
                f"own:user_accs:{user_id}"
            )
        ]
    ]

    if is_banned:
        rows.append([
            green(
                "✅ Unban User",
                f"own:user_unban:{user_id}"
            )
        ])
    else:
        rows.append([
            red(
                "🚫 Ban User",
                f"own:user_ban:{user_id}"
            )
        ])

    rows.append([
        blue(
            "💬 Send Message",
            f"own:user_msg:{user_id}"
        )
    ])

    rows.append([
        blue("🔙 Users", "own:users")
    ])

    return build_kb(rows)