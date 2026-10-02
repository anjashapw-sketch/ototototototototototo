"""
Settings handler.
Toggle notifications, thresholds, payment, support.
USDT BEP20 only — USD currency.
"""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database.engine import get_session
from bot.database.repositories import (
    SettingsRepository,
)
from bot.filters.is_owner import IsOwner
from bot.keyboards.owner.confirmations import (
    get_owner_back_kb,
)
from bot.keyboards.owner.main_menu import (
    OWNER_MENU,
)
from bot.keyboards.owner.settings import (
    get_payment_settings_kb,
    get_settings_kb,
)
from bot.states.settings import SettingsStates
from bot.utils.logger import log


settings_router = Router(name="own_settings")
settings_router.message.filter(IsOwner())
settings_router.callback_query.filter(IsOwner())


# ━━━ ENTRY ━━━

@settings_router.message(
    F.text == OWNER_MENU["settings"]
)
async def msg_settings(
    message: Message,
    state: FSMContext,
    **kwargs,
) -> None:
    """Show settings."""
    await state.clear()
    await _show_settings(message)


@settings_router.callback_query(
    F.data == "own:settings"
)
async def cb_settings(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs,
) -> None:
    """Settings callback."""
    await state.clear()
    await _show_settings(
        callback.message, edit=True
    )
    await callback.answer()


async def _show_settings(
    message: Message,
    edit: bool = False,
) -> None:
    """Build settings panel."""
    async with get_session() as session:
        repo = SettingsRepository(session)

        settings_dict = {
            "low_stock_alert": (
                await repo.get_bool(
                    repo.KEY_LOW_STOCK_ALERT,
                    default=True,
                )
            ),
            "session_check_enabled": (
                await repo.get_bool(
                    repo.KEY_SESSION_CHECK,
                    default=True,
                )
            ),
            "sale_notifications": (
                await repo.get_bool(
                    repo.KEY_SALE_NOTIF,
                    default=True,
                )
            ),
            "daily_report": (
                await repo.get_bool(
                    repo.KEY_DAILY_REPORT,
                    default=True,
                )
            ),
            "balance_req_notif": (
                await repo.get_bool(
                    repo.KEY_BALANCE_REQ_NOTIF,
                    default=True,
                )
            ),
            "new_user_notif": (
                await repo.get_bool(
                    repo.KEY_NEW_USER_NOTIF,
                    default=False,
                )
            ),
            "auto_2fa": (
                await repo.get_bool(
                    repo.KEY_AUTO_2FA,
                    default=True,
                )
            ),
        }

        threshold = await repo.get_int(
            repo.KEY_LOW_STOCK_THRESHOLD,
            default=5,
        )

    text = (
        "⚙️ <b>BOT SETTINGS</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"⚠️ Low Stock Threshold: <code>"
        f"{threshold}</code>"
    )

    kb = get_settings_kb(settings_dict)

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


# ━━━ TOGGLE SETTINGS ━━━

KEY_MAP = {
    "low_stock_alert": "low_stock_alert",
    "session_check_enabled": (
        "session_check_enabled"
    ),
    "sale_notifications": "sale_notifications",
    "daily_report": "daily_report",
    "balance_req_notif": "balance_req_notif",
    "new_user_notif": "new_user_notif",
    "auto_2fa": "auto_2fa",
}


@settings_router.callback_query(
    F.data.startswith("own:set_toggle:")
)
async def cb_toggle(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs,
) -> None:
    """Toggle a boolean setting."""
    key = callback.data.split(":")[-1]

    if key not in KEY_MAP:
        await callback.answer(
            "❌ Unknown setting",
            show_alert=True,
        )
        return

    async with get_session() as session:
        repo = SettingsRepository(session)
        new_val = await repo.toggle_bool(
            KEY_MAP[key]
        )

    status = "ON" if new_val else "OFF"
    await callback.answer(
        f"✅ {key}: {status}",
        show_alert=False,
    )

    log.info(
        f"⚙️ Toggle {key}={new_val} by "
        f"{callback.from_user.id}"
    )

    await _show_settings(
        callback.message, edit=True
    )


