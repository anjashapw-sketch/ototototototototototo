"""
Force subscription verification handler.

Handles the "✅ Verify Membership" button.
Shows main menu after successful verification.
"""

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.database.engine import get_session
from bot.database.repositories import (
    AccountRepository,
    ForceSubRepository,
    OwnerRepository,
    UserRepository,
)
from bot.keyboards.owner.main_menu import (
    get_owner_main_menu,
)
from bot.keyboards.user.force_sub import (
    get_force_sub_kb,
)
from bot.keyboards.user.main_menu import (
    get_main_menu,
)
from bot.loader import bot
from bot.locales.i18n import i18n
from bot.utils.formatters import format_money
from bot.utils.helpers import escape_html
from bot.utils.logger import log


force_sub_router = Router(name="force_sub")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# VERIFY MEMBERSHIP CALLBACK
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@force_sub_router.callback_query(
    F.data == "fsub:verify"
)
async def cb_verify_membership(
    callback: CallbackQuery,
    state: FSMContext,
    lang: str = "en",
    **kwargs,
) -> None:
    """
    Verify if user joined all required channels.

    Flow:
        1. Get list of active force sub channels
        2. Check membership of user in each
        3. If all joined → show main menu
        4. If some missing → show updated screen
    """
    user = callback.from_user
    if not user:
        return

    # Get all active force sub channels
    async with get_session() as session:
        repo = ForceSubRepository(session)
        channels = await repo.get_all_active()

    # No channels = automatically verified
    if not channels:
        await _show_verified(callback, lang)
        return

    # Check each channel for membership
    not_joined = []

    for channel in channels:
        try:
            member = await bot.get_chat_member(
                chat_id=channel.chat_id,
                user_id=user.id,
            )
            if member.status in (
                "left",
                "kicked",
            ):
                not_joined.append(channel)

        except TelegramBadRequest:
            not_joined.append(channel)

        except Exception as e:
            log.warning(
                f"Verify check error "
                f"for channel "
                f"{channel.chat_id}: {e}"
            )
            not_joined.append(channel)

    # All joined → success!
    if not not_joined:
        await _show_verified(callback, lang)
        return

    # Some still missing → show updated screen
    text = i18n.get(
        "force_sub_partial",
        lang=lang,
    )
    text += "\n\n"

    for ch in channels:
        if ch in not_joined:
            text += f"❌ {ch.name}\n"
        else:
            text += f"✅ {ch.name}\n"

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_force_sub_kb(
                not_joined, lang
            ),
        )
    except Exception:
        try:
            await callback.message.answer(
                text,
                reply_markup=get_force_sub_kb(
                    not_joined, lang
                ),
            )
        except Exception:
            pass

    await callback.answer(
        "⚠️ Join all channels first!",
        show_alert=True,
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HELPER — Show main menu after verification
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def _show_verified(
    callback: CallbackQuery,
    lang: str,
) -> None:
    """
    Show success message and main menu.

    Args:
        callback: The verify callback query
        lang: User's language
    """
    user = callback.from_user

    # Delete force sub message
    try:
        await callback.message.delete()
    except Exception:
        pass

    # Show success popup
    try:
        await callback.answer(
            "✅ Verified!",
            show_alert=False,
        )
    except Exception:
        pass

    # Fetch user data from DB
    async with get_session() as session:
        owner_repo = OwnerRepository(session)
        is_owner = await owner_repo.is_owner(
            user.id
        )

        user_repo = UserRepository(session)
        db_user = (
            await user_repo.get_by_telegram_id(
                user.id
            )
        )

        acc_repo = AccountRepository(session)
        purchased = len(
            await acc_repo.get_user_accounts(
                db_user.id
            )
        )

    # Build welcome message
    name = escape_html(
        user.first_name or "User"
    )
    balance = format_money(
        db_user.wallet_balance
    )

    welcome_text = i18n.get(
        "welcome",
        lang=lang,
        name=name,
        balance=balance,
        purchased=purchased,
    )

    # Send main menu (owner or user)
    try:
        if is_owner:
            await callback.message.answer(
                welcome_text,
                reply_markup=(
                    get_owner_main_menu()
                ),
            )
        else:
            await callback.message.answer(
                welcome_text,
                reply_markup=get_main_menu(lang),
            )
    except Exception as e:
        log.error(
            f"Show main menu error: {e}"
        )