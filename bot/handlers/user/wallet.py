"""
Wallet handler.
Wallet view and recent transactions.
"""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from bot.database.engine import get_session
from bot.database.models import TransactionType
from bot.database.repositories import (
    AccountRepository,
    TransactionRepository,
    UserRepository,
)
from bot.keyboards.user.wallet import get_wallet_kb
from bot.locales.i18n import i18n
from bot.utils.formatters import format_datetime, format_money
from bot.utils.helpers import escape_html

wallet_router = Router(name="wallet")


async def show_wallet(
    message: Message,
    lang: str = "en",
) -> None:
    """Display wallet screen."""

    user = message.from_user

    async with get_session() as session:
        user_repo = UserRepository(session)
        db_user = await user_repo.get_by_telegram_id(user.id)

        acc_repo = AccountRepository(session)
        accounts = await acc_repo.get_user_accounts(db_user.id)

        txn_repo = TransactionRepository(session)
        total_spent = await txn_repo.get_total_spent(db_user.id)
        recent = await txn_repo.get_user_transactions(
            db_user.id, limit=5
        )

    text = (
        f"💼 <b>My Wallet</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 Balance: <b>₹{format_money(db_user.wallet_balance)}</b>\n"
        f"💸 Total Spent: <b>₹{format_money(total_spent)}</b>\n"
        f"📦 Accounts: <b>{len(accounts)}</b>\n"
    )

    if recent:
        text += "\n━━ RECENT ━━\n"
        for txn in recent:
            sign = (
                "+"
                if txn.type == TransactionType.CREDIT
                else "-"
            )
            text += (
                f"\n{sign}₹{format_money(txn.amount)} | "
                f"{escape_html(txn.description[:30])}\n"
                f"📅 {format_datetime(txn.created_at)}"
            )
    else:
        text += "\n\n📭 No transactions yet."

    await message.answer(
        text,
        reply_markup=get_wallet_kb(lang),
    )


@wallet_router.callback_query(F.data == "wallet:view")
async def cb_view_wallet(
    callback: CallbackQuery,
    lang: str = "en",
    **kwargs,
) -> None:
    """Refresh wallet view."""

    await show_wallet(callback.message, lang)
    await callback.answer()