# ━━━ SET THRESHOLD ━━━

@settings_router.callback_query(
    F.data == "own:set_threshold"
)
async def cb_set_threshold(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs,
) -> None:
    """Ask for low stock threshold."""
    text = (
        "⚠️ <b>LOW STOCK THRESHOLD</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Enter number (e.g., 5):\n\n"
        "Owner gets alert when any\n"
        "country stock falls below this."
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_owner_back_kb(
                "own:settings"
            ),
        )
    except Exception:
        pass

    await state.set_state(
        SettingsStates.waiting_threshold
    )
    await callback.answer()


@settings_router.message(
    SettingsStates.waiting_threshold,
    F.text,
)
async def msg_set_threshold(
    message: Message,
    state: FSMContext,
    **kwargs,
) -> None:
    """Save threshold."""
    text = message.text.strip()

    try:
        value = int(text)
        if value < 1 or value > 1000:
            raise ValueError
    except ValueError:
        await message.answer(
            "❌ Invalid number (1-1000)."
        )
        return

    async with get_session() as session:
        repo = SettingsRepository(session)
        await repo.set(
            repo.KEY_LOW_STOCK_THRESHOLD,
            str(value),
        )

    await state.clear()

    await message.answer(
        f"✅ Threshold set: <code>{value}</code>",
        reply_markup=get_owner_back_kb(
            "own:settings"
        ),
    )

    log.info(
        f"⚙️ Threshold={value} by "
        f"{message.from_user.id}"
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PAYMENT SETTINGS MENU
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@settings_router.callback_query(
    F.data == "own:payment_settings"
)
async def cb_payment_settings(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs,
):
    """Show payment settings (USDT only)."""
    await state.clear()

    async with get_session() as session:
        repo = SettingsRepository(session)

        usdt_address = await repo.get(
            repo.KEY_USDT_BEP20_ADDRESS
        ) or "Not Set"

        min_deposit = await repo.get(
            repo.KEY_MIN_DEPOSIT
        ) or "1"

        max_deposit = await repo.get(
            repo.KEY_MAX_DEPOSIT
        ) or "10000"

    text = (
        "💳 <b>PAYMENT SETTINGS</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"💲 USDT Address (BEP20):\n"
        f"<code>{usdt_address}</code>\n\n"
        f"⬇️ Min Deposit: "
        f"<code>${min_deposit}</code>\n"
        f"⬆️ Max Deposit: "
        f"<code>${max_deposit}</code>"
    )

    await callback.message.edit_text(
        text,
        reply_markup=get_payment_settings_kb(),
    )

    await callback.answer()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# USDT ADDRESS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@settings_router.callback_query(
    F.data == "own:set_usdt"
)
async def cb_set_usdt(
    callback: CallbackQuery,
    state: FSMContext,
):
    await state.set_state(
        SettingsStates.waiting_usdt_address
    )

    await callback.message.edit_text(
        "💲 Send BEP20 wallet address:",
        reply_markup=get_owner_back_kb(
            "own:payment_settings"
        ),
    )

    await callback.answer()


