"""
Country flag emoji generator.
Converts country code to flag emoji.
"""

from typing import Optional

import pycountry


def get_flag(country_code: str) -> str:
    """
    Convert ISO country code to flag emoji.

    Args:
        country_code: 2-letter ISO code
                     (e.g., 'IN', 'US')

    Returns:
        Flag emoji or 🌍 if invalid
    """
    if not country_code or len(country_code) != 2:
        return "🌍"

    code = country_code.upper()

    # Each letter offset: A=127462
    try:
        return "".join(
            chr(0x1F1E6 + ord(c) - ord("A"))
            for c in code
        )
    except (ValueError, TypeError):
        return "🌍"


def get_country_name(
    country_code: str
) -> Optional[str]:
    """
    Get full country name from ISO code.

    Args:
        country_code: 2-letter ISO code

    Returns:
        Full country name or None
    """
    if not country_code:
        return None

    try:
        country = pycountry.countries.get(
            alpha_2=country_code.upper()
        )
        return country.name if country else None
    except (AttributeError, LookupError):
        return None


def get_country_flag_name(
    country_code: str
) -> str:
    """
    Get formatted flag + name string.

    Example:
        'IN' → '🇮🇳 India'
    """
    flag = get_flag(country_code)
    name = get_country_name(country_code)
    if name:
        return f"{flag} {name}"
    return f"{flag} Unknown"