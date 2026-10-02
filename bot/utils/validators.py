"""
Input validators.
Validates OTPs, amounts, IDs etc.
"""

from decimal import Decimal, InvalidOperation
from typing import Optional


def validate_otp(otp: str) -> Optional[str]:
    """
    Validate OTP format.

    Args:
        otp: User-entered OTP

    Returns:
        Cleaned OTP or None
    """
    if not otp:
        return None

    cleaned = otp.strip().replace(" ", "")

    if not cleaned.isdigit():
        return None

    if not (4 <= len(cleaned) <= 8):
        return None

    return cleaned


def validate_amount(
    amount_str: str,
    min_amount: Decimal = Decimal("1.00"),
    max_amount: Decimal = Decimal("1000000.00")
) -> Optional[Decimal]:
    """
    Validate monetary amount.

    Args:
        amount_str: User input
        min_amount: Minimum allowed
        max_amount: Maximum allowed

    Returns:
        Decimal amount or None
    """
    if not amount_str:
        return None

    cleaned = (
        amount_str.strip()
        .replace(",", "")
        .replace("₹", "")
        .replace("$", "")
        .strip()
    )

    try:
        amount = Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None

    if amount < min_amount:
        return None

    if amount > max_amount:
        return None

    # Round to 2 decimals
    return amount.quantize(Decimal("0.01"))


def validate_telegram_id(
    id_str: str
) -> Optional[int]:
    """
    Validate Telegram user ID.

    Returns:
        Valid int ID or None
    """
    if not id_str:
        return None

    cleaned = id_str.strip()

    try:
        tg_id = int(cleaned)
    except ValueError:
        return None

    # Telegram IDs are positive
    if tg_id <= 0:
        return None

    # Reasonable upper limit
    if tg_id > 10**12:
        return None

    return tg_id


def validate_chat_id(
    id_str: str
) -> Optional[int]:
    """
    Validate Telegram chat ID
    (channels/groups).

    Channel IDs start with -100.

    Returns:
        Valid int ID or None
    """
    if not id_str:
        return None

    cleaned = id_str.strip()

    try:
        chat_id = int(cleaned)
    except ValueError:
        return None

    # Channels: -100XXXXXXXXXX
    # Groups:  -XXXXXXXXX
    if chat_id >= 0:
        return None

    return chat_id


def validate_username(
    username: str
) -> Optional[str]:
    """
    Validate Telegram username.

    Returns:
        Cleaned username (no @) or None
    """
    if not username:
        return None

    cleaned = (
        username.strip()
        .lstrip("@")
        .replace("https://t.me/", "")
        .replace("t.me/", "")
        .strip()
    )

    if not cleaned:
        return None

    # Telegram username rules
    if len(cleaned) < 5 or len(cleaned) > 32:
        return None

    if not all(
        c.isalnum() or c == "_"
        for c in cleaned
    ):
        return None

    return cleaned


def validate_invite_link(
    link: str
) -> Optional[str]:
    """
    Validate Telegram invite link.

    Returns:
        Cleaned link or None
    """
    if not link:
        return None

    cleaned = link.strip()

    valid_prefixes = (
        "https://t.me/+",
        "https://t.me/joinchat/",
        "t.me/+",
        "t.me/joinchat/"
    )

    if not any(
        cleaned.startswith(p)
        for p in valid_prefixes
    ):
        return None

    # Normalize to https
    if cleaned.startswith("t.me/"):
        cleaned = "https://" + cleaned

    return cleaned