@settings_router.message(
    SettingsStates.waiting_usdt_address,
    F.text,
)
async def msg_set_usdt(
    message: Message,
    state: FSMContext,
):
    async with get_session() as session:
        repo = SettingsRepository(session)

        await repo.set(
            repo.KEY_USDT_BEP20_ADDRESS,
            message.text.strip(),
        )

    await state.clear()

    await message.answer(
        "✅ USDT address updated.",
        reply_markup=get_owner_back_kb(
            "own:payment_settings"
        ),
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MIN DEPOSIT (USD)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@settings_router.callback_query(
    F.data == "own:set_min_dep"
)
async def cb_set_min_dep(
    callback: CallbackQuery,
    state: FSMContext,
):
    await state.set_state(
        SettingsStates.waiting_min_deposit
    )

    await callback.message.edit_text(
        "⬇️ Send minimum deposit amount (USD):\n"
        "Example: <code>1</code>",
        reply_markup=get_owner_back_kb(
            "own:payment_settings"
        ),
    )

    await callback.answer()


@settings_router.message(
    SettingsStates.waiting_min_deposit,
    F.text,
)
async def msg_set_min_dep(
    message: Message,
    state: FSMContext,
):
    text = message.text.strip()

    try:
        value = float(text)
        if value < 0.1:
            raise ValueError
    except ValueError:
        await message.answer(
            "❌ Invalid amount."
        )
        return

    async with get_session() as session:
        repo = SettingsRepository(session)
        await repo.set(
            repo.KEY_MIN_DEPOSIT,
            str(value),
        )

    await state.clear()

    await message.answer(
        f"✅ Minimum deposit: <code>${value}</code>",
        reply_markup=get_owner_back_kb(
            "own:payment_settings"
        ),
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAX DEPOSIT (USD)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@settings_router.callback_query(
    F.data == "own:set_max_dep"
)
async def cb_set_max_dep(
    callback: CallbackQuery,
    state: FSMContext,
):
    await state.set_state(
        SettingsStates.waiting_max_deposit
    )

    await callback.message.edit_text(
        "⬆️ Send maximum deposit amount (USD):\n"
        "Example: <code>10000</code>",
        reply_markup=get_owner_back_kb(
            "own:payment_settings"
        ),
    )

    await callback.answer()


@settings_router.message(
    SettingsStates.waiting_max_deposit,
    F.text,
)
async def msg_set_max_dep(
    message: Message,
    state: FSMContext,
):
    text = message.text.strip()

    try:
        value = float(text)
        if value < 1:
            raise ValueError
    except ValueError:
        await message.answer(
            "❌ Invalid amount."
        )
        return

    async with get_session() as session:
        repo = SettingsRepository(session)
        await repo.set(
            repo.KEY_MAX_DEPOSIT,
            str(value),
        )

    await state.clear()

    await message.answer(
        f"✅ Maximum deposit: <code>${value}</code>",
        reply_markup=get_owner_back_kb(
            "own:payment_settings"
        ),
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SUPPORT USERNAME
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@settings_router.callback_query(
    F.data == "own:set_support_username"
)
async def cb_set_support_username(
    callback: CallbackQuery,
    state: FSMContext,
):
    """Ask for support username."""

    async with get_session() as session:
        repo = SettingsRepository(session)
        current = await repo.get(
            SettingsRepository.KEY_SUPPORT_USERNAME
        ) or "Not set"

    await state.set_state(
        SettingsStates.waiting_support_username
    )

    await callback.message.edit_text(
        f"👤 <b>Set Support Username</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"Current: <code>{current}</code>\n\n"
        f"Send Telegram username for support contact.\n"
        f"Example: <code>@yoursupport</code> or "
        f"<code>yoursupport</code>",
        reply_markup=get_owner_back_kb(
            "own:settings"
        ),
    )

    await callback.answer()


@settings_router.message(
    SettingsStates.waiting_support_username,
    F.text,
)
async def msg_set_support_username(
    message: Message,
    state: FSMContext,
):
    """Save support username."""

    username = (
        message.text.strip().lstrip("@")
    )

    if not username or " " in username:
        await message.answer(
            "❌ Invalid username.\n"
            "Send only the username "
            "(no spaces, no @)."
        )
        return

    async with get_session() as session:
        repo = SettingsRepository(session)
        await repo.set(
            SettingsRepository.KEY_SUPPORT_USERNAME,
            username,
        )

    await state.clear()

    await message.answer(
        f"✅ Support username set to: "
        f"<code>@{username}</code>",
        reply_markup=get_owner_back_kb(
            "own:settings"
        ),
    )

    log.info(
        f"⚙️ Support username={username} by "
        f"{message.from_user.id}"
    )