"""
Notifications handler.
Dedicated screen for managing notif toggles.
Provides clean UX separate from settings.
"""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database.engine import get_session
from bot.database.repositories import (
    SettingsRepository
)
from bot.filters.is_owner import IsOwner
from bot.keyboards.owner.main_menu import (
    OWNER_MENU
)
from bot.keyboards.owner.notifications import (
    get_notifications_kb
)
from bot.utils.logger import log


notifications_router = Router(
    name="own_notifications"
)
notifications_router.message.filter(IsOwner())
notifications_router.callback_query.filter(
    IsOwner()
)


# ━━━ ENTRY POINTS ━━━

@notifications_router.message(
    F.text == OWNER_MENU.get(
        "notifications", "🔔 Notifications"
    )
)
async def msg_notifications(
    message: Message,
    state: FSMContext,
    **kwargs
) -> None:
    """Show notification panel."""
    await state.clear()
    await _show_panel(message)


@notifications_router.callback_query(
    F.data == "own:notifications"
)
async def cb_notifications(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs
) -> None:
    """Show notification panel (callback)."""
    await state.clear()
    await _show_panel(
        callback.message, edit=True
    )
    await callback.answer()


async def _show_panel(
    message: Message,
    edit: bool = False
) -> None:
    """Build notifications panel."""
    async with get_session() as session:
        repo = SettingsRepository(session)

        settings_dict = {
            "low_stock_alert": (
                await repo.get_bool(
                    repo.KEY_LOW_STOCK_ALERT,
                    default=True
                )
            ),
            "session_check_enabled": (
                await repo.get_bool(
                    repo.KEY_SESSION_CHECK,
                    default=True
                )
            ),
            "sale_notifications": (
                await repo.get_bool(
                    repo.KEY_SALE_NOTIF,
                    default=True
                )
            ),
            "daily_report": (
                await repo.get_bool(
                    repo.KEY_DAILY_REPORT,
                    default=True
                )
            ),
            "balance_req_notif": (
                await repo.get_bool(
                    repo.KEY_BALANCE_REQ_NOTIF,
                    default=True
                )
            ),
            "new_user_notif": (
                await repo.get_bool(
                    repo.KEY_NEW_USER_NOTIF,
                    default=False
                )
            )
        }

    text = (
        "🔔 <b>NOTIFICATIONS</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Toggle which notifications you\n"
        "want to receive as owner:"
    )

    kb = get_notifications_kb(settings_dict)

    if edit:
        try:
            await message.edit_text(
                text, reply_markup=kb
            )
        except Exception:
            pass
    else:
        await message.answer(
            text, reply_markup=kb
        )


# ━━━ TOGGLE HANDLERS ━━━

NOTIF_KEY_MAP = {
    "low_stock_alert": (
        SettingsRepository.KEY_LOW_STOCK_ALERT
    ),
    "session_check_enabled": (
        SettingsRepository.KEY_SESSION_CHECK
    ),
    "sale_notifications": (
        SettingsRepository.KEY_SALE_NOTIF
    ),
    "daily_report": (
        SettingsRepository.KEY_DAILY_REPORT
    ),
    "balance_req_notif": (
        SettingsRepository
        .KEY_BALANCE_REQ_NOTIF
    ),
    "new_user_notif": (
        SettingsRepository.KEY_NEW_USER_NOTIF
    )
}


@notifications_router.callback_query(
    F.data.startswith("own:notif_toggle:")
)
async def cb_toggle_notif(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs
) -> None:
    """Toggle notification setting."""
    key = callback.data.split(":")[-1]

    setting_key = NOTIF_KEY_MAP.get(key)
    if not setting_key:
        await callback.answer(
            "❌ Unknown setting",
            show_alert=True
        )
        return

    async with get_session() as session:
        repo = SettingsRepository(session)
        new_val = await repo.toggle_bool(
            setting_key
        )

    status = "ON" if new_val else "OFF"
    await callback.answer(
        f"✅ {key.replace('_', ' ')}: {status}",
        show_alert=False
    )

    log.info(
        f"🔔 Notif toggle {key}={new_val} by "
        f"{callback.from_user.id}"
    )

    await _show_panel(
        callback.message, edit=True
    )