"""
Phone number utilities.
Parses, validates, normalizes phone numbers.
"""

from typing import Optional

import phonenumbers
from phonenumbers import (
    NumberParseException, PhoneNumberFormat
)


def normalize_phone(phone: str) -> Optional[str]:
    """
    Normalize phone number to E.164 format.

    Args:
        phone: Raw phone (with/without +)

    Returns:
        Normalized phone (+1234567890) or None
    """
    if not phone:
        return None

    # Clean input
    phone = phone.strip()
    if not phone.startswith("+"):
        phone = "+" + phone.lstrip("0")

    try:
        parsed = phonenumbers.parse(phone, None)
        if not phonenumbers.is_valid_number(
            parsed
        ):
            return None
        return phonenumbers.format_number(
            parsed, PhoneNumberFormat.E164
        )
    except NumberParseException:
        return None


def is_valid_phone(phone: str) -> bool:
    """Check if phone is valid."""
    return normalize_phone(phone) is not None


def get_country_code_from_phone(
    phone: str
) -> Optional[str]:
    """
    Extract ISO country code from phone.

    Args:
        phone: Phone in E.164 format

    Returns:
        2-letter ISO code or None
    """
    if not phone:
        return None

    if not phone.startswith("+"):
        phone = "+" + phone

    try:
        parsed = phonenumbers.parse(phone, None)
        region = (
            phonenumbers.region_code_for_number(
                parsed
            )
        )
        return region
    except NumberParseException:
        return None


def format_phone_pretty(phone: str) -> str:
    """
    Format phone in international style.

    Example:
        '+919876543210' → '+91 98765 43210'
    """
    if not phone:
        return phone

    if not phone.startswith("+"):
        phone = "+" + phone

    try:
        parsed = phonenumbers.parse(phone, None)
        return phonenumbers.format_number(
            parsed,
            PhoneNumberFormat.INTERNATIONAL
        )
    except NumberParseException:
        return phone