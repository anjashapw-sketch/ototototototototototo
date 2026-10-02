"""
Logging setup using Loguru.
Provides centralized logging.
"""

import sys
from pathlib import Path

from loguru import logger as _logger

from bot.config import settings


def setup_logger() -> None:
    """Configure Loguru logger."""
    # Remove default handler
    _logger.remove()

    # ━━━ CONSOLE OUTPUT ━━━
    _logger.add(
        sys.stdout,
        level=settings.log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}"
            "</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:"
            "<cyan>{function}</cyan>:"
            "<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        colorize=True,
        backtrace=True,
        diagnose=True
    )

    # ━━━ FILE OUTPUT ━━━
    log_path = Path(settings.log_file)
    log_path.parent.mkdir(
        parents=True, exist_ok=True
    )

    _logger.add(
        str(log_path),
        level=settings.log_level,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss} | "
            "{level: <8} | "
            "{name}:{function}:{line} - "
            "{message}"
        ),
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        backtrace=True,
        diagnose=True,
        enqueue=True
    )

    _logger.info("✅ Logger initialized")


# ━━━ EXPORT LOGGER INSTANCE ━━━
log = _logger