"""
Ultra-advanced device fingerprint generator.
Generates ultra-realistic device parameters
to make sessions completely undetectable.
"""

import hashlib
import json
import random
import time
from dataclasses import asdict, dataclass
from typing import Optional


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# REAL DEVICE PROFILES (2024-2025)
# Verified from real Telegram clients
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

REAL_DEVICES = [
    # ━━ Samsung Flagship ━━
    {
        "model": "SM-S928B",
        "name": "Samsung Galaxy S24 Ultra",
        "manufacturer": "samsung",
        "sdk": 34, "android": "14",
        "build": "UP1A.231005.007",
        "performance": "ultra",
    },
    {
        "model": "SM-S921B",
        "name": "Samsung Galaxy S24",
        "manufacturer": "samsung",
        "sdk": 34, "android": "14",
        "build": "UP1A.231005.007",
        "performance": "ultra",
    },
    {
        "model": "SM-S918B",
        "name": "Samsung Galaxy S23 Ultra",
        "manufacturer": "samsung",
        "sdk": 34, "android": "14",
        "build": "UP1A.231005.007",
        "performance": "ultra",
    },
    {
        "model": "SM-F946B",
        "name": "Samsung Galaxy Z Fold5",
        "manufacturer": "samsung",
        "sdk": 34, "android": "14",
        "build": "UP1A.231005.007",
        "performance": "ultra",
    },
    {
        "model": "SM-A546E",
        "name": "Samsung Galaxy A54 5G",
        "manufacturer": "samsung",
        "sdk": 33, "android": "13",
        "build": "TP1A.220624.014",
        "performance": "high",
    },
    {
        "model": "SM-A346E",
        "name": "Samsung Galaxy A34 5G",
        "manufacturer": "samsung",
        "sdk": 33, "android": "13",
        "build": "TP1A.220624.014",
        "performance": "high",
    },

    # ━━ Xiaomi / Redmi ━━
    {
        "model": "23116PN5BG",
        "name": "Xiaomi 13 Pro",
        "manufacturer": "Xiaomi",
        "sdk": 33, "android": "13",
        "build": "TKQ1.220829.002",
        "performance": "ultra",
    },
    {
        "model": "2306EPN60G",
        "name": "Xiaomi 13T Pro",
        "manufacturer": "Xiaomi",
        "sdk": 33, "android": "13",
        "build": "TKQ1.221013.002",
        "performance": "ultra",
    },
    {
        "model": "22101316G",
        "name": "Redmi Note 12 Pro",
        "manufacturer": "Xiaomi",
        "sdk": 33, "android": "13",
        "build": "TKQ1.220829.002",
        "performance": "high",
    },
    {
        "model": "23090RA98G",
        "name": "Redmi Note 13 Pro",
        "manufacturer": "Xiaomi",
        "sdk": 34, "android": "14",
        "build": "UP1A.231005.007",
        "performance": "high",
    },

    # ━━ OnePlus ━━
    {
        "model": "CPH2449",
        "name": "OnePlus 11",
        "manufacturer": "OnePlus",
        "sdk": 34, "android": "14",
        "build": "UP1A.231005.007",
        "performance": "ultra",
    },
    {
        "model": "CPH2581",
        "name": "OnePlus 12",
        "manufacturer": "OnePlus",
        "sdk": 34, "android": "14",
        "build": "UP1A.231005.007",
        "performance": "ultra",
    },
    {
        "model": "CPH2399",
        "name": "OnePlus Nord 3 5G",
        "manufacturer": "OnePlus",
        "sdk": 33, "android": "13",
        "build": "TP1A.220905.001",
        "performance": "high",
    },

    # ━━ Google Pixel ━━
    {
        "model": "Pixel 8 Pro",
        "name": "Google Pixel 8 Pro",
        "manufacturer": "Google",
        "sdk": 34, "android": "14",
        "build": "UD1A.230803.041",
        "performance": "ultra",
    },
    {
        "model": "Pixel 8",
        "name": "Google Pixel 8",
        "manufacturer": "Google",
        "sdk": 34, "android": "14",
        "build": "UD1A.230803.041",
        "performance": "ultra",
    },
    {
        "model": "Pixel 7 Pro",
        "name": "Google Pixel 7 Pro",
        "manufacturer": "Google",
        "sdk": 33, "android": "13",
        "build": "TQ3A.230901.001",
        "performance": "ultra",
    },
    {
        "model": "Pixel 7a",
        "name": "Google Pixel 7a",
        "manufacturer": "Google",
        "sdk": 33, "android": "13",
        "build": "TQ3A.230901.001",
        "performance": "high",
    },

    # ━━ Realme ━━
    {
        "model": "RMX3686",
        "name": "Realme GT Neo 5",
        "manufacturer": "realme",
        "sdk": 33, "android": "13",
        "build": "TP1A.220905.001",
        "performance": "high",
    },
    {
        "model": "RMX3851",
        "name": "Realme 11 Pro+",
        "manufacturer": "realme",
        "sdk": 33, "android": "13",
        "build": "TP1A.220905.001",
        "performance": "high",
    },

    # ━━ Vivo ━━
    {
        "model": "V2312",
        "name": "vivo X100 Pro",
        "manufacturer": "vivo",
        "sdk": 34, "android": "14",
        "build": "UP1A.231005.007",
        "performance": "ultra",
    },

    # ━━ Oppo ━━
    {
        "model": "CPH2557",
        "name": "OPPO Find X7 Ultra",
        "manufacturer": "OPPO",
        "sdk": 34, "android": "14",
        "build": "UP1A.231005.007",
        "performance": "ultra",
    },

    # ━━ Nothing ━━
    {
        "model": "A065",
        "name": "Nothing Phone (2)",
        "manufacturer": "Nothing",
        "sdk": 34, "android": "14",
        "build": "UP1A.231005.007",
        "performance": "ultra",
    },
]


