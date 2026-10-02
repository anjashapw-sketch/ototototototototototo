"""
User management handler (owner).
List, search, view, ban, message users.
"""

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database.engine import get_session
from bot.database.repositories import (
    AccountRepository,
    OwnerRepository,
    TransactionRepository,
    UserRepository
)
from bot.filters.is_owner import IsOwner
from bot.keyboards.owner.confirmations import (
    get_owner_back_kb
)
from bot.keyboards.owner.main_menu import (
    OWNER_MENU
)
from bot.keyboards.owner.users import (
    get_user_view_kb,
    get_users_list_kb,
    get_users_overview_kb
)
from bot.loader import bot
from bot.locales.i18n import i18n
from bot.services.wallet_service import (
    WalletService
)
from bot.states.admin_add import (
    UserSearchStates,
    WalletAdminStates
)
from bot.utils.formatters import (
    format_date, format_money
)
from bot.utils.helpers import escape_html
from bot.utils.logger import log
from bot.utils.validators import (
    validate_amount,
    validate_telegram_id
)


users_router = Router(name="own_users")
users_router.message.filter(IsOwner())
users_router.callback_query.filter(IsOwner())


# ━━━ OVERVIEW ━━━

@users_router.message(
    F.text == OWNER_MENU["users"]
)
async def msg_users(
    message: Message,
    state: FSMContext,
    **kwargs
) -> None:
    """Show users overview."""
    await state.clear()
    await _show_overview(message)


@users_router.callback_query(
    F.data == "own:users"
)
async def cb_users(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs
) -> None:
    """Users overview (callback)."""
    await state.clear()
    await _show_overview(
        callback.message, edit=True
    )
    await callback.answer()


async def _show_overview(
    message: Message,
    edit: bool = False
) -> None:
    """Build users overview."""
    async with get_session() as session:
        repo = UserRepository(session)
        total = await repo.count_all()
        banned = await repo.count_banned()

    text = (
        "👥 <b>USER MANAGEMENT</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Total: <code>{total}</code>\n"
        f"✅ Active: <code>"
        f"{total - banned}</code>\n"
        f"🚫 Banned: <code>{banned}</code>"
    )

    kb = get_users_overview_kb()

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


# ━━━ USERS LIST (Paginated) ━━━

@users_router.callback_query(
    F.data.startswith("own:user_list:")
)
async def cb_user_list(
    callback: CallbackQuery,
    **kwargs
) -> None:
    """Show paginated users list."""
    page = int(callback.data.split(":")[-1])
    page_size = 10

    async with get_session() as session:
        repo = UserRepository(session)
        users = await repo.get_all(
            limit=page_size,
            offset=page * page_size
        )

    if not users:
        await callback.answer(
            "No users on this page",
            show_alert=True
        )
        return

    text = (
        f"📋 <b>ALL USERS</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"Page {page + 1}"
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_users_list_kb(
                users, page, page_size
            )
        )
    except Exception:
        pass

    await callback.answer()


# ━━━ USER SEARCH ━━━

@users_router.callback_query(
    F.data == "own:user_search"
)
async def cb_user_search(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs
) -> None:
    """Prompt for user ID to search."""
    text = (
        "🔍 <b>SEARCH USER</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Send the Telegram User ID:"
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_owner_back_kb(
                "own:users"
            )
        )
    except Exception:
        pass

    await state.set_state(
        UserSearchStates.waiting_user_id
    )
    await callback.answer()


@users_router.message(
    UserSearchStates.waiting_user_id,
    F.text
)
async def msg_search_id(
    message: Message,
    state: FSMContext,
    **kwargs
) -> None:
    """Process search ID."""
    tg_id = validate_telegram_id(message.text)

    if not tg_id:
        await message.answer(
            "❌ Invalid ID. Send a number."
        )
        return

    async with get_session() as session:
        repo = UserRepository(session)
        user = await repo.get_by_telegram_id(
            tg_id
        )

    await state.clear()

    if not user:
        await message.answer(
            "❌ User not found.",
            reply_markup=get_owner_back_kb(
                "own:users"
            )
        )
        return

    await _show_user(message, user)


# ━━━ USER VIEW ━━━

@users_router.callback_query(
    F.data.startswith("own:user_view:")
)
async def cb_user_view(
    callback: CallbackQuery,
    **kwargs
) -> None:
    """View single user (by internal ID)."""
    user_id = int(callback.data.split(":")[-1])

    async with get_session() as session:
        repo = UserRepository(session)
        user = await repo.get_by_id(user_id)

    if not user:
        await callback.answer(
            "❌ Not found",
            show_alert=True
        )
        return

    await _show_user(
        callback.message, user, edit=True
    )
    await callback.answer()


