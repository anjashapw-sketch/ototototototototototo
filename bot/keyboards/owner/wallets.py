"""Owner wallet keyboards."""

from aiogram.types import InlineKeyboardMarkup

from bot.keyboards.builder import (
    blue,
    build_kb,
    green,
    red,
)


def get_wallets_menu_kb(
    pending_count: int = 0,
) -> InlineKeyboardMarkup:
    """Owner wallet management menu."""

    pending_label = (
        f"⏳ Pending Requests ({pending_count})"
        if pending_count > 0
        else "⏳ Pending Requests"
    )

    return build_kb([
        [
            green(
                pending_label,
                "owner:wallet_pending",
            )
        ],
        [
            blue(
                "⚙️ Payment Settings",
                "owner:payment_settings",
            )
        ],
        [
            blue("🔙 Back", "owner:dashboard")
        ],
    ])


def get_pending_requests_kb(
    requests: list,
) -> InlineKeyboardMarkup:
    """List of pending requests as buttons."""

    rows = []
    for req in requests:
        method = req.payment_method.value.upper()
        rows.append([
            blue(
                f"#{req.id} | "
                f"${req.amount_inr} | "
                f"{method}",
                f"owner:wallet_req:{req.id}",
            )
        ])

    rows.append([
        blue("🔙 Back", "owner:wallets")
    ])

    return build_kb(rows)


def get_request_action_kb(
    request_id: int,
) -> InlineKeyboardMarkup:
    """Approve / Reject buttons for a request."""

    return build_kb([
        [
            green(
                "✅ Approve",
                f"owner:wallet_approve:{request_id}",
            ),
            red(
                "❌ Reject",
                f"owner:wallet_reject:{request_id}",
            ),
        ],
        [
            blue(
                "🔙 Back",
                "owner:wallet_pending",
            )
        ],
    ])


def get_payment_settings_kb() -> InlineKeyboardMarkup:
    """Payment settings — USDT BEP20 only."""

    return build_kb([
        [
            blue(
                "💲 Set USDT Address",
                "owner:set_usdt_address",
            )
        ],
        [
            blue(
                "📉 Min Deposit",
                "owner:set_min_deposit",
            ),
            blue(
                "📈 Max Deposit",
                "owner:set_max_deposit",
            ),
        ],
        [
            blue("🔙 Back", "owner:wallets")
        ],
    ])