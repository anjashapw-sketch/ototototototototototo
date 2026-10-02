"""
Keyboard builder with color support.
Uses ButtonStyle for colored buttons.
"""

from typing import List, Optional

from aiogram.enums import ButtonStyle
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup
)


# ━━━ COLOR SHORTCUTS ━━━
GREEN = ButtonStyle.SUCCESS
RED = ButtonStyle.DANGER
BLUE = ButtonStyle.PRIMARY


def btn(
    text: str,
    callback_data: Optional[str] = None,
    url: Optional[str] = None,
    style: ButtonStyle = BLUE
) -> InlineKeyboardButton:
    """
    Create colored inline button.

    Args:
        text: Button text
        callback_data: Callback data
        url: URL (if URL button)
        style: BLUE/GREEN/RED

    Returns:
        InlineKeyboardButton
    """
    if url:
        return InlineKeyboardButton(
            text=text,
            url=url,
            style=style
        )
    return InlineKeyboardButton(
        text=text,
        callback_data=callback_data or "noop",
        style=style
    )


def green(
    text: str,
    callback_data: str
) -> InlineKeyboardButton:
    """Shortcut for green button."""
    return btn(text, callback_data, style=GREEN)


def red(
    text: str,
    callback_data: str
) -> InlineKeyboardButton:
    """Shortcut for red button."""
    return btn(text, callback_data, style=RED)


def blue(
    text: str,
    callback_data: str
) -> InlineKeyboardButton:
    """Shortcut for blue button."""
    return btn(text, callback_data, style=BLUE)


def url_btn(
    text: str,
    url: str,
    style: ButtonStyle = BLUE
) -> InlineKeyboardButton:
    """Shortcut for URL button."""
    return btn(text, url=url, style=style)


def build_kb(
    rows: List[List[InlineKeyboardButton]]
) -> InlineKeyboardMarkup:
    """Build inline keyboard from rows."""
    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


def build_reply_kb(
    rows: List[List[str]],
    resize: bool = True,
    persistent: bool = True
) -> ReplyKeyboardMarkup:
    """
    Build reply keyboard from text rows.

    Args:
        rows: List of rows (each row = list)
        resize: Resize to fit
        persistent: Always show

    Returns:
        ReplyKeyboardMarkup
    """
    keyboard = [
        [KeyboardButton(text=text) for text in row]
        for row in rows
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=resize,
        is_persistent=persistent
    )


def back_btn(
    text: str = "🔙 Back",
    callback_data: str = "back"
) -> InlineKeyboardButton:
    """Standard back button (blue)."""
    return blue(text, callback_data)


def confirm_cancel_row(
    confirm_text: str = "✅ Confirm",
    cancel_text: str = "❌ Cancel",
    confirm_cb: str = "confirm",
    cancel_cb: str = "cancel"
) -> List[InlineKeyboardButton]:
    """Standard confirm/cancel row."""
    return [
        green(confirm_text, confirm_cb),
        red(cancel_text, cancel_cb)
    ]