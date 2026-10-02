"""
Master router registration.
Registers all handler routers with dispatcher.
"""

from aiogram import Dispatcher

from bot.handlers.errors import errors_router
from bot.handlers.user import (
    start_router,
    force_sub_router,
    shop_router,
    purchase_router,
    wallet_router,
    wallet_request_router,
    my_accounts_router,
    view_otp_router,
    remove_device_router,
    profile_router,
    language_router,
    support_router,
    about_router
)
from bot.handlers.owner import (
    dashboard_router,
    add_account_router,
    bulk_upload_router,
    stock_router,
    users_router,
    wallets_router,
    admins_router,
    pricing_router,
    analytics_router,
    settings_router,
    notifications_router,
    force_sub_owner_router,
    sold_history_router,
    broadcast_router,
    notify_stock_router,
)


def register_all_routers(
    dp: Dispatcher
) -> None:
    """
    Register all routers in priority order.

    ORDER MATTERS:
    1. Errors          (catch all errors)
    2. Owner routers   (owner-specific)
    3. User routers    (user-side)
    """
    # ━━━ ERRORS (highest priority) ━━━
    dp.include_router(errors_router)

    # ━━━ OWNER ROUTERS ━━━
    dp.include_router(dashboard_router)
    dp.include_router(add_account_router)
    dp.include_router(notify_stock_router)
    dp.include_router(bulk_upload_router)
    dp.include_router(stock_router)
    dp.include_router(users_router)
    dp.include_router(wallets_router)
    dp.include_router(admins_router)
    dp.include_router(pricing_router)
    dp.include_router(analytics_router)
    dp.include_router(settings_router)
    dp.include_router(notifications_router)
    dp.include_router(force_sub_owner_router)
    dp.include_router(sold_history_router)
    dp.include_router(broadcast_router)

    # ━━━ USER ROUTERS ━━━
    dp.include_router(start_router)
    dp.include_router(force_sub_router)
    dp.include_router(shop_router)
    dp.include_router(purchase_router)
    dp.include_router(wallet_request_router)
    dp.include_router(wallet_router)
    dp.include_router(my_accounts_router)
    dp.include_router(view_otp_router)
    dp.include_router(remove_device_router)
    dp.include_router(profile_router)
    dp.include_router(language_router)
    dp.include_router(support_router)
    dp.include_router(about_router)