"""
Profile handler.
Shows user profile info.
"""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from bot.database.engine import get_session
from bot.database.repositories import (
    AccountRepository,
    TransactionRepository,
    UserRepository
)
from bot.keyboards.user.profile import (
    get_profile_kb
)
from bot.locales.i18n import i18n
from bot.utils.formatters import (
    format_date, format_money
)
from bot.utils.helpers import escape_html


profile_router = Router(name="profile")


async def show_profile(
    message: Message,
    lang: str = "en"
) -> None:
    """Display user profile."""
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

    text = i18n.get(
        "profile_title",
        lang=lang,
        id=user.id,
        name=escape_html(
            user.first_name or "User"
        ),
        username=escape_html(
            user.username or "none"
        ),
        joined=format_date(
            db_user.joined_date
        ),
        balance=format_money(
            db_user.wallet_balance
        ),
        purchases=len(accounts),
        language=i18n.get_language_name(
            db_user.language_code
        )
    )

    await message.answer(
        text,
        reply_markup=get_profile_kb(lang)
    )


@profile_router.callback_query(
    F.data == "profile:back"
)
async def cb_profile_back(
    callback: CallbackQuery,
    lang: str = "en",
    **kwargs
) -> None:
    """Back to profile from language menu."""
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

    text = i18n.get(
        "profile_title",
        lang=lang,
        id=user.id,
        name=escape_html(
            user.first_name or "User"
        ),
        username=escape_html(
            user.username or "none"
        ),
        joined=format_date(
            db_user.joined_date
        ),
        balance=format_money(
            db_user.wallet_balance
        ),
        purchases=len(accounts),
        language=i18n.get_language_name(
            db_user.language_code
        )
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_profile_kb(lang)
        )
    except Exception:
        pass

    await callback.answer()