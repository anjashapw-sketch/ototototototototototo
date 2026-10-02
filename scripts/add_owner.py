"""
Add owner script.
Manually add an owner to the database.

Usage:
    python scripts/add_owner.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root
sys.path.insert(
    0, str(Path(__file__).parent.parent)
)

from bot.database.engine import (
    engine, get_session
)
from bot.database.models.owner import OwnerRole
from bot.database.repositories import (
    OwnerRepository
)


async def add_owner() -> None:
    """Interactive owner add."""
    print("━" * 50)
    print("👑 ADD OWNER")
    print("━" * 50)

    try:
        tg_id_input = input(
            "\nTelegram User ID: "
        ).strip()
        tg_id = int(tg_id_input)
    except ValueError:
        print("❌ Invalid ID")
        return

    username = input(
        "Username (optional): "
    ).strip() or None

    print("\nRole:")
    print("  1. Superadmin (full access)")
    print("  2. Admin (limited)")

    role_input = input(
        "\nChoice (1/2): "
    ).strip()

    if role_input == "1":
        role = OwnerRole.SUPERADMIN
    elif role_input == "2":
        role = OwnerRole.ADMIN
    else:
        print("❌ Invalid choice")
        return

    async with get_session() as session:
        repo = OwnerRepository(session)

        existing = await repo.get_by_telegram_id(
            tg_id
        )
        if existing:
            print(
                f"\n⚠️ User already an owner "
                f"({existing.role.value})"
            )
            return

        await repo.create(
            telegram_id=tg_id,
            username=username,
            role=role
        )

    print("\n" + "━" * 50)
    print(f"✅ Owner added successfully!")
    print(f"   ID: {tg_id}")
    print(f"   Username: @{username or 'none'}")
    print(f"   Role: {role.value}")
    print("━" * 50)


async def main() -> None:
    """Main entry point."""
    try:
        await add_owner()
    except KeyboardInterrupt:
        print("\n⚡ Cancelled")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())