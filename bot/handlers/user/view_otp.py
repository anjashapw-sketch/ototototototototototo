"""
View OTP handler.
Reads OTP from purchased account.
"""

from datetime import datetime

from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.database.engine import get_session
from bot.database.repositories import (
    AccountRepository,
    UserRepository
)
from bot.keyboards.user.account import get_otp_kb
from bot.locales.i18n import i18n
from bot.services.otp_reader import otp_reader
from bot.utils.formatters import (
    format_phone_pretty
)
from bot.utils.logger import log


view_otp_router = Router(name="view_otp")


@view_otp_router.callback_query(
    F.data.startswith("acc:otp:")
)
async def cb_view_otp(
    callback: CallbackQuery,
    lang: str = "en",
    **kwargs
) -> None:
    """Read and display OTP."""
    acc_id = int(callback.data.split(":")[-1])
    user = callback.from_user

    # Show loading
    await callback.answer(
        "⏳ Fetching OTP...",
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

        # Verify ownership
        if (
            not account
            or account.sold_to != db_user.id
        ):
            await callback.answer(
                "❌ Account not found",
                show_alert=True
            )
            return

        # Check if session alive
        if not account.session_alive:
            await callback.message.edit_text(
                i18n.get(
                    "error_session_dead", lang
                ),
                reply_markup=get_otp_kb(
                    acc_id=acc_id,
                    otp_code=None,
                    lang=lang
                )
            )
            return

    # Try to read OTP
    try:
        otp_code, full_msg = (
            await otp_reader.read_otp(account)
        )
    except Exception as e:
        log.error(
            f"❌ OTP read error: {e}"
        )
        otp_code = None
        full_msg = None

    pretty_phone = format_phone_pretty(
        account.phone
    )

    if not otp_code:
        # No OTP found
        text = i18n.get(
            "otp_not_found", lang
        )

        try:
            await callback.message.edit_text(
                text,
                reply_markup=get_otp_kb(
                    acc_id=acc_id,
                    otp_code=None,
                    lang=lang
                )
            )
        except Exception:
            pass
        return

    # OTP found — display
    text = i18n.get(
        "otp_title",
        lang=lang,
        phone=pretty_phone,
        code=otp_code,
        time="just now"
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_otp_kb(
                acc_id=acc_id,
                otp_code=otp_code,
                lang=lang
            )
        )
    except Exception:
        pass

    log.info(
        f"📱 OTP viewed: user={db_user.id}, "
        f"acc={acc_id}"
    )