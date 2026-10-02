"""
Notify users handler.
Broadcast new stock additions to all users.
Flow: confirm → ask description → preview → send
"""

from collections import Counter

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot.database.engine import get_session
from bot.database.repositories import (
    UserRepository,
)
from bot.filters.is_owner import IsOwner
from bot.keyboards.builder import (
    blue,
    build_kb,
    green,
    red,
)
from bot.loader import bot
from bot.utils.flag_emoji import get_flag
from bot.utils.logger import log


notify_stock_router = Router(
    name="own_notify_stock"
)
notify_stock_router.message.filter(IsOwner())
notify_stock_router.callback_query.filter(IsOwner())


# ━━━ FSM STATES ━━━

class NotifyStockStates(StatesGroup):
    """States for notify stock flow."""
    waiting_description = State()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 1 — ASK FOR DESCRIPTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@notify_stock_router.callback_query(
    F.data == "own:notify_stock"
)
async def cb_notify_stock_start(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs,
) -> None:
    """Ask admin for description before broadcast."""

    data = await state.get_data()
    added_list = data.get("added_accounts", [])

    if not added_list:
        await callback.answer(
            "⚠️ No accounts added in this session.",
            show_alert=True,
        )
        return

    # Group by country for summary
    country_count = Counter()
    country_names = {}
    for acc in added_list:
        code = acc["country_code"]
        country_count[code] += 1
        country_names[code] = acc["country_name"]

    lines = []
    for code, count in country_count.most_common():
        flag = get_flag(code)
        name = country_names[code]
        lines.append(
            f"  {flag} <b>{name}</b> "
            f"— <code>{count}</code>"
        )
    summary = "\n".join(lines)

    # Save summary in state for next step
    await state.update_data(
        country_count=dict(country_count),
        country_names=country_names,
    )

    await state.set_state(
        NotifyStockStates.waiting_description
    )

    kb = build_kb([
        [
            blue(
                "⏭ Skip Description",
                "own:notify_stock_skip_desc",
            ),
        ],
        [
            red(
                "❌ Cancel",
                "own:notify_stock_cancel",
            ),
        ],
    ])

    text = (
        f"📝 <b>ADD DESCRIPTION</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 Total: <b>{len(added_list)}</b> accounts\n"
        f"🌍 Countries:\n{summary}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💬 Send a description message\n"
        f"for users (optional).\n\n"
        f"<i>Examples:</i>\n"
        f"• <i>Fresh USA accounts, OTP working!</i>\n"
        f"• <i>Premium quality, limited stock!</i>\n"
        f"• <i>Special discount for next 24h!</i>\n\n"
        f"Or click Skip to broadcast without one."
    )

    try:
        await callback.message.edit_text(
            text, reply_markup=kb
        )
    except Exception:
        await callback.message.answer(
            text, reply_markup=kb
        )

    await callback.answer()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 2 — RECEIVE DESCRIPTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@notify_stock_router.message(
    NotifyStockStates.waiting_description,
    F.text,
)
async def msg_receive_description(
    message: Message,
    state: FSMContext,
    **kwargs,
) -> None:
    """Save description and show preview."""

    description = message.text.strip()

    if len(description) > 500:
        await message.answer(
            "❌ Description too long. Max 500 chars."
        )
        return

    await state.update_data(
        description=description
    )

    await _show_preview(message, state)