async def _show_user(
    message: Message,
    user,
    edit: bool = False
) -> None:
    """Display user details."""
    async with get_session() as session:
        acc_repo = AccountRepository(session)
        accounts = (
            await acc_repo.get_user_accounts(
                user.id
            )
        )

        txn_repo = TransactionRepository(session)
        total_spent = (
            await txn_repo.get_total_spent(
                user.id
            )
        )

    name = escape_html(
        user.first_name or "Unknown"
    )
    username = (
        f"@{escape_html(user.username)}"
        if user.username else "none"
    )
    status = (
        "🚫 Banned" if user.is_banned
        else "✅ Active"
    )

    text = (
        f"👤 <b>USER DETAILS</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 ID: <code>{user.telegram_id}</code>\n"
        f"👤 Name: {name}\n"
        f"📛 {username}\n"
        f"📅 Joined: {format_date(user.joined_date)}\n"
        f"💰 Balance: <code>"
        f"{format_money(user.wallet_balance)}</code>\n"
        f"📦 Purchased: <code>"
        f"{len(accounts)}</code>\n"
        f"📊 Total Spent: <code>"
        f"{format_money(total_spent)}</code>\n"
        f"🌍 Lang: <code>{user.language_code}"
        f"</code>\n"
        f"🔒 Status: {status}"
    )

    kb = get_user_view_kb(
        user.id, user.is_banned
    )

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


# ━━━ BAN / UNBAN ━━━

@users_router.callback_query(
    F.data.startswith("own:user_ban:")
)
async def cb_ban_user(
    callback: CallbackQuery,
    **kwargs
) -> None:
    """Ban user."""
    user_id = int(callback.data.split(":")[-1])

    async with get_session() as session:
        repo = UserRepository(session)
        await repo.ban(user_id)

    await callback.answer(
        "🚫 User banned",
        show_alert=True
    )

    log.info(
        f"🚫 Banned: user={user_id} by "
        f"{callback.from_user.id}"
    )

    await cb_user_view(callback)


@users_router.callback_query(
    F.data.startswith("own:user_unban:")
)
async def cb_unban_user(
    callback: CallbackQuery,
    **kwargs
) -> None:
    """Unban user."""
    user_id = int(callback.data.split(":")[-1])

    async with get_session() as session:
        repo = UserRepository(session)
        await repo.unban(user_id)

    await callback.answer(
        "✅ User unbanned",
        show_alert=True
    )

    log.info(
        f"✅ Unbanned: user={user_id} by "
        f"{callback.from_user.id}"
    )

    await cb_user_view(callback)


# ━━━ MESSAGE USER ━━━

@users_router.callback_query(
    F.data.startswith("own:user_msg:")
)
async def cb_msg_user(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs
) -> None:
    """Prompt to send message to user."""
    user_id = int(callback.data.split(":")[-1])

    await state.update_data(
        target_user_id=user_id
    )

    text = (
        "💬 <b>SEND MESSAGE</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Send the message you want\n"
        "to forward to this user:"
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_owner_back_kb(
                f"own:user_view:{user_id}"
            )
        )
    except Exception:
        pass

    await state.set_state(
        UserSearchStates.waiting_message
    )
    await callback.answer()


@users_router.message(
    UserSearchStates.waiting_message,
    F.text
)
async def msg_send_to_user(
    message: Message,
    state: FSMContext,
    **kwargs
) -> None:
    """Forward message to user."""
    data = await state.get_data()
    user_id = data.get("target_user_id")

    if not user_id:
        await state.clear()
        return

    async with get_session() as session:
        repo = UserRepository(session)
        user = await repo.get_by_id(user_id)

    if not user:
        await message.answer("❌ User not found")
        await state.clear()
        return

    text = (
        f"📨 <b>Message from Admin</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"{escape_html(message.text)}"
    )

    try:
        await bot.send_message(
            chat_id=user.telegram_id,
            text=text
        )
        await message.answer(
            "✅ Message sent successfully.",
            reply_markup=get_owner_back_kb(
                "own:users"
            )
        )
    except TelegramAPIError as e:
        await message.answer(
            f"❌ Failed: {e}",
            reply_markup=get_owner_back_kb(
                "own:users"
            )
        )

    await state.clear()


# ━━━ BANNED USERS LIST ━━━

@users_router.callback_query(
    F.data == "own:user_banned"
)
async def cb_banned_users(
    callback: CallbackQuery,
    **kwargs
) -> None:
    """Show banned users."""
    async with get_session() as session:
        from sqlalchemy import select
        from bot.database.models import User
        result = await session.execute(
            select(User)
            .where(User.is_banned == True)
            .limit(50)
        )
        banned = list(result.scalars().all())

    if not banned:
        await callback.answer(
            "✅ No banned users",
            show_alert=True
        )
        return

    text = (
        f"🚫 <b>BANNED USERS</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"Total: <code>{len(banned)}</code>"
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_users_list_kb(
                banned, page=0, page_size=10
            )
        )
    except Exception:
        pass

    await callback.answer()


