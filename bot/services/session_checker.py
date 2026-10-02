"""
Session checker service.
Batch verifies session health for accounts.
Used by scheduler & manual checks.
"""

import asyncio
from typing import List, Tuple

from bot.database.engine import get_session
from bot.database.models import Account
from bot.database.repositories import (
    AccountRepository,
    SettingsRepository
)
from bot.services.notification import (
    notification_service
)
from bot.services.otp_reader import otp_reader
from bot.utils.logger import log


class CheckerResult:
    """Result of bulk session check."""

    def __init__(self):
        self.total: int = 0
        self.alive: int = 0
        self.dead: int = 0
        self.dead_accounts: List[Account] = []


class SessionChecker:
    """Batch session health checker."""

    @staticmethod
    async def check_one(
        account: Account
    ) -> bool:
        """
        Check single account session.

        Args:
            account: Account model

        Returns:
            True if alive
        """
        try:
            return await otp_reader.check_alive(
                account
            )
        except Exception as e:
            log.warning(
                f"Check error: acc={account.id}, "
                f"err={e}"
            )
            return False

    @staticmethod
    async def check_all_stock(
        delay: float = 1.0,
        notify_owners: bool = True
    ) -> CheckerResult:
        """
        Check all in-stock accounts.

        Args:
            delay: Delay between checks
            notify_owners: Alert on dead

        Returns:
            CheckerResult
        """
        result = CheckerResult()

        async with get_session() as session:
            repo = AccountRepository(session)
            accounts = (
                await repo.get_all_alive_sessions()
            )

        result.total = len(accounts)
        log.info(
            f"📊 Session check: "
            f"{result.total} accounts"
        )

        for account in accounts:
            is_alive = (
                await SessionChecker.check_one(
                    account
                )
            )

            if is_alive:
                result.alive += 1
            else:
                result.dead += 1
                result.dead_accounts.append(
                    account
                )

                # Mark as dead in DB
                async with get_session() as s:
                    acc_repo = (
                        AccountRepository(s)
                    )
                    await acc_repo.mark_session_dead(
                        account.id
                    )

            await asyncio.sleep(delay)

        log.info(
            f"📊 Result: alive={result.alive}, "
            f"dead={result.dead}"
        )

        # Notify owners of dead sessions
        if (
            notify_owners
            and result.dead_accounts
        ):
            await SessionChecker._notify_dead(
                result.dead_accounts
            )

        return result

    @staticmethod
    async def check_low_stock(
        threshold: int = None
    ) -> List[Tuple[str, str, int]]:
        """
        Find countries with low stock.

        Args:
            threshold: Min stock count

        Returns:
            List of (code, name, count)
            below threshold
        """
        async with get_session() as session:
            settings_repo = SettingsRepository(
                session
            )
            if threshold is None:
                threshold = (
                    await settings_repo.get_int(
                        settings_repo
                        .KEY_LOW_STOCK_THRESHOLD,
                        default=5
                    )
                )

            acc_repo = AccountRepository(session)
            countries = (
                await acc_repo
                .get_stock_by_country()
            )

        low_stock = [
            (code, name, count)
            for code, name, count in countries
            if count < threshold
        ]

        return low_stock

    @staticmethod
    async def _notify_dead(
        dead_accounts: List[Account]
    ) -> None:
        """Notify owners of dead sessions."""
        from bot.utils.flag_emoji import (
            get_flag
        )

        text_lines = [
            "❌ <b>DEAD SESSIONS DETECTED</b>",
            "━━━━━━━━━━━━━━━━━━",
            "",
            f"📊 Total dead: "
            f"<code>{len(dead_accounts)}</code>",
            ""
        ]

        for acc in dead_accounts[:10]:
            flag = get_flag(acc.country_code)
            text_lines.append(
                f"{flag} <code>{acc.phone}</code>"
            )

        if len(dead_accounts) > 10:
            text_lines.append(
                f"\n...and "
                f"{len(dead_accounts) - 10} more"
            )

        await notification_service.notify_owners(
            text="\n".join(text_lines),
            setting_key=(
                SettingsRepository
                .KEY_SESSION_CHECK
            )
        )


# ━━━ SINGLETON ━━━
session_checker = SessionChecker()