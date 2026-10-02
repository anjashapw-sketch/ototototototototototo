"""
Analytics handler.
Show stats by period.
"""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database.engine import get_session
from bot.database.repositories import (
    StatsRepository,
    UserRepository
)
from bot.filters.is_owner import IsOwner
from bot.keyboards.owner.analytics import (
    get_analytics_kb
)
from bot.keyboards.owner.main_menu import (
    OWNER_MENU
)
from bot.utils.flag_emoji import get_flag
from bot.utils.formatters import format_money


analytics_router = Router(name="own_analytics")
analytics_router.message.filter(IsOwner())
analytics_router.callback_query.filter(IsOwner())


# ━━━ ENTRY ━━━

@analytics_router.message(
    F.text == OWNER_MENU["analytics"]
)
async def msg_analytics(
    message: Message,
    state: FSMContext,
    **kwargs
) -> None:
    """Show analytics menu."""
    await state.clear()
    await _show_period(
        message, days=7
    )


@analytics_router.callback_query(
    F.data == "own:analytics"
)
async def cb_analytics(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs
) -> None:
    """Analytics callback."""
    await state.clear()
    await _show_period(
        callback.message, days=7, edit=True
    )
    await callback.answer()


# ━━━ PERIOD SELECTION ━━━

@analytics_router.callback_query(
    F.data.startswith("own:stats:")
)
async def cb_period(
    callback: CallbackQuery,
    **kwargs
) -> None:
    """Show stats for selected period."""
    period = callback.data.split(":")[-1]

    if period == "all":
        days = 36500  # ~100 years
    else:
        try:
            days = int(period)
        except ValueError:
            days = 7

    await _show_period(
        callback.message, days, edit=True
    )
    await callback.answer()


async def _show_period(
    message,
    days: int,
    edit: bool = False
) -> None:
    """Build stats text for period."""
    async with get_session() as session:
        stats_repo = StatsRepository(session)
        user_repo = UserRepository(session)

        revenue = (
            await stats_repo
            .get_revenue_in_period(days)
        )
        sold = (
            await stats_repo
            .get_sold_count_in_period(days)
        )
        new_users = (
            await stats_repo
            .get_new_users_in_period(days)
        )
        top_countries = (
            await stats_repo.get_top_countries(
                limit=5
            )
        )
        total_users = (
            await user_repo.count_all()
        )

    period_label = {
        1: "TODAY",
        7: "THIS WEEK",
        30: "THIS MONTH"
    }.get(days, "ALL TIME")

    text = (
        f"📊 <b>ANALYTICS</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"━━ {period_label} ━━\n\n"
        f"📦 Sold: <code>{sold}</code>\n"
        f"💰 Revenue: <code>"
        f"{format_money(revenue)}</code>\n"
        f"👥 New Users: <code>"
        f"{new_users}</code>\n"
        f"\n━━ OVERALL ━━\n\n"
        f"👥 Total Users: <code>"
        f"{total_users}</code>\n"
    )

    if top_countries:
        text += "\n━━ TOP COUNTRIES ━━\n"
        for i, (code, name, count) in enumerate(
            top_countries, 1
        ):
            flag = get_flag(code)
            text += (
                f"\n{i}. {flag} {name} — "
                f"<code>{count}</code> sold"
            )

    kb = get_analytics_kb()

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