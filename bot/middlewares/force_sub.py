"""
Force subscription middleware.

Blocks user actions until they join required
channels. Owners are bypassed automatically.
"""

from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
)

from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (
    CallbackQuery,
    Message,
    TelegramObject,
)

from bot.database.engine import get_session
from bot.database.repositories import (
    ForceSubRepository,
    OwnerRepository,
    SettingsRepository,
)
from bot.loader import bot
from bot.utils.logger import log


# Commands that always bypass force sub
BYPASS_COMMANDS = {"/start"}


class ForceSubMiddleware(BaseMiddleware):
    """
    Force subscription check middleware.

    Workflow:
        1. If force sub disabled → pass
        2. If user is owner → pass
        3. If no channels configured → pass
        4. If user is on fsub:* callback → pass
        5. Check all channels for membership
        6. If not joined → BLOCK + show screen
        7. If joined all → pass to handler
    """

    async def __call__(
        self,
        handler: Callable[
            [TelegramObject, Dict[str, Any]],
            Awaitable[Any],
        ],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = event.from_user
        if not user:
            return await handler(event, data)

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━
        # BYPASS: Force sub verify clicks
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━
        if isinstance(event, CallbackQuery):
            if (
                event.data
                and event.data.startswith("fsub:")
            ):
                return await handler(event, data)

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Check settings + owner
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━
        async with get_session() as session:
            # Skip if force sub disabled
            settings_repo = SettingsRepository(
                session
            )
            enabled = (
                await settings_repo.get_bool(
                    settings_repo.KEY_FORCE_SUB,
                    default=False,
                )
            )
            if not enabled:
                return await handler(event, data)

            # Skip for owners
            owner_repo = OwnerRepository(session)
            if await owner_repo.is_owner(
                user.id
            ):
                return await handler(event, data)

            # Get active channels
            fsub_repo = ForceSubRepository(
                session
            )
            channels = (
                await fsub_repo.get_all_active()
            )

        # No channels configured = pass
        if not channels:
            return await handler(event, data)

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Check membership in each channel
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━
        not_joined: List = []

        for channel in channels:
            try:
                member = (
                    await bot.get_chat_member(
                        chat_id=channel.chat_id,
                        user_id=user.id,
                    )
                )
                if member.status in (
                    "left",
                    "kicked",
                ):
                    not_joined.append(channel)

            except TelegramBadRequest:
                # User never joined
                not_joined.append(channel)

            except Exception as e:
                log.warning(
                    f"Force sub check error "
                    f"for channel {channel.chat_id}: "
                    f"{e}"
                )
                not_joined.append(channel)

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━
        # BLOCK if not joined all
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━
        if not_joined:
            await _show_force_sub_screen(
                event=event,
                channels=not_joined,
                all_channels=channels,
            )
            # ⛔ Block — don't call handler
            return

        # ✅ All channels joined → pass
        return await handler(event, data)


async def _show_force_sub_screen(
    event: TelegramObject,
    channels: list,
    all_channels: list,
) -> None:
    """
    Show force sub join screen to blocked user.

    Args:
        event: Triggering event
        channels: Channels user hasn't joined
        all_channels: All required channels
    """
    from bot.keyboards.user.force_sub import (
        get_force_sub_kb,
    )
    from bot.locales.i18n import i18n

    lang = "en"

    text = i18n.get(
        "force_sub_required",
        lang=lang,
    )

    # Build status list
    if all_channels:
        text += "\n\n"
        for ch in all_channels:
            if ch in channels:
                text += f"❌ {ch.name}\n"
            else:
                text += f"✅ {ch.name}\n"

    kb = get_force_sub_kb(channels, lang)

    try:
        if isinstance(event, CallbackQuery):
            # Alert + try to edit message
            try:
                await event.answer(
                    "⚠️ Join all channels first!",
                    show_alert=True,
                )
            except Exception:
                pass

            try:
                await event.message.edit_text(
                    text,
                    reply_markup=kb,
                )
            except Exception:
                try:
                    await event.message.answer(
                        text,
                        reply_markup=kb,
                    )
                except Exception:
                    pass

        elif isinstance(event, Message):
            try:
                await event.answer(
                    text,
                    reply_markup=kb,
                )
            except Exception:
                pass

    except Exception as e:
        log.warning(
            f"Force sub screen send error: {e}"
        )