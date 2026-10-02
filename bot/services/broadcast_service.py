"""
Broadcast service.
Sends mass messages to users.
"""

import asyncio
from typing import List

from aiogram.exceptions import (
    TelegramAPIError,
    TelegramForbiddenError,
    TelegramRetryAfter
)

from bot.database.engine import get_session
from bot.database.repositories import (
    UserRepository
)
from bot.loader import bot
from bot.utils.logger import log


class BroadcastResult:
    """Result of broadcast operation."""

    def __init__(self):
        self.total: int = 0
        self.sent: int = 0
        self.failed: int = 0
        self.blocked: int = 0


class BroadcastService:
    """Mass message sender."""

    @staticmethod
    async def get_all_user_ids() -> List[int]:
        """Get all non-banned user Telegram IDs."""
        async with get_session() as session:
            from sqlalchemy import select
            from bot.database.models import User
            result = await session.execute(
                select(User.telegram_id)
                .where(User.is_banned == False)
            )
            return [
                row[0]
                for row in result.all()
            ]

    @staticmethod
    async def broadcast(
        text: str,
        delay: float = 0.05
    ) -> BroadcastResult:
        """
        Send message to all users.

        Args:
            text: Message text (HTML)
            delay: Delay between sends

        Returns:
            BroadcastResult
        """
        user_ids = (
            await BroadcastService
            .get_all_user_ids()
        )
        result = BroadcastResult()
        result.total = len(user_ids)

        for tg_id in user_ids:
            try:
                await bot.send_message(
                    chat_id=tg_id,
                    text=text
                )
                result.sent += 1
            except TelegramForbiddenError:
                result.blocked += 1
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after)
                try:
                    await bot.send_message(
                        chat_id=tg_id,
                        text=text
                    )
                    result.sent += 1
                except Exception:
                    result.failed += 1
            except TelegramAPIError as e:
                log.warning(
                    f"Broadcast fail {tg_id}: {e}"
                )
                result.failed += 1
            except Exception as e:
                log.error(
                    f"Broadcast error: {e}"
                )
                result.failed += 1

            await asyncio.sleep(delay)

        log.info(
            f"📢 Broadcast: sent={result.sent}, "
            f"failed={result.failed}, "
            f"blocked={result.blocked}"
        )
        return result


# ━━━ SINGLETON ━━━
broadcast_service = BroadcastService()