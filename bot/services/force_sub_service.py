"""
Force subscription service.
Verifies channels & bot admin status.
"""

from typing import Optional, Tuple

from aiogram.exceptions import (
    TelegramAPIError, TelegramBadRequest
)

from bot.database.models.force_sub_channel \
    import ChannelType
from bot.loader import bot
from bot.utils.logger import log


class ForceSubService:
    """Service for channel verification."""

    @staticmethod
    async def verify_channel(
        chat_id: int
    ) -> Tuple[bool, str, dict]:
        """
        Verify bot is admin in channel.

        Args:
            chat_id: Numeric chat ID

        Returns:
            (is_admin, error_msg, chat_info)
        """
        try:
            chat = await bot.get_chat(chat_id)
        except TelegramBadRequest:
            return (
                False,
                "Chat not found. Make sure "
                "bot is added.",
                {}
            )
        except TelegramAPIError as e:
            return (
                False,
                f"API error: {e}",
                {}
            )

        try:
            me = await bot.get_me()
            member = await bot.get_chat_member(
                chat_id=chat_id,
                user_id=me.id
            )

            if member.status not in (
                "administrator", "creator"
            ):
                return (
                    False,
                    "Bot is not admin. "
                    "Promote bot first.",
                    {}
                )

        except TelegramAPIError as e:
            return (
                False,
                f"Member check failed: {e}",
                {}
            )

        info = {
            "title": chat.title or "Unknown",
            "username": chat.username,
            "members_count": (
                await bot.get_chat_member_count(
                    chat_id
                )
                if hasattr(
                    bot, "get_chat_member_count"
                )
                else 0
            )
        }

        return (True, "OK", info)

    @staticmethod
    async def resolve_public_username(
        username: str
    ) -> Tuple[Optional[int], Optional[str]]:
        """
        Resolve public username to chat ID.

        Returns:
            (chat_id, title) or (None, None)
        """
        clean = (
            username.lstrip("@")
            .replace("https://t.me/", "")
            .replace("t.me/", "")
            .strip()
        )

        try:
            chat = await bot.get_chat(
                f"@{clean}"
            )
            return (chat.id, chat.title)
        except (
            TelegramBadRequest,
            TelegramAPIError
        ) as e:
            log.warning(
                f"Username resolve failed: {e}"
            )
            return (None, None)


# ━━━ SINGLETON ━━━
force_sub_service = ForceSubService()