"""
Bot main entry point.
Starts the bot with all configurations.
"""

from aiogram.types import BotCommand

from bot.config import settings
from bot.loader import bot, dp
from bot.locales.i18n import i18n
from bot.utils.logger import log, setup_logger


async def set_bot_commands() -> None:
    """Set bot commands menu."""
    commands = [
        BotCommand(
            command="start",
            description="🚀 Start the bot",
        ),
        BotCommand(
            command="menu",
            description="📋 Main menu",
        ),
        BotCommand(
            command="shop",
            description="🛒 Browse accounts",
        ),
        BotCommand(
            command="wallet",
            description="💰 My wallet",
        ),
        BotCommand(
            command="myaccounts",
            description="📦 My purchased accounts",
        ),
        BotCommand(
            command="profile",
            description="👤 My profile",
        ),
        BotCommand(
            command="language",
            description="🌍 Change language",
        ),
        BotCommand(
            command="support",
            description="📞 Contact support",
        ),
    ]
    await bot.set_my_commands(commands)
    log.info("✅ Bot commands set")


async def init_database_tables() -> None:
    """Auto-create DB tables if not exist.
    Also handles schema migrations.
    """
    from sqlalchemy import text
    from bot.database.base import Base
    from bot.database.engine import engine

    # Import all models so they register
    from bot.database.models import (  # noqa
        User, Owner, Account, Transaction,
        WalletRequest, Pricing, Setting,
        BulkBatch, ForceSubChannel,
    )

    async with engine.begin() as conn:
        # ━━ AUTO-MIGRATION: wallet_requests ━━
        try:
            table_result = await conn.execute(
                text(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' "
                    "AND name='wallet_requests'"
                )
            )
            table_exists = (
                table_result.fetchone() is not None
            )

            if table_exists:
                # Check legacy column
                col_result = await conn.execute(
                    text(
                        "SELECT name FROM "
                        "pragma_table_info"
                        "('wallet_requests') "
                        "WHERE name='amount_inr'"
                    )
                )
                has_new_col = (
                    col_result.fetchone() is not None
                )

                if not has_new_col:
                    log.warning(
                        "⚠️ Old wallet_requests "
                        "schema. Migrating..."
                    )
                    await conn.execute(
                        text(
                            "DROP TABLE wallet_requests"
                        )
                    )
                    log.info(
                        "✅ Old wallet_requests dropped"
                    )
                else:
                    # ━━ Add missing FamGateway columns ━━
                    fam_cols = [
                        ("fam_order_id", "VARCHAR(64)"),
                        ("fam_qr_url", "VARCHAR(512)"),
                        ("fam_upi_intent", "VARCHAR(512)"),
                        ("fam_checkout_url", "VARCHAR(512)"),
                        ("fam_utr", "VARCHAR(64)"),
                        ("fam_sender_name", "VARCHAR(128)"),
                        ("fam_expires_at", "DATETIME"),
                        ("auto_verified", "BOOLEAN DEFAULT 0"),
                    ]

                    existing_result = await conn.execute(
                        text(
                            "SELECT name FROM "
                            "pragma_table_info"
                            "('wallet_requests')"
                        )
                    )
                    existing_cols = {
                        row[0]
                        for row in existing_result.fetchall()
                    }

                    for col_name, col_type in fam_cols:
                        if col_name not in existing_cols:
                            try:
                                await conn.execute(
                                    text(
                                        f"ALTER TABLE "
                                        f"wallet_requests "
                                        f"ADD COLUMN "
                                        f"{col_name} {col_type}"
                                    )
                                )
                                log.info(
                                    f"✅ Added column: "
                                    f"{col_name}"
                                )
                            except Exception as e:
                                log.warning(
                                    f"⚠️ Could not add "
                                    f"{col_name}: {e}"
                                )

        except Exception as e:
            log.warning(
                f"⚠️ Migration check failed: {e}"
            )

        # Create all tables (or missing ones)
        await conn.run_sync(
            Base.metadata.create_all
        )

    log.info("✅ Database tables verified")


async def register_handlers() -> None:
    """Register all handler routers."""
    from bot.handlers.router import (
        register_all_routers,
    )
    register_all_routers(dp)
    log.info("✅ All handlers registered")


async def register_middlewares() -> None:
    """Register all middlewares."""
    from bot.middlewares import (
        register_all_middlewares,
    )
    register_all_middlewares(dp)
    log.info("✅ All middlewares registered")


