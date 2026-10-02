"""User handlers package."""

from bot.handlers.user.start import (
    start_router
)
from bot.handlers.user.force_sub_check import (
    force_sub_router
)
from bot.handlers.user.shop import shop_router
from bot.handlers.user.purchase import (
    purchase_router
)
from bot.handlers.user.wallet import (
    wallet_router
)
from bot.handlers.user.wallet_request import (
    wallet_request_router
)
from bot.handlers.user.my_accounts import (
    my_accounts_router
)
from bot.handlers.user.view_otp import (
    view_otp_router
)
from bot.handlers.user.remove_device import (
    remove_device_router
)
from bot.handlers.user.profile import (
    profile_router
)
from bot.handlers.user.language import (
    language_router
)
from bot.handlers.user.support import (
    support_router
)
from bot.handlers.user.about import (
    about_router
)

__all__ = [
    "start_router",
    "force_sub_router",
    "shop_router",
    "purchase_router",
    "wallet_router",
    "wallet_request_router",
    "my_accounts_router",
    "view_otp_router",
    "remove_device_router",
    "profile_router",
    "language_router",
    "support_router",
    "about_router"
]