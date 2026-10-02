"""
Bot and Dispatcher instances.
Centralized initialization.
"""

from aiogram import Bot, Dispatcher
from aiogram.client.default import (
    DefaultBotProperties
)
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import (
    MemoryStorage
)

from bot.config import settings


# ━━━ BOT INSTANCE ━━━
bot = Bot(
    token=settings.bot_token,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML,
        link_preview_is_disabled=True
    )
)

# ━━━ FSM STORAGE ━━━
storage = MemoryStorage()

# ━━━ DISPATCHER ━━━
dp = Dispatcher(storage=storage)