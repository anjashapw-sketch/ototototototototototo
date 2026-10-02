"""Generic confirmation keyboards."""

from aiogram.types import InlineKeyboardMarkup

from bot.keyboards.builder import (
    blue, build_kb, green, red
)


def get_yes_no_kb(
    yes_cb: str,
    no_cb: str,
    yes_text: str = "✅ Yes",
    no_text: str = "❌ No",
    danger: bool = False,
) -> InlineKeyboardMarkup:
    """
    Generic Yes/No confirmation.
    """
    yes_btn = (
        red(yes_text, yes_cb)
        if danger
        else green(yes_text, yes_cb)
    )
    return build_kb([
        [yes_btn, blue(no_text, no_cb)]
    ])


def get_owner_back_kb(
    callback_data: str = "own:dashboard"
) -> InlineKeyboardMarkup:
    """Owner back to dashboard."""
    return build_kb([
        [blue("🔙 Dashboard", callback_data)]
    ])


def get_add_account_cancel_kb() -> InlineKeyboardMarkup:
    """Cancel add account flow."""
    return build_kb([
        [
            red(
                "❌ Cancel",
                "own:add_acc_cancel"
            )
        ]
    ])


def get_add_another_kb(
    added_count: int = 1,
) -> InlineKeyboardMarkup:
    """After successful add — with notify option."""
    notify_label = (
        f"📢 Notify Users ({added_count} added)"
        if added_count > 0
        else "📢 Notify Users"
    )

    return build_kb([
        [
            green(
                "➕ Add Another",
                "own:add_acc"
            )
        ],
        [
            green(
                notify_label,
                "own:notify_stock"
            )
        ],
        [
            blue("🔙 Dashboard", "own:dashboard")
        ]
    ])


def get_wallet_requests_kb(
    requests: list
) -> InlineKeyboardMarkup:
    """List of pending wallet requests."""
    from bot.utils.formatters import format_money

    rows = []
    for req in requests:
        amount = format_money(req.amount)
        text = (
            f"💳 User #{req.user_id} - {amount}"
        )
        rows.append([
            blue(
                text,
                f"own:wreq_view:{req.id}"
            )
        ])

    rows.append([
        blue("🔙 Wallets", "own:wallets")
    ])

    return build_kb(rows)


def get_wallet_request_action_kb(
    req_id: int
) -> InlineKeyboardMarkup:
    """Approve/Reject wallet request."""
    return build_kb([
        [
            green(
                "✅ Approve",
                f"own:wreq_approve:{req_id}"
            ),
            red(
                "❌ Reject",
                f"own:wreq_reject:{req_id}"
            )
        ],
        [
            blue(
                "🔙 Back",
                "own:wreq_pending"
            )
        ]
    ])


def get_wallets_overview_kb() -> InlineKeyboardMarkup:
    """Wallet management overview."""
    return build_kb([
        [
            blue(
                "📨 Pending Requests",
                "own:wreq_pending"
            )
        ],
        [
            green(
                "💰 Manual Add Balance",
                "own:wal_addbal"
            )
        ],
        [
            blue(
                "📋 All Transactions",
                "own:wal_txns"
            )
        ],
        [
            blue("🔙 Dashboard", "own:dashboard")
        ]
    ])