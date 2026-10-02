"""Owner handlers package."""

from bot.handlers.owner.dashboard import (
    dashboard_router
)
from bot.handlers.owner.add_account import (
    add_account_router
)
from bot.handlers.owner.bulk_upload import (
    bulk_upload_router
)
from bot.handlers.owner.stock import (
    stock_router
)
from bot.handlers.owner.users import (
    users_router
)
from bot.handlers.owner.wallets import (
    wallets_router
)
from bot.handlers.owner.admins import (
    admins_router
)
from bot.handlers.owner.pricing import (
    pricing_router
)
from bot.handlers.owner.analytics import (
    analytics_router
)
from bot.handlers.owner.settings import (
    settings_router
)
from bot.handlers.owner.notifications import (
    notifications_router
)
from bot.handlers.owner.force_sub import (
    force_sub_owner_router
)
from bot.handlers.owner.sold_history import (
    sold_history_router
)
from bot.handlers.owner.broadcast import (
    broadcast_router
)
from bot.handlers.owner.notify_stock import (
    notify_stock_router
)

__all__ = [
    "dashboard_router",
    "add_account_router",
    "bulk_upload_router",
    "stock_router",
    "users_router",
    "wallets_router",
    "admins_router",
    "pricing_router",
    "analytics_router",
    "settings_router",
    "notifications_router",
    "force_sub_owner_router",
    "sold_history_router",
    "broadcast_router",
    "notify_stock_router",
]