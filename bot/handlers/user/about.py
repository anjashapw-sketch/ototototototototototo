"""
About handler.
Shows bot information.
"""

from aiogram import Router
from aiogram.types import Message

from bot.keyboards.user.common import (
    get_back_menu_kb
)
from bot.locales.i18n import i18n


about_router = Router(name="about")


async def show_about(
    message: Message,
    lang: str = "en"
) -> None:
    """Display about info."""
    text = i18n.get("about_text", lang)

    await message.answer(
        text,
        reply_markup=get_back_menu_kb(lang)
    )