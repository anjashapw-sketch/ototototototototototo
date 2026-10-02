"""
Stats calculator service.
High-level analytics wrapper.
Builds dashboard-friendly reports.
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.repositories import (
    StatsRepository
)


class StatsCalculator:
    """Wraps stats queries into reports."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = StatsRepository(session)

    async def get_period_summary(
        self, days: int
    ) -> Dict:
        """
        Get all stats for a period.

        Args:
            days: Period in days

        Returns:
            Dict with revenue, sold, users
        """
        return {
            "days": days,
            "revenue": (
                await self.repo
                .get_revenue_in_period(days)
            ),
            "sold": (
                await self.repo
                .get_sold_count_in_period(days)
            ),
            "new_users": (
                await self.repo
                .get_new_users_in_period(days)
            )
        }

    async def get_full_report(
        self
    ) -> Dict:
        """
        Get complete report for all periods.

        Returns:
            Dict with daily/weekly/monthly/total
        """
        dashboard = (
            await self.repo.get_dashboard_stats()
        )

        return {
            "dashboard": dashboard,
            "today": await self.get_period_summary(
                days=1
            ),
            "week": await self.get_period_summary(
                days=7
            ),
            "month": await self.get_period_summary(
                days=30
            ),
            "all_time": (
                await self.get_period_summary(
                    days=36500
                )
            ),
            "top_countries": (
                await self.repo.get_top_countries(
                    limit=5
                )
            )
        }

    async def get_daily_report_text(
        self
    ) -> str:
        """
        Build daily report for owner notif.

        Returns:
            Formatted HTML text
        """
        from bot.utils.flag_emoji import (
            get_flag
        )
        from bot.utils.formatters import (
            format_money
        )

        today = await self.get_period_summary(
            days=1
        )
        week = await self.get_period_summary(
            days=7
        )
        top = await self.repo.get_top_countries(
            limit=3
        )

        text_lines = [
            "📊 <b>DAILY REPORT</b>",
            "━━━━━━━━━━━━━━━━━━",
            "",
            f"📅 Date: "
            f"{datetime.utcnow().strftime('%Y-%m-%d')}",
            "",
            "━━ TODAY ━━",
            f"📦 Sold: <code>{today['sold']}</code>",
            f"💰 Revenue: <code>"
            f"{format_money(today['revenue'])}</code>",
            f"👥 New Users: <code>"
            f"{today['new_users']}</code>",
            "",
            "━━ THIS WEEK ━━",
            f"📦 Sold: <code>{week['sold']}</code>",
            f"💰 Revenue: <code>"
            f"{format_money(week['revenue'])}</code>"
        ]

        if top:
            text_lines.append("")
            text_lines.append(
                "━━ TOP COUNTRIES ━━"
            )
            for i, (code, name, count) in enumerate(
                top, 1
            ):
                flag = get_flag(code)
                text_lines.append(
                    f"{i}. {flag} {name} — "
                    f"<code>{count}</code>"
                )

        return "\n".join(text_lines)


# Note: This service is async-instantiated
# per call. No singleton.