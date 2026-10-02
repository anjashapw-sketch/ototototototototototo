"""
Broadcast handler.
Send mass messages to all users.
"""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.filters.is_owner import IsOwner
from bot.keyboards.builder import (
    blue, build_kb, green, red
)
from bot.keyboards.owner.confirmations import (
    get_owner_back_kb
)
from bot.keyboards.owner.main_menu import (
    OWNER_MENU
)
from bot.services.broadcast_service import (
    broadcast_service
)
from bot.states.broadcast import BroadcastStates
from bot.utils.helpers import escape_html
from bot.utils.logger import log


broadcast_router = Router(name="own_broadcast")
broadcast_router.message.filter(IsOwner())
broadcast_router.callback_query.filter(IsOwner())


# ━━━ ENTRY ━━━

@broadcast_router.message(
    F.text == OWNER_MENU["broadcast"]
)
async def msg_broadcast(
    message: Message,
    state: FSMContext,
    **kwargs
) -> None:
    """Start broadcast flow."""
    await state.clear()

    text = (
        "📢 <b>BROADCAST MESSAGE</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Send the message you want to\n"
        "broadcast to ALL users.\n\n"
        "HTML formatting supported.\n"
        "Example: <code>&lt;b&gt;Hello&lt;/b&gt;</code>"
    )

    await message.answer(
        text,
        reply_markup=get_owner_back_kb(
            "own:dashboard"
        )
    )

    await state.set_state(
        BroadcastStates.waiting_message
    )


@broadcast_router.message(
    BroadcastStates.waiting_message,
    F.text
)
async def msg_preview(
    message: Message,
    state: FSMContext,
    **kwargs
) -> None:
    """Show preview & ask confirm."""
    broadcast_text = message.text

    await state.update_data(
        broadcast_text=broadcast_text
    )

    user_ids = (
        await broadcast_service
        .get_all_user_ids()
    )

    text = (
        f"📢 <b>BROADCAST PREVIEW</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"Will be sent to: <code>"
        f"{len(user_ids)}</code> users.\n\n"
        f"━━ MESSAGE ━━\n\n"
        f"{broadcast_text}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"Confirm to send?"
    )

    kb = build_kb([
        [
            green(
                "✅ Send Now",
                "own:bcast_confirm"
            ),
            red(
                "❌ Cancel",
                "own:bcast_cancel"
            )
        ]
    ])

    await message.answer(text, reply_markup=kb)
    await state.set_state(
        BroadcastStates.waiting_confirm
    )


@broadcast_router.callback_query(
    F.data == "own:bcast_confirm"
)
async def cb_send(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs
) -> None:
    """Send broadcast."""
    data = await state.get_data()
    text = data.get("broadcast_text")

    if not text:
        await state.clear()
        await callback.answer(
            "❌ No message",
            show_alert=True
        )
        return

    try:
        await callback.message.edit_text(
            "📢 <b>BROADCASTING...</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "Please wait, this may take time."
        )
    except Exception:
        pass

    await callback.answer(
        "📢 Started", show_alert=False
    )

    # Execute broadcast
    result = await broadcast_service.broadcast(
        text=text
    )

    summary = (
        f"✅ <b>BROADCAST COMPLETE</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 Total: <code>{result.total}</code>\n"
        f"✅ Sent: <code>{result.sent}</code>\n"
        f"❌ Failed: <code>{result.failed}</code>\n"
        f"🚫 Blocked: <code>{result.blocked}</code>"
    )

    try:
        await callback.message.edit_text(
            summary,
            reply_markup=get_owner_back_kb(
                "own:dashboard"
            )
        )
    except Exception:
        pass

    await state.clear()

    log.info(
        f"📢 Broadcast by "
        f"{callback.from_user.id}: "
        f"sent={result.sent}"
    )


@broadcast_router.callback_query(
    F.data == "own:bcast_cancel"
)
async def cb_cancel(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs
) -> None:
    """Cancel broadcast."""
    await state.clear()

    try:
        await callback.message.edit_text(
            "❌ Broadcast cancelled.",
            reply_markup=get_owner_back_kb(
                "own:dashboard"
            )
        )
    except Exception:
        pass

    await callback.answer()