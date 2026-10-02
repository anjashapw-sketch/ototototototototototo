"""
Owner dashboard handler.
Main owner panel with stats.
"""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database.engine import get_session
from bot.database.repositories import (
    StatsRepository
)
from bot.filters.is_owner import IsOwner
from bot.keyboards.owner.dashboard import (
    get_dashboard_kb
)
from bot.keyboards.owner.main_menu import (
    OWNER_MENU,
    get_owner_main_menu
)
from bot.keyboards.user.main_menu import (
    get_main_menu
)
from bot.utils.formatters import format_money


dashboard_router = Router(name="own_dashboard")
dashboard_router.message.filter(IsOwner())
dashboard_router.callback_query.filter(IsOwner())


def _build_dashboard_text(stats: dict) -> str:
    """Build dashboard text from stats."""
    return (
        "👑 <b>GHOST MARKET — ADMIN</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "━━ QUICK STATS ━━\n\n"
        f"📦 Total Stock: <code>"
        f"{stats['total_stock']}</code>\n"
        f"✅ Active: <code>"
        f"{stats['total_stock'] - stats['dead_sessions']}"
        f"</code>\n"
        f"❌ Dead: <code>"
        f"{stats['dead_sessions']}</code>\n"
        f"👥 Total Users: <code>"
        f"{stats['total_users']}</code>\n"
        f"🚫 Banned: <code>"
        f"{stats['banned_users']}</code>\n"
        f"💰 Total Sold: <code>"
        f"{stats['total_sold']}</code>\n"
        f"📊 Today Sold: <code>"
        f"{stats['today_sold']}</code>\n"
    )


@dashboard_router.message(
    F.text == OWNER_MENU["dashboard"]
)
async def msg_dashboard(
    message: Message,
    state: FSMContext,
    **kwargs
) -> None:
    """Show owner dashboard."""
    await state.clear()

    async with get_session() as session:
        repo = StatsRepository(session)
        stats = await repo.get_dashboard_stats()

    text = _build_dashboard_text(stats)

    await message.answer(
        text,
        reply_markup=get_dashboard_kb()
    )


@dashboard_router.callback_query(
    F.data == "own:dashboard"
)
async def cb_dashboard(
    callback: CallbackQuery,
    state: FSMContext,
    **kwargs
) -> None:
    """Dashboard callback."""
    await state.clear()

    async with get_session() as session:
        repo = StatsRepository(session)
        stats = await repo.get_dashboard_stats()

    text = _build_dashboard_text(stats)

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_dashboard_kb()
        )
    except Exception:
        pass

    await callback.answer()


@dashboard_router.message(
    F.text == OWNER_MENU["user_mode"]
)
async def msg_user_mode(
    message: Message,
    state: FSMContext,
    lang: str = "en",
    **kwargs
) -> None:
    """Switch owner to user view."""
    await state.clear()
    await message.answer(
        "🔄 Switched to user view.\n"
        "Use the menu below.",
        reply_markup=get_main_menu(lang)
    )