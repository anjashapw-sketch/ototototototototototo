"""
Force sub check job.
Periodically verify bot is still admin in
all force sub channels.
"""

from bot.database.engine import get_session
from bot.database.repositories import (
    ForceSubRepository
)
from bot.services.force_sub_service import (
    force_sub_service
)
from bot.services.notification import (
    notification_service
)
from bot.utils.logger import log


async def force_sub_check_job() -> None:
    """Recheck bot admin in all channels."""
    log.info("⏰ Force sub check job started")

    async with get_session() as session:
        repo = ForceSubRepository(session)
        channels = await repo.get_all_active()

    if not channels:
        log.info("ℹ️ No force sub channels")
        return

    log.info(
        f"⏳ Checking {len(channels)} channels"
    )

    issues = []

    for channel in channels:
        try:
            is_admin, msg, _ = (
                await force_sub_service
                .verify_channel(channel.chat_id)
            )
        except Exception as e:
            log.warning(
                f"Force sub check error "
                f"{channel.chat_id}: {e}"
            )
            is_admin = False
            msg = str(e)

        # Update status if changed
        if channel.is_bot_admin != is_admin:
            async with get_session() as session:
                repo = ForceSubRepository(
                    session
                )
                await repo.update_bot_admin_status(
                    channel.id, is_admin
                )

            if not is_admin:
                issues.append((channel, msg))

    # Notify if issues
    if issues:
        text = (
            f"⚠️ <b>FORCE SUB ISSUES</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"Bot lost admin in:\n"
        )
        for ch, reason in issues[:5]:
            text += (
                f"\n❌ {ch.name}\n"
                f"   Reason: {reason[:50]}"
            )

        await notification_service.notify_owners(
            text=text
        )

        log.warning(
            f"⚠️ {len(issues)} force sub issues"
        )
    else:
        log.info(
            "✅ All force sub channels OK"
        )