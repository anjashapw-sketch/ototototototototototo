"""Force subscription keyboards (owner)."""

from typing import List

from aiogram.types import InlineKeyboardMarkup

from bot.database.models import ForceSubChannel
from bot.database.models.force_sub_channel \
    import ChannelType
from bot.keyboards.builder import (
    blue, build_kb, green, red
)


def get_fsub_main_kb(
    is_enabled: bool
) -> InlineKeyboardMarkup:
    """Force sub main screen."""
    toggle_text = (
        "🔴 Disable Force Sub"
        if is_enabled
        else "🟢 Enable Force Sub"
    )
    toggle_btn_fn = red if is_enabled else green

    return build_kb([
        [
            green(
                "➕ Add Channel/Group",
                "own:fsub_add"
            )
        ],
        [
            blue(
                "📋 Manage Existing",
                "own:fsub_list"
            )
        ],
        [
            toggle_btn_fn(
                toggle_text,
                "own:fsub_toggle"
            )
        ],
        [
            blue(
                "🔙 Dashboard", "own:dashboard"
            )
        ]
    ])


def get_fsub_type_kb() -> InlineKeyboardMarkup:
    """Public or Private selection."""
    return build_kb([
        [
            blue(
                "🌐 Public",
                "own:fsub_type:public"
            ),
            blue(
                "🔒 Private",
                "own:fsub_type:private"
            )
        ],
        [
            red("❌ Cancel", "own:fsub")
        ]
    ])


def get_fsub_cancel_kb() -> InlineKeyboardMarkup:
    """Cancel during add flow."""
    return build_kb([
        [
            red("❌ Cancel", "own:fsub")
        ]
    ])


def get_fsub_list_kb(
    channels: List[ForceSubChannel]
) -> InlineKeyboardMarkup:
    """List of channels to manage."""
    rows = []
    for ch in channels:
        icon = (
            "🔒" if ch.type == ChannelType.PRIVATE
            else "🌐"
        )
        rows.append([
            blue(
                f"{icon} {ch.name}",
                f"own:fsub_view:{ch.id}"
            )
        ])

    rows.append([
        blue("🔙 Back", "own:fsub")
    ])

    return build_kb(rows)


def get_fsub_channel_kb(
    channel_id: int
) -> InlineKeyboardMarkup:
    """Single channel actions."""
    return build_kb([
        [
            blue(
                "🔄 Recheck Bot Admin",
                f"own:fsub_recheck:{channel_id}"
            )
        ],
        [
            blue(
                "✏️ Edit Invite Link",
                f"own:fsub_editlink:{channel_id}"
            )
        ],
        [
            red(
                "🗑 Remove Channel",
                f"own:fsub_remove:{channel_id}"
            )
        ],
        [
            blue("🔙 Back", "own:fsub_list")
        ]
    ])


def get_fsub_remove_confirm_kb(
    channel_id: int
) -> InlineKeyboardMarkup:
    """Confirm remove channel."""
    return build_kb([
        [
            red(
                "✅ Yes, Remove",
                f"own:fsub_rm_yes:{channel_id}"
            ),
            blue(
                "❌ Cancel",
                f"own:fsub_view:{channel_id}"
            )
        ]
    ])


def get_fsub_retry_kb() -> InlineKeyboardMarkup:
    """Retry/Cancel for errors."""
    return build_kb([
        [
            green(
                "🔄 Try Again",
                "own:fsub_retry"
            ),
            red("❌ Cancel", "own:fsub")
        ]
    ])