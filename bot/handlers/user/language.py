"""
Language handler.
Allows users to change language.
"""

from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.database.engine import get_session
from bot.database.repositories import (
    AccountRepository,
    OwnerRepository,
    UserRepository,
)
from bot.keyboards.owner.main_menu import (
    get_owner_main_menu,
)
from bot.keyboards.user.language import (
    get_language_kb,
)
from bot.keyboards.user.main_menu import (
    get_main_menu,
)
from bot.locales.i18n import i18n
from bot.utils.formatters import format_money
from bot.utils.helpers import escape_html
from bot.utils.logger import log


language_router = Router(name="language")


@language_router.callback_query(
    F.data == "profile:lang"
)
async def cb_show_language(
    callback: CallbackQuery,
    lang: str = "en",
    **kwargs,
) -> None:
    """Show language selection menu."""
    text = i18n.get("language_select", lang)

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_language_kb(lang),
        )
    except Exception:
        pass

    await callback.answer()


@language_router.callback_query(
    F.data.startswith("lang:set:")
)
async def cb_set_language(
    callback: CallbackQuery,
    **kwargs,
) -> None:
    """Set user's language."""
    new_lang = callback.data.split(":")[-1]

    if not i18n.is_supported(new_lang):
        await callback.answer(
            "❌ Unsupported language",
            show_alert=True,
        )
        return

    user = callback.from_user

    async with get_session() as session:
        user_repo = UserRepository(session)
        db_user = (
            await user_repo.get_by_telegram_id(
                user.id
            )
        )
        await user_repo.set_language(
            db_user.id, new_lang
        )

    lang_name = i18n.get_language_name(new_lang)
    confirm_text = i18n.get(
        "language_changed",
        lang=new_lang,
        language=lang_name,
    )

    await callback.answer(
        confirm_text, show_alert=True
    )

    log.info(
        f"🌍 Language changed: "
        f"user={db_user.id}, lang={new_lang}"
    )

    # Delete old message
    try:
        await callback.message.delete()
    except Exception:
        pass

    # Refresh main menu with new language
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

    name = escape_html(
        user.first_name or "User"
    )
    balance = format_money(
        db_user.wallet_balance
    )

    welcome_text = i18n.get(
        "welcome",
        lang=new_lang,
        name=name,
        balance=balance,
        purchased=purchased,
    )

    if is_owner:
        await callback.message.answer(
            welcome_text,
            reply_markup=get_owner_main_menu(),
        )
    else:
        await callback.message.answer(
            welcome_text,
            reply_markup=get_main_menu(new_lang),
        )