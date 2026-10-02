"""
Support handler.
Shows contact info for support.
"""

from aiogram import Router
from aiogram.types import Message

from bot.database.engine import get_session
from bot.database.repositories import (
    OwnerRepository,
    SettingsRepository,
)
from bot.keyboards.user.common import (
    get_back_menu_kb
)
from bot.locales.i18n import i18n


support_router = Router(name="support")


async def show_support(
    message: Message,
    lang: str = "en"
) -> None:
    """Display support contact info."""

    async with get_session() as session:
        # 1. Try configured support username
        settings_repo = SettingsRepository(session)
        support_username = await settings_repo.get(
            SettingsRepository.KEY_SUPPORT_USERNAME
        )

        # 2. Fallback to superadmins
        owner_repo = OwnerRepository(session)
        superadmins = (
            await owner_repo.get_all_superadmins()
        )

    contact_lines = []

    # If admin configured a support username
    if support_username and support_username.strip():
        clean = support_username.strip().lstrip("@")
        contact_lines.append(
            f"👤 Support: @{clean}"
        )
    elif superadmins:
        # Fallback to superadmins
        for admin in superadmins:
            if admin.username:
                contact_lines.append(
                    f"👑 @{admin.username}"
                )
            else:
                contact_lines.append(
                    f"👑 ID: <code>"
                    f"{admin.telegram_id}</code>"
                )

    contact = (
        "\n".join(contact_lines)
        if contact_lines
        else "Contact info not available"
    )

    text = i18n.get(
        "support_text",
        lang=lang,
        contact=contact
    )

    await message.answer(
        text,
        reply_markup=get_back_menu_kb(lang)
    )