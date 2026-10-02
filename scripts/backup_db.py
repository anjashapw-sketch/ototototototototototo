"""
Database backup script.
Creates a timestamped copy of the SQLite DB.

Usage:
    python scripts/backup_db.py
"""

import shutil
import sys
from datetime import datetime
from pathlib import Path

# Add project root
sys.path.insert(
    0, str(Path(__file__).parent.parent)
)

from bot.config import settings


def backup_database() -> Path:
    """Create database backup."""
    db_file = (
        settings.data_dir / "ghost.db"
    )

    if not db_file.exists():
        print(
            f"❌ Database not found: {db_file}"
        )
        sys.exit(1)

    # Create backups directory
    backup_dir = (
        settings.data_dir / "backups"
    )
    backup_dir.mkdir(
        parents=True, exist_ok=True
    )

    # Timestamped filename
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )
    backup_file = (
        backup_dir / f"ghost_{timestamp}.db"
    )

    print("━" * 50)
    print("💾 DATABASE BACKUP")
    print("━" * 50)
    print(f"\nSource: {db_file}")
    print(f"Target: {backup_file}\n")

    try:
        shutil.copy2(db_file, backup_file)
        size_kb = (
            backup_file.stat().st_size / 1024
        )
        print(
            f"✅ Backup created: "
            f"{size_kb:.2f} KB"
        )
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        sys.exit(1)

    # Cleanup old backups (keep last 10)
    _cleanup_old_backups(backup_dir)

    print("━" * 50)
    return backup_file


def _cleanup_old_backups(
    backup_dir: Path,
    keep: int = 10
) -> None:
    """Keep only N most recent backups."""
    backups = sorted(
        backup_dir.glob("ghost_*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    if len(backups) <= keep:
        return

    removed = 0
    for old_backup in backups[keep:]:
        try:
            old_backup.unlink()
            removed += 1
        except Exception:
            pass

    if removed:
        print(
            f"🧹 Removed {removed} old backups"
        )


def main() -> None:
    """Main entry."""
    try:
        backup_database()
    except KeyboardInterrupt:
        print("\n⚡ Cancelled")
        sys.exit(0)


if __name__ == "__main__":
    main()