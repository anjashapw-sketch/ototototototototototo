"""
Remove device handler.
Logout bot from user's purchased account.
"""

from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.database.engine import get_session
from bot.database.repositories import (
    AccountRepository,
    UserRepository
)
from bot.keyboards.user.account import (
    get_remove_confirm_kb
)
from bot.keyboards.user.common import (
    get_back_menu_kb
)
from bot.locales.i18n import i18n
from bot.services.otp_reader import otp_reader
from bot.utils.logger import log


remove_device_router = Router(
    name="remove_device"
)


@remove_device_router.callback_query(
    F.data.startswith("acc:remove:")
)
async def cb_remove_init(
    callback: CallbackQuery,
    lang: str = "en",
    **kwargs
) -> None:
    """Show remove device confirmation."""
    acc_id = int(callback.data.split(":")[-1])
    user = callback.from_user

    async with get_session() as session:
        user_repo = UserRepository(session)
        db_user = (
            await user_repo.get_by_telegram_id(
                user.id
            )
        )

        acc_repo = AccountRepository(session)
        account = await acc_repo.get_by_id(
            acc_id
        )

        if (
            not account
            or account.sold_to != db_user.id
        ):
            await callback.answer(
                "❌ Not found",
                show_alert=True
            )
            return

    text = i18n.get(
        "remove_device_confirm", lang
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_remove_confirm_kb(
                acc_id, lang
            )
        )
    except Exception:
        pass

    await callback.answer()


@remove_device_router.callback_query(
    F.data.startswith("acc:remove_yes:")
)
async def cb_remove_confirm(
    callback: CallbackQuery,
    lang: str = "en",
    **kwargs
) -> None:
    """Execute device removal (logout)."""
    acc_id = int(callback.data.split(":")[-1])
    user = callback.from_user

    await callback.answer(
        "⏳ Logging out...",
        show_alert=False
    )

    async with get_session() as session:
        user_repo = UserRepository(session)
        db_user = (
            await user_repo.get_by_telegram_id(
                user.id
            )
        )

        acc_repo = AccountRepository(session)
        account = await acc_repo.get_by_id(
            acc_id
        )

        if (
            not account
            or account.sold_to != db_user.id
        ):
            await callback.answer(
                "❌ Not found",
                show_alert=True
            )
            return

    # Perform logout
    try:
        success = (
            await otp_reader.terminate_session(
                account
            )
        )
    except Exception as e:
        log.error(
            f"❌ Remove device error: {e}"
        )
        success = False

    # Mark session as dead regardless
    async with get_session() as session:
        acc_repo = AccountRepository(session)
        await acc_repo.mark_session_dead(
            acc_id
        )

    text = i18n.get("device_removed", lang)

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_back_menu_kb(lang)
        )
    except Exception:
        pass

    log.info(
        f"🗑 Device removed: user={db_user.id}, "
        f"acc={acc_id}, success={success}"
    )