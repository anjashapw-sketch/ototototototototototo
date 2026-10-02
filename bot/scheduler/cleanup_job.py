"""
Cleanup job.
Daily cleanup of old logs, expired items.
"""

from datetime import datetime, timedelta
from pathlib import Path

from bot.config import settings
from bot.utils.logger import log


async def cleanup_job() -> None:
    """Daily cleanup tasks."""
    log.info("⏰ Cleanup job started")

    await _cleanup_temp_uploads()
    await _cleanup_old_logs()

    log.info("✅ Cleanup completed")


async def _cleanup_temp_uploads() -> None:
    """Remove temp upload files older than 24h."""
    uploads_dir = settings.uploads_dir

    if not uploads_dir.exists():
        return

    cutoff = (
        datetime.now().timestamp()
        - (24 * 3600)
    )

    removed = 0
    for file_path in uploads_dir.iterdir():
        if not file_path.is_file():
            continue

        if file_path.stat().st_mtime < cutoff:
            try:
                file_path.unlink()
                removed += 1
            except Exception as e:
                log.warning(
                    f"Cleanup failed "
                    f"{file_path}: {e}"
                )

    if removed:
        log.info(
            f"🧹 Removed {removed} old uploads"
        )


async def _cleanup_old_logs() -> None:
    """
    Loguru handles rotation but we 
    can clean very old .zip backups.
    """
    logs_dir = settings.logs_dir

    if not logs_dir.exists():
        return

    cutoff = (
        datetime.now()
        - timedelta(days=30)
    ).timestamp()

    removed = 0
    for file_path in logs_dir.iterdir():
        if not file_path.suffix == ".zip":
            continue

        if file_path.stat().st_mtime < cutoff:
            try:
                file_path.unlink()
                removed += 1
            except Exception as e:
                log.warning(
                    f"Log cleanup failed: {e}"
                )

    if removed:
        log.info(
            f"🧹 Removed {removed} old log zips"
        )