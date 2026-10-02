"""
Main scheduler.
Manages all background jobs using APScheduler.
"""

from apscheduler.schedulers.asyncio import (
    AsyncIOScheduler
)
from apscheduler.triggers.cron import (
    CronTrigger
)
from apscheduler.triggers.interval import (
    IntervalTrigger
)

from bot.config import settings
from bot.scheduler.cleanup_job import (
    cleanup_job
)
from bot.scheduler.daily_report_job import (
    daily_report_job
)
from bot.scheduler.force_sub_check_job import (
    force_sub_check_job
)
from bot.scheduler.session_check_job import (
    session_check_job
)
from bot.utils.logger import log


# ━━━ SCHEDULER INSTANCE ━━━
scheduler = AsyncIOScheduler(
    timezone="UTC"
)


async def start() -> None:
    """Start scheduler with all jobs."""

    # ━━━ SESSION CHECK JOB ━━━
    scheduler.add_job(
        session_check_job,
        trigger=IntervalTrigger(
            seconds=(
                settings.session_check_interval
            )
        ),
        id="session_check",
        name="Session Alive Check",
        replace_existing=True,
        max_instances=1
    )

    # ━━━ FORCE SUB CHECK JOB ━━━
    scheduler.add_job(
        force_sub_check_job,
        trigger=IntervalTrigger(
            seconds=(
                settings.force_sub_check_interval
            )
        ),
        id="force_sub_check",
        name="Force Sub Channels Check",
        replace_existing=True,
        max_instances=1
    )

    # ━━━ DAILY REPORT JOB ━━━
    scheduler.add_job(
        daily_report_job,
        trigger=CronTrigger(
            hour=9, minute=0
        ),
        id="daily_report",
        name="Daily Sales Report",
        replace_existing=True,
        max_instances=1
    )

    # ━━━ CLEANUP JOB ━━━
    scheduler.add_job(
        cleanup_job,
        trigger=CronTrigger(
            hour=3, minute=0
        ),
        id="cleanup",
        name="Daily Cleanup",
        replace_existing=True,
        max_instances=1
    )

    scheduler.start()

    log.info(
        f"✅ Scheduler started with "
        f"{len(scheduler.get_jobs())} jobs"
    )

    for job in scheduler.get_jobs():
        log.info(
            f"  ├─ {job.name} "
            f"(next: {job.next_run_time})"
        )


async def stop() -> None:
    """Shutdown scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        log.info("✅ Scheduler stopped")