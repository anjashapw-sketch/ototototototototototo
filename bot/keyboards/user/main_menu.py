"""User main menu (reply keyboard)."""

from aiogram.types import ReplyKeyboardMarkup

from bot.keyboards.builder import build_reply_kb
from bot.locales.i18n import i18n


def get_main_menu(
    lang: str = "en"
) -> ReplyKeyboardMarkup:
    """
    Build main menu reply keyboard.

    Args:
        lang: User language

    Returns:
        ReplyKeyboardMarkup
    """
    return build_reply_kb(
        rows=[
            [
                i18n.get("main_menu_shop", lang),
                i18n.get(
                    "main_menu_wallet", lang
                )
            ],
            [
                i18n.get(
                    "main_menu_accounts", lang
                ),
                i18n.get(
                    "main_menu_profile", lang
                )
            ],
            [
                i18n.get(
                    "main_menu_support", lang
                ),
                i18n.get(
                    "main_menu_about", lang
                )
            ]
        ]
    )


def get_main_menu_texts(lang: str) -> dict:
    """
    Get all main menu text mappings.
    Used for matching reply keyboard taps.
    """
    return {
        "shop": i18n.get(
            "main_menu_shop", lang
        ),
        "wallet": i18n.get(
            "main_menu_wallet", lang
        ),
        "accounts": i18n.get(
            "main_menu_accounts", lang
        ),
        "profile": i18n.get(
            "main_menu_profile", lang
        ),
        "support": i18n.get(
            "main_menu_support", lang
        ),
        "about": i18n.get(
            "main_menu_about", lang
        )
    }