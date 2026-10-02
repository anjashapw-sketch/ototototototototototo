"""
Session check job.
Verifies all stock sessions are alive.
Notifies owners of dead sessions.
"""

import asyncio
from typing import List

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
from bot.utils.flag_emoji import get_flag
from bot.utils.logger import log


async def session_check_job() -> None:
    """
    Check all in-stock sessions.
    Mark dead ones, notify owners.
    """
    log.info("⏰ Session check job started")

    # Verify if enabled in settings
    async with get_session() as session:
        repo = SettingsRepository(session)
        enabled = await repo.get_bool(
            repo.KEY_SESSION_CHECK,
            default=True
        )

    if not enabled:
        log.info(
            "⏸ Session check disabled, skipping"
        )
        return

    # Get all alive sessions
    async with get_session() as session:
        acc_repo = AccountRepository(session)
        accounts = (
            await acc_repo
            .get_all_alive_sessions()
        )

    if not accounts:
        log.info("ℹ️ No alive sessions to check")
        return

    log.info(
        f"⏳ Checking {len(accounts)} sessions..."
    )

    newly_dead: List[Account] = []

    # Check in batches to avoid overload
    batch_size = 5
    for i in range(
        0, len(accounts), batch_size
    ):
        batch = accounts[i:i + batch_size]
        tasks = [
            _check_one(acc)
            for acc in batch
        ]
        results = await asyncio.gather(
            *tasks, return_exceptions=True
        )

        for acc, is_alive in zip(batch, results):
            if isinstance(is_alive, Exception):
                log.warning(
                    f"Check error {acc.id}: "
                    f"{is_alive}"
                )
                continue
            if not is_alive:
                newly_dead.append(acc)

        # Throttle between batches
        await asyncio.sleep(2)

    # Mark dead in DB
    if newly_dead:
        async with get_session() as session:
            repo = AccountRepository(session)
            for acc in newly_dead:
                await repo.mark_session_dead(
                    acc.id
                )

        log.warning(
            f"❌ {len(newly_dead)} sessions died"
        )

        # Notify owners
        await _notify_dead_sessions(newly_dead)
    else:
        log.info(
            "✅ All sessions alive"
        )


async def _check_one(account: Account) -> bool:
    """Check single account, return True if alive."""
    try:
        return await otp_reader.check_alive(
            account
        )
    except Exception as e:
        log.warning(
            f"Session check error "
            f"acc={account.id}: {e}"
        )
        return False


async def _notify_dead_sessions(
    accounts: List[Account]
) -> None:
    """Send owner notification of dead sessions."""
    text = (
        f"⚠️ <b>DEAD SESSIONS DETECTED</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"Total: <code>{len(accounts)}</code>\n\n"
    )

    for acc in accounts[:10]:
        flag = get_flag(acc.country_code)
        text += (
            f"{flag} <code>{acc.phone}</code>\n"
        )

    if len(accounts) > 10:
        text += (
            f"\n...and "
            f"{len(accounts) - 10} more"
        )

    await notification_service.notify_owners(
        text=text
    )