"""
Notification service.
Sends notifications to owners and users.
"""

from typing import List, Optional

from aiogram.exceptions import TelegramAPIError

from bot.database.engine import get_session
from bot.database.repositories import (
    OwnerRepository,
    SettingsRepository
)
from bot.loader import bot
from bot.utils.logger import log


class NotificationService:
    """Service for sending notifications."""

    @staticmethod
    async def get_owner_ids() -> List[int]:
        """Get all owner Telegram IDs."""
        async with get_session() as session:
            repo = OwnerRepository(session)
            owners = await repo.get_all()
            return [o.telegram_id for o in owners]

    @staticmethod
    async def _check_setting(
        setting_key: Optional[str],
    ) -> bool:
        """Check if a setting is enabled."""
        if not setting_key:
            return True

        async with get_session() as session:
            repo = SettingsRepository(session)
            return await repo.get_bool(
                setting_key, default=True
            )

    @staticmethod
    async def notify_owners(
        text: str,
        setting_key: Optional[str] = None,
        reply_markup=None
    ) -> int:
        """
        Send text notification to all owners.

        Returns:
            Count of successful sends
        """
        enabled = await (
            NotificationService._check_setting(
                setting_key
            )
        )
        if not enabled:
            return 0

        owner_ids = (
            await NotificationService
            .get_owner_ids()
        )
        sent = 0

        for owner_id in owner_ids:
            try:
                await bot.send_message(
                    chat_id=owner_id,
                    text=text,
                    reply_markup=reply_markup
                )
                sent += 1
            except TelegramAPIError as e:
                log.warning(
                    f"Failed notify {owner_id}: "
                    f"{e}"
                )
            except Exception as e:
                log.error(
                    f"Notify error: {e}"
                )

        return sent

    @staticmethod
    async def notify_owners_photo(
        photo: str,
        caption: str,
        setting_key: Optional[str] = None,
        reply_markup=None,
    ) -> int:
        """
        Send photo with caption to all owners.

        Args:
            photo: file_id of the photo
            caption: Caption text
            setting_key: Setting to check
            reply_markup: Optional keyboard

        Returns:
            Count of successful sends
        """
        enabled = await (
            NotificationService._check_setting(
                setting_key
            )
        )
        if not enabled:
            return 0

        owner_ids = (
            await NotificationService
            .get_owner_ids()
        )
        sent = 0

        for owner_id in owner_ids:
            try:
                await bot.send_photo(
                    chat_id=owner_id,
                    photo=photo,
                    caption=caption,
                    reply_markup=reply_markup,
                )
                sent += 1
            except TelegramAPIError as e:
                log.warning(
                    f"Failed notify photo "
                    f"{owner_id}: {e}"
                )
                # Fallback — send text only
                try:
                    await bot.send_message(
                        chat_id=owner_id,
                        text=caption,
                        reply_markup=reply_markup,
                    )
                    sent += 1
                except Exception:
                    pass
            except Exception as e:
                log.error(
                    f"Notify photo error: {e}"
                )

        return sent

    @staticmethod
    async def notify_user(
        user_tg_id: int,
        text: str,
        reply_markup=None
    ) -> bool:
        """Send notification to single user."""
        try:
            await bot.send_message(
                chat_id=user_tg_id,
                text=text,
                reply_markup=reply_markup
            )
            return True
        except TelegramAPIError as e:
            log.warning(
                f"Failed notify user "
                f"{user_tg_id}: {e}"
            )
            return False
        except Exception as e:
            log.error(f"Notify error: {e}")
            return False


# ━━━ SINGLETON ━━━
notification_service = NotificationService()