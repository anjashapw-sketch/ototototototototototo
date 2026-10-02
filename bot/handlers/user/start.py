"""
Start handler.
Handles /start command and main menu.
Branding is included in welcome locale.
"""

from aiogram import F, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database.engine import get_session
from bot.database.repositories import (
    AccountRepository,
    OwnerRepository,
    UserRepository,
)
from bot.keyboards.owner.main_menu import (
    get_owner_main_menu,
)
from bot.keyboards.user.main_menu import (
    get_main_menu,
    get_main_menu_texts,
)
from bot.locales.i18n import i18n
from bot.utils.formatters import format_money
from bot.utils.helpers import escape_html


start_router = Router(name="start")


@start_router.message(CommandStart())
async def cmd_start(
    message: Message,
    state: FSMContext,
    lang: str = "en",
    **kwargs,
) -> None:
    """Handle /start command."""
    await state.clear()

    user = message.from_user
    if not user:
        return

    blocked = kwargs.get(
        "force_sub_blocked", False
    )
    if blocked:
        await _show_force_sub(
            message,
            kwargs.get(
                "not_joined_channels", []
            ),
            lang,
        )
        return

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
        lang=lang,
        name=name,
        balance=balance,
        purchased=purchased,
    )

    if is_owner:
        await message.answer(
            welcome_text,
            reply_markup=get_owner_main_menu(),
        )
    else:
        await message.answer(
            welcome_text,
            reply_markup=get_main_menu(lang),
        )


@start_router.message(Command("menu"))
async def cmd_menu(
    message: Message,
    state: FSMContext,
    lang: str = "en",
    **kwargs,
) -> None:
    """Show main menu."""
    await cmd_start(
        message, state, lang, **kwargs
    )


@start_router.callback_query(
    F.data == "menu:main"
)
async def cb_main_menu(
    callback: CallbackQuery,
    state: FSMContext,
    lang: str = "en",
    **kwargs,
) -> None:
    """Return to main menu (callback)."""
    await state.clear()

    user = callback.from_user
    if not user:
        return

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
        lang=lang,
        name=name,
        balance=balance,
        purchased=purchased,
    )

    try:
        await callback.message.delete()
    except Exception:
        pass

    if is_owner:
        await callback.message.answer(
            welcome_text,
            reply_markup=get_owner_main_menu(),
        )
    else:
        await callback.message.answer(
            welcome_text,
            reply_markup=get_main_menu(lang),
        )

    await callback.answer()


@start_router.message(StateFilter(None), F.text)
async def reply_menu_handler(
    message: Message,
    state: FSMContext,
    lang: str = "en",
    **kwargs,
) -> None:
    """
    Handle reply keyboard taps.
    Only triggered when no FSM state is set.
    """
    text = message.text
    if not text:
        return

    menu_texts = get_main_menu_texts(lang)

    if text == menu_texts["shop"]:
        from bot.handlers.user.shop import (
            show_shop,
        )
        await show_shop(message, lang)

    elif text == menu_texts["wallet"]:
        from bot.handlers.user.wallet import (
            show_wallet,
        )
        await show_wallet(message, lang)

    elif text == menu_texts["accounts"]:
        from bot.handlers.user.my_accounts \
            import show_my_accounts
        await show_my_accounts(message, lang)

    elif text == menu_texts["profile"]:
        from bot.handlers.user.profile import (
            show_profile,
        )
        await show_profile(message, lang)

    elif text == menu_texts["support"]:
        from bot.handlers.user.support import (
            show_support,
        )
        await show_support(message, lang)

    elif text == menu_texts["about"]:
        from bot.handlers.user.about import (
            show_about,
        )
        await show_about(message, lang)


async def _show_force_sub(
    message: Message,
    channels: list,
    lang: str,
) -> None:
    """Show force sub join screen."""
    from bot.keyboards.user.force_sub import (
        get_force_sub_kb,
    )

    text = i18n.get(
        "force_sub_required", lang=lang
    )

    if channels:
        text += "\n\n"
        for ch in channels:
            text += f"❌ {ch.name}\n"

    await message.answer(
        text,
        reply_markup=get_force_sub_kb(
            channels, lang
        ),
    )