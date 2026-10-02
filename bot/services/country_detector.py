"""
Country detection from phone numbers.
Uses phonenumbers + pycountry.
"""

from typing import Optional, Tuple

import phonenumbers
from phonenumbers import (
    NumberParseException, geocoder
)

from bot.utils.flag_emoji import (
    get_country_name
)
from bot.utils.logger import log


class CountryDetector:
    """
    Detect country from phone numbers.
    """

    @staticmethod
    def detect(
        phone: str
    ) -> Tuple[str, str]:
        """
        Detect country code and name.

        Args:
            phone: Phone in E.164 format

        Returns:
            (country_code, country_name)
            e.g., ('IN', 'India')
            Falls back to ('XX', 'Unknown')
        """
        if not phone:
            return ("XX", "Unknown")

        if not phone.startswith("+"):
            phone = "+" + phone

        try:
            parsed = phonenumbers.parse(
                phone, None
            )
            region = (
                phonenumbers
                .region_code_for_number(parsed)
            )

            if not region:
                return ("XX", "Unknown")

            name = (
                get_country_name(region)
                or geocoder.description_for_number(
                    parsed, "en"
                )
                or "Unknown"
            )

            return (region, name)

        except NumberParseException as e:
            log.warning(
                f"Country detection failed for "
                f"{phone}: {e}"
            )
            return ("XX", "Unknown")

    @staticmethod
    def get_country_code_only(
        phone: str
    ) -> str:
        """Get just country code."""
        code, _ = CountryDetector.detect(phone)
        return code

    @staticmethod
    def is_valid_country(
        phone: str
    ) -> bool:
        """Check if phone has valid country."""
        code, _ = CountryDetector.detect(phone)
        return code != "XX"


# ━━━ SINGLETON INSTANCE ━━━
country_detector = CountryDetector()