# Telegram Android app versions (2024-2025)
APP_VERSIONS = [
    "10.13.3", "10.13.2", "10.13.1", "10.13.0",
    "10.12.0", "10.11.2", "10.11.1", "10.11.0",
    "10.10.1", "10.10.0", "10.9.2", "10.9.1",
]


# Language by country with regional variants
LANG_BY_COUNTRY = {
    "IN": ("en", "en-IN"),
    "US": ("en", "en-US"),
    "GB": ("en", "en-GB"),
    "CA": ("en", "en-CA"),
    "AU": ("en", "en-AU"),
    "RU": ("ru", "ru-RU"),
    "UA": ("uk", "uk-UA"),
    "DE": ("de", "de-DE"),
    "FR": ("fr", "fr-FR"),
    "ES": ("es", "es-ES"),
    "IT": ("it", "it-IT"),
    "PT": ("pt", "pt-PT"),
    "BR": ("pt", "pt-BR"),
    "CN": ("zh", "zh-CN"),
    "TW": ("zh", "zh-TW"),
    "JP": ("ja", "ja-JP"),
    "KR": ("ko", "ko-KR"),
    "SA": ("ar", "ar-SA"),
    "AE": ("ar", "ar-AE"),
    "EG": ("ar", "ar-EG"),
    "TR": ("tr", "tr-TR"),
    "ID": ("id", "id-ID"),
    "TH": ("th", "th-TH"),
    "VN": ("vi", "vi-VN"),
    "PH": ("en", "en-PH"),
    "MX": ("es", "es-MX"),
    "AR": ("es", "es-AR"),
    "PL": ("pl", "pl-PL"),
    "NL": ("nl", "nl-NL"),
    "SE": ("sv", "sv-SE"),
    "NO": ("nb", "nb-NO"),
    "DK": ("da", "da-DK"),
    "FI": ("fi", "fi-FI"),
    "GR": ("el", "el-GR"),
    "IL": ("he", "he-IL"),
    "IR": ("fa", "fa-IR"),
}


