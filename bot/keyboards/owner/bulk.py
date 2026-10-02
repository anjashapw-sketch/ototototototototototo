"""Bulk upload keyboards."""

from aiogram.types import InlineKeyboardMarkup

from bot.keyboards.builder import (
    blue, build_kb, green, red
)


def get_bulk_start_kb() -> InlineKeyboardMarkup:
    """Initial bulk upload prompt keyboard."""
    return build_kb([
        [
            green(
                "▶️ Start Processing",
                "own:bulk_start"
            )
        ],
        [
            red(
                "❌ Cancel Upload",
                "own:bulk_cancel"
            )
        ]
    ])


def get_bulk_progress_kb() -> InlineKeyboardMarkup:
    """Progress keyboard during bulk upload."""
    return build_kb([
        [
            red(
                "⏭ Skip This Number",
                "own:bulk_skip"
            )
        ],
        [
            red(
                "⏹ Stop Bulk Upload",
                "own:bulk_stop"
            )
        ]
    ])


def get_bulk_stop_confirm_kb() -> InlineKeyboardMarkup:
    """Confirm stop bulk."""
    return build_kb([
        [
            red(
                "✅ Yes, Stop",
                "own:bulk_stop_yes"
            ),
            blue(
                "❌ No, Continue",
                "own:bulk_continue"
            )
        ]
    ])


def get_bulk_done_kb() -> InlineKeyboardMarkup:
    """After bulk upload complete."""
    return build_kb([
        [
            blue("📦 View Stock", "own:stock")
        ],
        [
            blue("🔙 Dashboard", "own:dashboard")
        ]
    ])