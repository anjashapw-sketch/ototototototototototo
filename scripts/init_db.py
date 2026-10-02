"""
Database initialization script.
Creates all tables.

Usage:
    python scripts/init_db.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(
    0, str(Path(__file__).parent.parent)
)

from bot.config import settings
from bot.database.base import Base
from bot.database.engine import engine

# Import all models to register them
from bot.database.models import (  # noqa: F401
    User, Owner, Account, Transaction,
    WalletRequest, Pricing, Setting,
    BulkBatch, ForceSubChannel
)


async def init_database() -> None:
    """Create all database tables."""
    print("⚡ Initializing database...")
    print(f"📂 Path: {settings.database_url}")

    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all
        )

    print("✅ All tables created successfully!")
    print(
        "📊 Tables: users, owners, accounts, "
        "transactions, wallet_requests, "
        "pricing, settings, bulk_batches, "
        "force_sub_channels"
    )


async def main() -> None:
    """Main entry point."""
    try:
        await init_database()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())