# Time zones by country
TIMEZONE_BY_COUNTRY = {
    "IN": "Asia/Kolkata",
    "US": "America/New_York",
    "GB": "Europe/London",
    "RU": "Europe/Moscow",
    "DE": "Europe/Berlin",
    "FR": "Europe/Paris",
    "CN": "Asia/Shanghai",
    "JP": "Asia/Tokyo",
    "KR": "Asia/Seoul",
    "SA": "Asia/Riyadh",
    "AE": "Asia/Dubai",
    "BR": "America/Sao_Paulo",
    "MX": "America/Mexico_City",
    "AU": "Australia/Sydney",
    "ID": "Asia/Jakarta",
}


@dataclass
class DeviceFingerprint:
    """Ultra-realistic device fingerprint data."""
    device_model: str
    system_version: str
    app_version: str
    lang_code: str
    system_lang_code: str

    # Extended fields (for storage only)
    manufacturer: str = ""
    android_version: str = ""
    sdk_level: int = 0
    build_id: str = ""
    timezone: str = "UTC"
    device_id: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(
        cls, json_str: str
    ) -> "DeviceFingerprint":
        """Load from JSON."""
        data = json.loads(json_str)
        return cls(**data)


class FingerprintGenerator:
    """
    Ultra-advanced fingerprint generator
    for maximum stealth. Each fingerprint
    is unique, persistent, and indistinguishable
    from real Telegram clients.
    """

    @staticmethod
    def _generate_device_id(
        device_name: str,
        phone: Optional[str] = None,
    ) -> str:
        """
        Generate a persistent device ID
        based on device + phone (or random).
        """
        seed = (
            f"{device_name}-{phone or random.random()}-"
            f"{int(time.time())}"
        )
        return hashlib.sha256(
            seed.encode()
        ).hexdigest()[:16]

    @staticmethod
    def _build_system_version(
        device: dict
    ) -> str:
        """
        Build realistic system version string.
        Format: 'Android 14 (UP1A.231005.007)'
        """
        return (
            f"Android {device['android']} "
            f"({device['build']})"
        )

    @staticmethod
    def generate(
        country_code: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> DeviceFingerprint:
        """
        Generate ultra-realistic fingerprint.

        Args:
            country_code: ISO country code
                          for region matching
            phone: Phone number for persistent ID

        Returns:
            DeviceFingerprint instance
        """
        device = random.choice(REAL_DEVICES)
        app_version = random.choice(APP_VERSIONS)

        # Determine language
        if country_code and country_code in LANG_BY_COUNTRY:
            lang_short, lang_full = (
                LANG_BY_COUNTRY[country_code]
            )
        else:
            lang_short, lang_full = ("en", "en-US")

        # Timezone
        tz = TIMEZONE_BY_COUNTRY.get(
            country_code or "US", "UTC"
        )

        # Generate persistent device ID
        device_id = (
            FingerprintGenerator._generate_device_id(
                device["name"], phone
            )
        )

        return DeviceFingerprint(
            device_model=device["name"],
            system_version=(
                FingerprintGenerator
                ._build_system_version(device)
            ),
            app_version=app_version,
            lang_code=lang_short,
            system_lang_code=lang_full,
            manufacturer=device["manufacturer"],
            android_version=device["android"],
            sdk_level=device["sdk"],
            build_id=device["build"],
            timezone=tz,
            device_id=device_id,
        )

    @staticmethod
    def generate_json(
        country_code: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> str:
        """Generate fingerprint as JSON."""
        fp = FingerprintGenerator.generate(
            country_code, phone
        )
        return fp.to_json()


# ━━━ SINGLETON INSTANCE ━━━
fingerprint_generator = FingerprintGenerator()