"""
Text formatters.
Money, datetime, phone masking, time helpers.
"""

from datetime import datetime
from decimal import Decimal


def format_money(
    amount: Decimal,
    currency: str = "",
) -> str:
    """
    Format amount with optional currency.

    Default: no currency symbol (added by locale).
    Pass currency="$" to prepend dollar sign.

    Args:
        amount: Decimal amount to format
        currency: Optional currency symbol prefix

    Examples:
        format_money(1234.5)          → '1,234.50'
        format_money(1234.5, '$')     → '$1,234.50'
        format_money(None)            → '0.00'
        format_money(None, '$')       → '$0.00'

    Returns:
        Formatted string with thousands separator
        and 2 decimal places.
    """
    if amount is None:
        return f"{currency}0.00"

    formatted = f"{amount:,.2f}"
    return f"{currency}{formatted}"


def format_datetime(
    dt: datetime,
    format_str: str = "%Y-%m-%d %H:%M",
) -> str:
    """
    Format datetime for display.

    Args:
        dt: datetime object
        format_str: strftime format string

    Returns:
        Formatted datetime string or 'N/A'
    """
    if dt is None:
        return "N/A"
    return dt.strftime(format_str)


def format_date(dt: datetime) -> str:
    """
    Format date only (no time).

    Args:
        dt: datetime object

    Returns:
        Date string in YYYY-MM-DD format
    """
    if dt is None:
        return "N/A"
    return dt.strftime("%Y-%m-%d")


def format_phone_masked(phone: str) -> str:
    """
    Mask middle of phone number for privacy.

    Args:
        phone: Phone number with country code

    Example:
        '+919876543210' → '+919876XX3210'

    Returns:
        Phone with masked middle digits
    """
    if not phone or len(phone) < 8:
        return phone

    visible_start = 6
    visible_end = 4
    masked_len = (
        len(phone) - visible_start - visible_end
    )

    if masked_len <= 0:
        return phone

    return (
        phone[:visible_start]
        + "X" * masked_len
        + phone[-visible_end:]
    )


def format_phone_pretty(phone: str) -> str:
    """
    Format phone in international style.

    Args:
        phone: Phone number with country code

    Example:
        '+919876543210' → '+91 98765 43210'

    Returns:
        Pretty-formatted phone number
    """
    if not phone:
        return phone

    if not phone.startswith("+"):
        phone = "+" + phone

    try:
        import phonenumbers
        from phonenumbers import (
            PhoneNumberFormat,
        )

        parsed = phonenumbers.parse(phone, None)
        return phonenumbers.format_number(
            parsed,
            PhoneNumberFormat.INTERNATIONAL,
        )
    except Exception:
        return phone


def format_time_ago(dt: datetime) -> str:
    """
    Format relative time (e.g., '2 mins ago').

    Args:
        dt: datetime in UTC

    Examples:
        '2 mins ago', '3 hours ago', '5 days ago'

    Returns:
        Human-readable relative time string
    """
    if dt is None:
        return "N/A"

    now = datetime.utcnow()
    diff = now - dt
    seconds = diff.total_seconds()

    if seconds < 60:
        return "just now"

    if seconds < 3600:
        mins = int(seconds // 60)
        return (
            f"{mins} min"
            f"{'s' if mins != 1 else ''} ago"
        )

    if seconds < 86400:
        hours = int(seconds // 3600)
        return (
            f"{hours} hour"
            f"{'s' if hours != 1 else ''} ago"
        )

    days = int(seconds // 86400)
    return (
        f"{days} day"
        f"{'s' if days != 1 else ''} ago"
    )


def truncate(
    text: str,
    max_length: int = 50,
) -> str:
    """
    Truncate text with ellipsis.

    Args:
        text: Input text
        max_length: Maximum allowed length

    Returns:
        Truncated text with '...' suffix if cut
    """
    if not text or len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."