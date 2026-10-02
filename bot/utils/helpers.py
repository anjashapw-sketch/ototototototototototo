"""
Miscellaneous helper functions.
"""

import secrets
import string


def generate_random_password(
    length: int = 12,
    prefix: str = ""
) -> str:
    """
    Generate secure random password.

    Args:
        length: Password length (without prefix)
        prefix: Optional prefix

    Returns:
        Random password string
    """
    alphabet = (
        string.ascii_letters
        + string.digits
    )
    password = "".join(
        secrets.choice(alphabet)
        for _ in range(length)
    )
    return f"{prefix}{password}"


def chunk_list(
    items: list, chunk_size: int
) -> list[list]:
    """
    Split list into chunks.

    Example:
        chunk_list([1,2,3,4,5], 2)
        → [[1,2], [3,4], [5]]
    """
    return [
        items[i : i + chunk_size]
        for i in range(0, len(items), chunk_size)
    ]


def safe_int(
    value, default: int = 0
) -> int:
    """Safely convert to int."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def escape_html(text: str) -> str:
    """Escape HTML special chars."""
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )