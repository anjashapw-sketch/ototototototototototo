"""
Ghost Market Bot — Entry Point.
Run with: python main.py
"""

import asyncio
import sys

from bot.main import run_bot


def main() -> None:
    """Main entry point for hosting panels."""
    try:
        asyncio.run(run_bot())
    except (KeyboardInterrupt, SystemExit):
        print("\n⚡ Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()