# ━━━ TOP BUYERS ━━━

@users_router.callback_query(
    F.data == "own:user_top"
)
async def cb_top_buyers(
    callback: CallbackQuery,
    **kwargs
) -> None:
    """Show top buyers by spending."""
    async with get_session() as session:
        from sqlalchemy import desc, func, select
        from bot.database.models import (
            Account, AccountStatus, User
        )
        result = await session.execute(
            select(
                User,
                func.sum(Account.price).label(
                    "spent"
                )
            )
            .join(
                Account,
                Account.sold_to == User.id
            )
            .where(
                Account.status ==
                AccountStatus.SOLD
            )
            .group_by(User.id)
            .order_by(desc("spent"))
            .limit(10)
        )
        rows = list(result.all())

    if not rows:
        await callback.answer(
            "No buyers yet",
            show_alert=True
        )
        return

    text = (
        "💰 <b>TOP 10 BUYERS</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
    )

    for i, (user, spent) in enumerate(rows, 1):
        name = escape_html(
            user.first_name or user.username
            or str(user.telegram_id)
        )
        text += (
            f"\n{i}. {name} — "
            f"<code>{format_money(spent)}</code>"
        )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_owner_back_kb(
                "own:users"
            )
        )
    except Exception:
        pass

    await callback.answer()


# ━━━ VIEW USER'S ACCOUNTS ━━━

@users_router.callback_query(
    F.data.startswith("own:user_accs:")
)
async def cb_user_accounts(
    callback: CallbackQuery,
    **kwargs
) -> None:
    """Show accounts purchased by user."""
    user_id = int(callback.data.split(":")[-1])

    async with get_session() as session:
        acc_repo = AccountRepository(session)
        accounts = (
            await acc_repo.get_user_accounts(
                user_id
            )
        )

    if not accounts:
        await callback.answer(
            "No accounts purchased",
            show_alert=True
        )
        return

    text = (
        f"📦 <b>USER'S ACCOUNTS</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"Total: <code>{len(accounts)}</code>\n"
    )

    for acc in accounts[:15]:
        flag = get_flag(acc.country_code)
        text += (
            f"\n{flag} <code>{acc.phone}</code>"
        )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_owner_back_kb(
                f"own:user_view:{user_id}"
            )
        )
    except Exception:
        pass

    await callback.answer()


# ━━━ ADD BALANCE TO USER ━━━

@users_router.callback_query(
    F.data.startswith("own:user_addbal:")
)
async def cb_add_balance_init(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs
) -> None:
    """Start add balance flow."""
    user_id = int(callback.data.split(":")[-1])

    await state.update_data(
        target_user_id=user_id
    )

    text = (
        "💰 <b>ADD BALANCE</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Enter amount to credit:"
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_owner_back_kb(
                f"own:user_view:{user_id}"
            )
        )
    except Exception:
        pass

    await state.set_state(
        WalletAdminStates.waiting_amount
    )
    await callback.answer()


@users_router.message(
    WalletAdminStates.waiting_amount,
    F.text
)
async def msg_user_addbal(
    message: Message,
    state: FSMContext,
    **kwargs
) -> None:
    """Process amount for user balance add."""
    amount = validate_amount(message.text)

    if not amount:
        await message.answer(
            "❌ Invalid amount."
        )
        return

    data = await state.get_data()
    target_user_id = data.get(
        "target_user_id"
    )

    if not target_user_id:
        await state.clear()
        return

    async with get_session() as session:
        owner_repo = OwnerRepository(session)
        owner = await owner_repo.get_by_telegram_id(
            message.from_user.id
        )

        wallet = WalletService(session)
        success, msg = await wallet.credit(
            user_id=target_user_id,
            amount=amount,
            description=(
                f"Credit by admin @"
                f"{message.from_user.username or owner.id}"
            ),
            done_by=owner.id
        )

        user_repo = UserRepository(session)
        user = await user_repo.get_by_id(
            target_user_id
        )

    await state.clear()

    if not success:
        await message.answer(
            f"❌ {msg}",
            reply_markup=get_owner_back_kb(
                f"own:user_view:{target_user_id}"
            )
        )
        return

    await message.answer(
        f"✅ {format_money(amount)} credited.\n"
        f"New balance: "
        f"{format_money(user.wallet_balance)}",
        reply_markup=get_owner_back_kb(
            f"own:user_view:{target_user_id}"
        )
    )

    # Notify user
    try:
        text = i18n.get(
            "balance_added",
            lang=user.language_code,
            amount=format_money(amount),
            balance=format_money(
                user.wallet_balance
            )
        )
        await bot.send_message(
            chat_id=user.telegram_id,
            text=text
        )
    except Exception:
        pass

    log.info(
        f"💰 Manual credit: "
        f"user={target_user_id}, "
        f"amount={amount}, by={owner.id}"
    )