@notify_stock_router.callback_query(
    F.data == "own:notify_stock_skip_desc"
)
async def cb_skip_description(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs,
) -> None:
    """Skip description and show preview."""

    await state.update_data(description=None)
    await _show_preview(
        callback.message, state, is_callback=True
    )
    await callback.answer()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 3 — SHOW PREVIEW
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def _show_preview(
    message: Message,
    state: FSMContext,
    is_callback: bool = False,
) -> None:
    """Show broadcast preview."""

    data = await state.get_data()
    added_list = data.get("added_accounts", [])
    description = data.get("description")
    country_count = Counter(
        data.get("country_count", {})
    )
    country_names = data.get("country_names", {})

    # Build broadcast preview
    preview = _build_broadcast_text(
        country_count, country_names, description
    )

    confirm_text = (
        f"📢 <b>BROADCAST PREVIEW</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>This message will be sent:</b>\n\n"
        f"{preview}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ Send to all users now?"
    )

    kb = build_kb([
        [
            green(
                "✅ Send Broadcast",
                "own:notify_stock_send",
            ),
        ],
        [
            blue(
                "✏️ Edit Description",
                "own:notify_stock",
            ),
        ],
        [
            red(
                "❌ Cancel",
                "own:notify_stock_cancel",
            ),
        ],
    ])

    if is_callback:
        try:
            await message.edit_text(
                confirm_text, reply_markup=kb
            )
            return
        except Exception:
            pass

    await message.answer(
        confirm_text, reply_markup=kb
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 4 — SEND BROADCAST
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@notify_stock_router.callback_query(
    F.data == "own:notify_stock_send"
)
async def cb_notify_stock_send(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs,
) -> None:
    """Send the broadcast to all users."""

    data = await state.get_data()
    added_list = data.get("added_accounts", [])
    description = data.get("description")
    country_count = Counter(
        data.get("country_count", {})
    )
    country_names = data.get("country_names", {})

    if not added_list:
        await callback.answer(
            "⚠️ No accounts to notify.",
            show_alert=True,
        )
        return

    broadcast_text = _build_broadcast_text(
        country_count, country_names, description
    )

    # Inline button to shop
    kb = build_kb([
        [
            green(
                "🛒 Browse Shop",
                "menu:main",
            ),
        ],
    ])

    # Get all active users
    async with get_session() as session:
        user_repo = UserRepository(session)
        user_ids = (
            await user_repo.get_all_active_ids()
        )

    total = len(user_ids)
    if total == 0:
        await callback.answer(
            "⚠️ No users to broadcast to.",
            show_alert=True,
        )
        return

    try:
        await callback.message.edit_text(
            f"📡 <b>Broadcasting...</b>\n\n"
            f"👥 Total users: <b>{total}</b>\n"
            f"⏳ Please wait..."
        )
    except Exception:
        pass

    await callback.answer()

    # Send to all
    sent = 0
    failed = 0

    for tg_id in user_ids:
        try:
            await bot.send_message(
                chat_id=tg_id,
                text=broadcast_text,
                reply_markup=kb,
                disable_web_page_preview=True,
            )
            sent += 1
        except Exception as e:
            failed += 1
            log.debug(
                f"Broadcast fail to {tg_id}: {e}"
            )

    # Clear everything
    await state.clear()

    # Final result
    result_text = (
        f"✅ <b>BROADCAST COMPLETE</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 Accounts: "
        f"<b>{len(added_list)}</b>\n"
        f"👥 Total users: <b>{total}</b>\n"
        f"✅ Sent: <b>{sent}</b>\n"
        f"❌ Failed: <b>{failed}</b>\n\n"
        f"<i>Users have been notified!</i>"
    )

    back_kb = build_kb([
        [
            blue(
                "🔙 Dashboard",
                "own:dashboard",
            ),
        ],
    ])

    try:
        await callback.message.edit_text(
            result_text, reply_markup=back_kb
        )
    except Exception:
        await callback.message.answer(
            result_text, reply_markup=back_kb
        )

    log.info(
        f"📢 Stock broadcast: sent={sent}, "
        f"failed={failed}, "
        f"by={callback.from_user.id}"
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CANCEL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@notify_stock_router.callback_query(
    F.data == "own:notify_stock_cancel"
)
async def cb_notify_stock_cancel(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs,
) -> None:
    """Cancel broadcast (keep added list)."""

    # Preserve added list
    data = await state.get_data()
    added_list = data.get("added_accounts", [])

    await state.clear()
    if added_list:
        await state.update_data(
            added_accounts=added_list
        )

    kb = build_kb([
        [
            green(
                "📢 Notify Now",
                "own:notify_stock",
            ),
        ],
        [
            blue(
                "🔙 Dashboard",
                "own:dashboard",
            ),
        ],
    ])

    await callback.message.edit_text(
        "❌ Broadcast cancelled.\n\n"
        "<i>Your added accounts are preserved.\n"
        "You can notify users anytime.</i>",
        reply_markup=kb,
    )
    await callback.answer()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HELPER — Build broadcast message
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _build_broadcast_text(
    country_count: Counter,
    country_names: dict,
    description: str | None = None,
) -> str:
    """Build the beautiful broadcast message."""

    total = sum(country_count.values())

    lines = []
    for code, count in country_count.most_common():
        flag = get_flag(code)
        name = country_names.get(
            code, code.upper()
        )
        lines.append(
            f"  {flag} <b>{name}</b> "
            f"— <code>{count}</code> in stock"
        )

    countries_text = "\n".join(lines)

    description_block = ""
    if description:
        description_block = (
            f"\n\n💬 <b>Note from admin:</b>\n"
            f"<i>{description}</i>\n"
        )

    return (
        f"🔥 <b>NEW STOCK ALERT!</b> 🔥\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"✨ Fresh accounts just dropped!\n\n"
        f"📦 <b>Total Added:</b> "
        f"<code>{total}</code>\n"
        f"🌍 <b>Countries Available:</b>\n\n"
        f"{countries_text}"
        f"{description_block}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"⚡ <b>Hurry up!</b>\n"
        f"💎 First come, first served.\n\n"
        f"🛒 Tap below to grab yours!"
    )