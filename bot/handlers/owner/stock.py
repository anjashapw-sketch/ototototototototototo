"""
Stock management handler (owner).
View, check, remove accounts.
"""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database.engine import get_session
from bot.database.repositories import (
    AccountRepository
)
from bot.filters.is_owner import IsOwner
from bot.keyboards.owner.confirmations import (
    get_owner_back_kb
)
from bot.keyboards.owner.main_menu import (
    OWNER_MENU
)
from bot.keyboards.owner.stock import (
    get_account_view_kb,
    get_country_stock_kb,
    get_remove_account_confirm_kb,
    get_stock_overview_kb
)
from bot.services.otp_reader import otp_reader
from bot.utils.flag_emoji import get_flag
from bot.utils.formatters import (
    format_date,
    format_money,
    format_phone_pretty
)
from bot.utils.logger import log


stock_router = Router(name="own_stock")
stock_router.message.filter(IsOwner())
stock_router.callback_query.filter(IsOwner())


# ━━━ STOCK OVERVIEW ━━━

@stock_router.message(
    F.text == OWNER_MENU["stock"]
)
async def msg_stock(
    message: Message,
    state: FSMContext,
    **kwargs
) -> None:
    """Show stock overview."""
    await state.clear()
    await _show_stock_overview(message)


@stock_router.callback_query(
    F.data == "own:stock"
)
async def cb_stock(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs
) -> None:
    """Stock overview (callback)."""
    await state.clear()
    await _show_stock_overview(
        callback.message, edit=True
    )
    await callback.answer()


async def _show_stock_overview(
    message: Message,
    edit: bool = False
) -> None:
    """Build and send stock overview."""
    async with get_session() as session:
        repo = AccountRepository(session)
        countries = (
            await repo.get_stock_by_country()
        )
        total = await repo.count_in_stock()
        dead = await repo.count_dead_sessions()

    text = (
        "📦 <b>STOCK MANAGEMENT</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 Total in stock: <code>{total}</code>\n"
        f"✅ Active: <code>{total - dead}</code>\n"
        f"❌ Dead: <code>{dead}</code>"
    )

    if not countries:
        text += "\n\nNo countries in stock."

    kb = get_stock_overview_kb(countries)

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


# ━━━ COUNTRY DRILL-DOWN ━━━

@stock_router.callback_query(
    F.data.startswith("own:stock_c:")
)
async def cb_country_stock(
    callback: CallbackQuery,
    **kwargs
) -> None:
    """Show accounts in a country."""
    country_code = callback.data.split(":")[-1]

    async with get_session() as session:
        from sqlalchemy import select
        from bot.database.models import (
            Account, AccountStatus
        )
        result = await session.execute(
            select(Account)
            .where(
                Account.country_code ==
                country_code,
                Account.status ==
                AccountStatus.IN_STOCK
            )
            .order_by(Account.added_date)
        )
        accounts = list(result.scalars().all())

    if not accounts:
        await callback.answer(
            "No accounts in this country",
            show_alert=True
        )
        return

    flag = get_flag(country_code)
    text = (
        f"{flag} <b>{accounts[0].country_name}"
        f"</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"Total: <code>{len(accounts)}</code> "
        f"accounts\n"
        f"(Showing first 20)"
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_country_stock_kb(
                country_code, accounts
            )
        )
    except Exception:
        pass

    await callback.answer()


# ━━━ ACCOUNT VIEW ━━━

@stock_router.callback_query(
    F.data.startswith("own:acc_view:")
)
async def cb_account_view(
    callback: CallbackQuery,
    **kwargs
) -> None:
    """Show single account details."""
    acc_id = int(callback.data.split(":")[-1])

    async with get_session() as session:
        repo = AccountRepository(session)
        account = await repo.get_by_id(acc_id)

    if not account:
        await callback.answer(
            "❌ Account not found",
            show_alert=True
        )
        return

    flag = get_flag(account.country_code)
    pretty_phone = format_phone_pretty(
        account.phone
    )
    status = (
        "✅ Active"
        if account.session_alive
        else "❌ Dead"
    )

    text = (
        f"📱 <b>ACCOUNT "
        f"#ACC-{account.id:04d}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"📞 Phone: <code>"
        f"{pretty_phone}</code>\n"
        f"🌍 Country: {flag} "
        f"{account.country_name}\n"
        f"💰 Price: {format_money(account.price)}\n"
        f"📊 Session: {status}\n"
        f"📅 Added: {format_date(account.added_date)}\n"
        f"📌 Status: {account.status.value.upper()}"
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_account_view_kb(
                acc_id
            )
        )
    except Exception:
        pass

    await callback.answer()


# ━━━ SESSION CHECK ━━━

