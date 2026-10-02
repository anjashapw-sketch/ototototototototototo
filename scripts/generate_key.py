"""
Generate Fernet encryption key.

Usage:
    python scripts/generate_key.py

Copy the output and paste in .env
as ENCRYPTION_KEY value.
"""

from cryptography.fernet import Fernet


def main() -> None:
    """Generate and print key."""
    key = Fernet.generate_key().decode("utf-8")
    print("━" * 60)
    print("🔐 ENCRYPTION KEY GENERATED")
    print("━" * 60)
    print(f"\n{key}\n")
    print("━" * 60)
    print(
        "📋 Copy this value and paste in .env:"
    )
    print(f"ENCRYPTION_KEY={key}")
    print("━" * 60)
    print(
        "⚠️  Keep this safe! If lost, all "
        "encrypted data becomes unreadable."
    )


if __name__ == "__main__":
    main()