async def on_startup() -> None:
    """Startup hook."""
    log.info("━" * 50)
    log.info("⚡ GHOST MARKET BOT STARTING")
    log.info("━" * 50)

    # Setup logger
    setup_logger()

    # Ensure directories exist
    settings.ensure_directories()

    # Auto-create database tables
    await init_database_tables()

    # Load translations
    i18n.load_all()

    # Initialize default settings
    await initialize_defaults()

    # Sync superadmins from .env
    await sync_superadmins()

    # Set bot commands
    await set_bot_commands()

    # Register middlewares (order matters!)
    await register_middlewares()

    # Register all handlers
    await register_handlers()

    # Start scheduler
    await start_scheduler()

    # ━━ Start FamGateway auto-verify poller ━━
    try:
        from bot.tasks.famgateway_poller import (
            poll_famgateway_orders,
        )
        import asyncio
        asyncio.create_task(poll_famgateway_orders())
        log.info("✅ FamGateway poller task created")
    except ImportError as e:
        log.warning(
            f"⚠️ FamGateway poller not available: {e}"
        )

    # Get bot info
    me = await bot.get_me()
    log.info(
        f"✅ Bot started: @{me.username} "
        f"(ID: {me.id})"
    )
    log.info("━" * 50)


async def on_shutdown() -> None:
    """Shutdown hook."""
    log.info("⚡ Bot shutting down...")
    await bot.session.close()
    log.info("✅ Bot stopped cleanly")


async def initialize_defaults() -> None:
    """Initialize default settings in DB."""
    from bot.database.engine import get_session
    from bot.database.repositories import (
        SettingsRepository,
    )

    async with get_session() as session:
        repo = SettingsRepository(session)

        # Default settings
        defaults = {
            # ━━ Core ━━
            repo.KEY_FORCE_SUB: "false",
            repo.KEY_LOW_STOCK_ALERT: "true",
            repo.KEY_SESSION_CHECK: "true",
            repo.KEY_SALE_NOTIF: "true",
            repo.KEY_DAILY_REPORT: "true",
            repo.KEY_BALANCE_REQ_NOTIF: "true",
            repo.KEY_NEW_USER_NOTIF: "false",
            repo.KEY_AUTO_2FA: "true",
            repo.KEY_LOW_STOCK_THRESHOLD: (
                str(settings.low_stock_threshold)
            ),

            # ━━ Payment — Common ━━
            repo.KEY_MIN_DEPOSIT: "10",
            repo.KEY_MAX_DEPOSIT: "100000",

            # ━━ Support ━━
            repo.KEY_SUPPORT_USERNAME: "",

            # ━━ UPI (FamGateway) ━━
            "fam_auto_enabled": "true",
            "fam_daily_limit": "5000",

            # ━━ USDT Crypto (NEW) ━━
            "usdt_bep20_address": "",
            "usdt_rate_mode": "auto",
            "usdt_rate": "83.0",
            "usdt_rate_live": "0",
            "usdt_rate_last_update": "",
        }

        for key, value in defaults.items():
            existing = await repo.get(key)
            if existing is None:
                await repo.set(key, value)

    log.info("✅ Default settings initialized")


async def sync_superadmins() -> None:
    """Sync superadmin IDs from .env to DB."""
    from bot.database.engine import get_session
    from bot.database.models.owner import (
        OwnerRole,
    )
    from bot.database.repositories import (
        OwnerRepository,
    )

    async with get_session() as session:
        repo = OwnerRepository(session)

        for tg_id in settings.superadmin_id_list:
            existing = (
                await repo.get_by_telegram_id(
                    tg_id
                )
            )
            if existing is None:
                await repo.create(
                    telegram_id=tg_id,
                    role=OwnerRole.SUPERADMIN,
                )
                log.info(
                    f"✅ Superadmin added: "
                    f"{tg_id}"
                )

    log.info("✅ Superadmins synced from .env")


async def start_scheduler() -> None:
    """Start background scheduler."""
    try:
        from bot.scheduler.scheduler import (
            start as start_jobs,
        )
        await start_jobs()
        log.info("✅ Scheduler started")
    except ImportError:
        log.warning(
            "⚠️ Scheduler module not found, "
            "skipping background jobs"
        )


async def run_bot() -> None:
    """Main bot runner."""
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    try:
        await dp.start_polling(
            bot,
            allowed_updates=(
                dp.resolve_used_update_types()
            ),
        )
    except Exception as e:
        log.critical(f"❌ Bot crashed: {e}")
        raise


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENTRY POINT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    import asyncio
    import sys

    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Bot crashed: {e}")
        sys.exit(1)