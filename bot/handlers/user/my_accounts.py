"""
My accounts handler.
Shows user's purchased accounts.
"""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from bot.database.engine import get_session
from bot.database.repositories import (
    AccountRepository,
    UserRepository
)
from bot.keyboards.user.account import (
    get_account_details_kb,
    get_my_accounts_kb
)
from bot.keyboards.user.common import (
    get_back_menu_kb
)
from bot.locales.i18n import i18n
from bot.services.account_manager import (
    AccountManager
)
from bot.utils.flag_emoji import get_flag
from bot.utils.formatters import (
    format_date,
    format_phone_pretty
)


my_accounts_router = Router(name="my_accounts")


async def show_my_accounts(
    message: Message,
    lang: str = "en"
) -> None:
    """Display user's account list."""
    user = message.from_user

    async with get_session() as session:
        user_repo = UserRepository(session)
        db_user = (
            await user_repo.get_by_telegram_id(
                user.id
            )
        )

        acc_repo = AccountRepository(session)
        accounts = (
            await acc_repo.get_user_accounts(
                db_user.id
            )
        )

    if not accounts:
        await message.answer(
            i18n.get("my_accounts_empty", lang),
            reply_markup=get_back_menu_kb(lang)
        )
        return

    text = i18n.get(
        "my_accounts_title",
        lang=lang,
        count=len(accounts)
    )

    await message.answer(
        text,
        reply_markup=get_my_accounts_kb(
            accounts, lang
        )
    )


@my_accounts_router.callback_query(
    F.data == "acc:my_list"
)
async def cb_my_list(
    callback: CallbackQuery,
    lang: str = "en",
    **kwargs
) -> None:
    """Show accounts list (callback)."""
    user = callback.from_user

    async with get_session() as session:
        user_repo = UserRepository(session)
        db_user = (
            await user_repo.get_by_telegram_id(
                user.id
            )
        )

        acc_repo = AccountRepository(session)
        accounts = (
            await acc_repo.get_user_accounts(
                db_user.id
            )
        )

    if not accounts:
        try:
            await callback.message.edit_text(
                i18n.get(
                    "my_accounts_empty", lang
                ),
                reply_markup=get_back_menu_kb(
                    lang
                )
            )
        except Exception:
            pass
        await callback.answer()
        return

    text = i18n.get(
        "my_accounts_title",
        lang=lang,
        count=len(accounts)
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_my_accounts_kb(
                accounts, lang
            )
        )
    except Exception:
        pass

    await callback.answer()


@my_accounts_router.callback_query(
    F.data.startswith("acc:details:")
)
async def cb_account_details(
    callback: CallbackQuery,
    lang: str = "en",
    **kwargs
) -> None:
    """Show single account details."""
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

        manager = AccountManager(session)
        twofa = manager.decrypt_2fa(account)

    flag = get_flag(account.country_code)
    pretty_phone = format_phone_pretty(
        account.phone
    )

    if account.session_alive:
        status_text = i18n.get(
            "status_active", lang
        )
    else:
        status_text = i18n.get(
            "status_removed", lang
        )

    text = i18n.get(
        "account_details",
        lang=lang,
        phone=pretty_phone,
        twofa=twofa or "N/A",
        country=f"{flag} {account.country_name}",
        date=format_date(account.sold_date),
        status=status_text
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_account_details_kb(
                acc_id, lang
            )
        )
    except Exception:
        pass

    await callback.answer()