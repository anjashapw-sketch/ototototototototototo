"""Force subscription keyboards."""

from typing import List

from aiogram.types import InlineKeyboardMarkup

from bot.database.models import ForceSubChannel
from bot.database.models.force_sub_channel \
    import ChannelType
from bot.keyboards.builder import (
    build_kb, green, url_btn
)
from bot.locales.i18n import i18n


def get_force_sub_kb(
    channels: List[ForceSubChannel],
    lang: str = "en"
) -> InlineKeyboardMarkup:
    """
    Build force sub join keyboard.

    Args:
        channels: Required channels list
        lang: User language

    Returns:
        InlineKeyboardMarkup
    """
    rows = []

    for channel in channels:
        if channel.type == ChannelType.PRIVATE:
            text = i18n.get(
                "btn_join_private",
                lang=lang,
                name=channel.name
            )
        else:
            text = i18n.get(
                "btn_join",
                lang=lang,
                name=channel.name
            )

        rows.append([
            url_btn(text, channel.invite_link)
        ])

    # Verify button
    rows.append([
        green(
            i18n.get(
                "btn_verify_membership",
                lang=lang
            ),
            "fsub:verify"
        )
    ])

    return build_kb(rows)