@stock_router.callback_query(
    F.data.startswith("own:acc_check:")
)
async def cb_check_session(
    callback: CallbackQuery,
    **kwargs
) -> None:
    """Check if session is alive."""
    acc_id = int(callback.data.split(":")[-1])

    await callback.answer(
        "⏳ Checking...",
        show_alert=False
    )

    async with get_session() as session:
        repo = AccountRepository(session)
        account = await repo.get_by_id(acc_id)

    if not account:
        await callback.answer(
            "❌ Not found",
            show_alert=True
        )
        return

    try:
        is_alive = await otp_reader.check_alive(
            account
        )
    except Exception as e:
        log.error(f"Check session error: {e}")
        is_alive = False

    # Update DB
    async with get_session() as session:
        repo = AccountRepository(session)
        if is_alive:
            from sqlalchemy import update
            from bot.database.models import (
                Account
            )
            await session.execute(
                update(Account)
                .where(Account.id == acc_id)
                .values(session_alive=True)
            )
        else:
            await repo.mark_session_dead(acc_id)

    status_emoji = "✅" if is_alive else "❌"
    status_text = (
        "ALIVE" if is_alive else "DEAD"
    )

    await callback.answer(
        f"{status_emoji} Session is "
        f"{status_text}",
        show_alert=True
    )

    # Refresh view
    await cb_account_view(callback)


# ━━━ REMOVE ACCOUNT ━━━

@stock_router.callback_query(
    F.data.startswith("own:acc_remove:")
)
async def cb_remove_init(
    callback: CallbackQuery,
    **kwargs
) -> None:
    """Confirm account removal."""
    acc_id = int(callback.data.split(":")[-1])

    text = (
        f"⚠️ <b>REMOVE ACCOUNT?</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"Account #ACC-{acc_id:04d}\n"
        f"will be permanently deleted.\n\n"
        f"This action CANNOT be undone."
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=(
                get_remove_account_confirm_kb(
                    acc_id
                )
            )
        )
    except Exception:
        pass

    await callback.answer()


@stock_router.callback_query(
    F.data.startswith("own:acc_rm_yes:")
)
async def cb_remove_confirm(
    callback: CallbackQuery,
    **kwargs
) -> None:
    """Actually delete account."""
    acc_id = int(callback.data.split(":")[-1])

    async with get_session() as session:
        repo = AccountRepository(session)
        success = await repo.delete(acc_id)

    if success:
        await callback.answer(
            "✅ Account removed",
            show_alert=True
        )
        log.info(
            f"🗑 Account removed: {acc_id} by "
            f"{callback.from_user.id}"
        )

        try:
            await callback.message.edit_text(
                "✅ Account permanently removed.",
                reply_markup=get_owner_back_kb(
                    "own:stock"
                )
            )
        except Exception:
            pass
    else:
        await callback.answer(
            "❌ Failed to remove",
            show_alert=True
        )


# ━━━ DEAD SESSIONS ━━━

@stock_router.callback_query(
    F.data == "own:stock_dead"
)
async def cb_dead_sessions(
    callback: CallbackQuery,
    **kwargs
) -> None:
    """Show dead session accounts."""
    async with get_session() as session:
        from sqlalchemy import select
        from bot.database.models import (
            Account, AccountStatus
        )
        result = await session.execute(
            select(Account)
            .where(
                Account.status ==
                AccountStatus.IN_STOCK,
                Account.session_alive == False
            )
        )
        dead_accs = list(result.scalars().all())

    if not dead_accs:
        await callback.answer(
            "✅ No dead sessions!",
            show_alert=True
        )
        return

    from bot.keyboards.builder import (
        blue, build_kb, red
    )

    rows = []
    for acc in dead_accs[:20]:
        flag = get_flag(acc.country_code)
        text = f"{flag} {acc.phone}"
        rows.append([
            blue(
                text,
                f"own:acc_view:{acc.id}"
            )
        ])

    rows.append([
        red(
            "🗑 Delete All Dead",
            "own:dead_delete_all"
        )
    ])
    rows.append([
        blue("🔙 Stock", "own:stock")
    ])

    text = (
        f"❌ <b>DEAD SESSIONS</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"Total: <code>{len(dead_accs)}</code>"
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=build_kb(rows)
        )
    except Exception:
        pass

    await callback.answer()


@stock_router.callback_query(
    F.data == "own:dead_delete_all"
)
async def cb_delete_all_dead(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs
) -> None:
    """Bulk delete dead sessions."""
    async with get_session() as session:
        from sqlalchemy import delete
        from bot.database.models import (
            Account, AccountStatus
        )
        result = await session.execute(
            delete(Account)
            .where(
                Account.status ==
                AccountStatus.IN_STOCK,
                Account.session_alive == False
            )
        )
        count = result.rowcount

    await callback.answer(
        f"✅ Deleted {count} dead sessions",
        show_alert=True
    )

    log.info(
        f"🗑 Deleted {count} dead by "
        f"{callback.from_user.id}"
    )

    await cb_stock(callback, state)