"""
Sold history handler.
Paginated view of all sales.
"""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database.engine import get_session
from bot.database.repositories import (
    AccountRepository,
    UserRepository
)
from bot.filters.is_owner import IsOwner
from bot.keyboards.builder import (
    blue, build_kb
)
from bot.keyboards.owner.main_menu import (
    OWNER_MENU
)
from bot.utils.flag_emoji import get_flag
from bot.utils.formatters import (
    format_datetime, format_money
)
from bot.utils.helpers import escape_html


sold_history_router = Router(name="own_sold")
sold_history_router.message.filter(IsOwner())
sold_history_router.callback_query.filter(
    IsOwner()
)


PAGE_SIZE = 10


# ━━━ ENTRY ━━━

@sold_history_router.message(
    F.text == OWNER_MENU["sold_history"]
)
async def msg_sold(
    message: Message,
    state: FSMContext,
    **kwargs
) -> None:
    """Show sold history."""
    await state.clear()
    await _show_page(message, page=0)


@sold_history_router.callback_query(
    F.data == "own:sold"
)
async def cb_sold(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs
) -> None:
    """Sold history (callback)."""
    await state.clear()
    await _show_page(
        callback.message, page=0, edit=True
    )
    await callback.answer()


@sold_history_router.callback_query(
    F.data.startswith("own:sold_p:")
)
async def cb_sold_page(
    callback: CallbackQuery,
    **kwargs
) -> None:
    """Pagination."""
    page = int(callback.data.split(":")[-1])
    await _show_page(
        callback.message, page=page, edit=True
    )
    await callback.answer()


async def _show_page(
    message: Message,
    page: int,
    edit: bool = False
) -> None:
    """Render a single page of sales."""
    async with get_session() as session:
        acc_repo = AccountRepository(session)
        accounts = await acc_repo.get_sold_history(
            limit=PAGE_SIZE,
            offset=page * PAGE_SIZE
        )
        total = await acc_repo.count_sold()

        # Resolve buyer names
        buyer_map = {}
        for acc in accounts:
            if acc.sold_to in buyer_map:
                continue
            user_repo = UserRepository(session)
            buyer = await user_repo.get_by_id(
                acc.sold_to
            )
            if buyer:
                buyer_map[acc.sold_to] = (
                    buyer.username
                    or buyer.first_name
                    or str(buyer.telegram_id)
                )

    if not accounts:
        text = (
            "📋 <b>SOLD HISTORY</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "No sales yet."
        )
        kb = build_kb([
            [blue(
                "🔙 Dashboard",
                "own:dashboard"
            )]
        ])

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
        return

    text = (
        f"📋 <b>SOLD HISTORY</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 Total Sold: <code>{total}</code>\n"
        f"📄 Page: {page + 1}\n"
    )

    for i, acc in enumerate(
        accounts, start=page * PAGE_SIZE + 1
    ):
        flag = get_flag(acc.country_code)
        buyer = buyer_map.get(
            acc.sold_to, f"#{acc.sold_to}"
        )
        text += (
            f"\n{i}. {flag} <code>{acc.phone}</code>\n"
            f"   👤 @{escape_html(buyer)} | "
            f"{format_money(acc.price)}\n"
            f"   📅 {format_datetime(acc.sold_date)}"
        )

    # Pagination buttons
    nav_row = []
    if page > 0:
        nav_row.append(
            blue(
                "◀️ Prev",
                f"own:sold_p:{page - 1}"
            )
        )

    has_next = (
        (page + 1) * PAGE_SIZE < total
    )
    if has_next:
        nav_row.append(
            blue(
                "▶️ Next",
                f"own:sold_p:{page + 1}"
            )
        )

    rows = []
    if nav_row:
        rows.append(nav_row)
    rows.append([
        blue("🔙 Dashboard", "own:dashboard")
    ])

    kb = build_kb(rows)

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