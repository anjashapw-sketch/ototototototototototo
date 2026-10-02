"""
Daily report job.
Sends daily sales summary to owners.
"""

from datetime import datetime

from bot.database.engine import get_session
from bot.database.repositories import (
    AccountRepository,
    SettingsRepository,
    StatsRepository,
    UserRepository
)
from bot.services.notification import (
    notification_service
)
from bot.utils.flag_emoji import get_flag
from bot.utils.formatters import format_money
from bot.utils.logger import log


async def daily_report_job() -> None:
    """Send daily summary to owners."""
    log.info("⏰ Daily report job started")

    async with get_session() as session:
        settings_repo = SettingsRepository(
            session
        )
        enabled = await settings_repo.get_bool(
            settings_repo.KEY_DAILY_REPORT,
            default=True
        )

    if not enabled:
        log.info(
            "⏸ Daily report disabled"
        )
        return

    async with get_session() as session:
        stats_repo = StatsRepository(session)
        acc_repo = AccountRepository(session)
        user_repo = UserRepository(session)

        # Yesterday's stats
        revenue = (
            await stats_repo
            .get_revenue_in_period(1)
        )
        sold = (
            await stats_repo
            .get_sold_count_in_period(1)
        )
        new_users = (
            await stats_repo
            .get_new_users_in_period(1)
        )

        # Current state
        in_stock = await acc_repo.count_in_stock()
        dead = await acc_repo.count_dead_sessions()
        total_users = await user_repo.count_all()

        # Top countries today
        top_countries = (
            await stats_repo
            .get_top_countries(limit=3)
        )

    today = datetime.utcnow().strftime(
        "%Y-%m-%d"
    )

    text = (
        f"📊 <b>DAILY REPORT</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📅 {today}\n\n"
        f"━━ LAST 24 HOURS ━━\n\n"
        f"📦 Sold: <code>{sold}</code>\n"
        f"💰 Revenue: <code>"
        f"{format_money(revenue)}</code>\n"
        f"👥 New Users: <code>"
        f"{new_users}</code>\n"
        f"\n━━ CURRENT STATE ━━\n\n"
        f"📦 In Stock: <code>{in_stock}</code>\n"
        f"❌ Dead Sessions: <code>"
        f"{dead}</code>\n"
        f"👥 Total Users: <code>"
        f"{total_users}</code>\n"
    )

    if top_countries:
        text += "\n━━ TOP COUNTRIES (ALL) ━━\n"
        for i, (code, name, count) in enumerate(
            top_countries, 1
        ):
            flag = get_flag(code)
            text += (
                f"\n{i}. {flag} {name} — "
                f"<code>{count}</code>"
            )

    sent = await notification_service.notify_owners(
        text=text
    )

    log.info(
        f"📊 Daily report sent to {sent} owners"
    )