"""
Global error handler.
Catches all unhandled exceptions.
"""

from aiogram import Router
from aiogram.types import ErrorEvent

from bot.utils.logger import log


errors_router = Router(name="errors")


@errors_router.errors()
async def global_error_handler(
    event: ErrorEvent
) -> bool:
    """
    Handle all uncaught errors.

    Returns:
        True to mark as handled
    """
    exception = event.exception
    update = event.update

    log.error(
        f"❌ Unhandled error: "
        f"{type(exception).__name__}: "
        f"{exception}"
    )
    log.exception(exception)

    # Try to notify user
    try:
        if update.message:
            await update.message.answer(
                "❌ Something went wrong.\n"
                "Please try again later."
            )
        elif update.callback_query:
            await update.callback_query.answer(
                "❌ Error. Please try again.",
                show_alert=True
            )
    except Exception as e:
        log.warning(
            f"Failed to notify user: {e}"
        )

    return True