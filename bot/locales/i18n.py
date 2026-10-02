"""
Custom i18n (internationalization) system.
Loads JSON files and provides translations.
"""

import json
from typing import Any, Dict, Optional

from bot.config import settings
from bot.utils.logger import log


class I18n:
    """
    Internationalization handler.
    Loads translations from JSON files.
    """

    SUPPORTED_LANGUAGES = [
        "en", "hi", "ru", "es", "zh", "ar"
    ]

    LANGUAGE_NAMES = {
        "en": "🇬🇧 English",
        "hi": "🇮🇳 हिन्दी",
        "ru": "🇷🇺 Русский",
        "es": "🇪🇸 Español",
        "zh": "🇨🇳 中文",
        "ar": "🇸🇦 العربية"
    }

    def __init__(self):
        self._translations: Dict[
            str, Dict[str, Any]
        ] = {}
        self._default_lang = (
            settings.default_language
        )

    def load_all(self) -> None:
        """Load all language JSON files."""
        for lang in self.SUPPORTED_LANGUAGES:
            self._load_language(lang)
        log.info(
            f"✅ Loaded {len(self._translations)} "
            f"languages"
        )

    def _load_language(self, lang: str) -> None:
        """Load single language file."""
        lang_file = (
            settings.locales_dir / f"{lang}.json"
        )

        if not lang_file.exists():
            log.warning(
                f"⚠️ Language file missing: "
                f"{lang}.json"
            )
            self._translations[lang] = {}
            return

        try:
            with open(
                lang_file, "r", encoding="utf-8"
            ) as f:
                self._translations[lang] = (
                    json.load(f)
                )
        except (json.JSONDecodeError, OSError) as e:
            log.error(
                f"❌ Failed to load {lang}.json: "
                f"{e}"
            )
            self._translations[lang] = {}

    def get(
        self,
        key: str,
        lang: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Get translated text.

        Args:
            key: Translation key (e.g., 'welcome')
            lang: Language code
            **kwargs: Format params

        Returns:
            Translated string
        """
        if lang is None:
            lang = self._default_lang

        # Try requested language
        translations = self._translations.get(
            lang, {}
        )
        text = translations.get(key)

        # Fallback to English
        if text is None and lang != "en":
            text = self._translations.get(
                "en", {}
            ).get(key)

        # Final fallback
        if text is None:
            return f"[{key}]"

        # Format with kwargs
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, ValueError) as e:
                log.warning(
                    f"Format error for '{key}': "
                    f"{e}"
                )
                return text

        return text

    def is_supported(self, lang: str) -> bool:
        """Check if language is supported."""
        return lang in self.SUPPORTED_LANGUAGES

    def get_language_name(self, lang: str) -> str:
        """Get display name for language."""
        return self.LANGUAGE_NAMES.get(
            lang, lang.upper()
        )


# ━━━ SINGLETON INSTANCE ━━━
i18n = I18n()


# ━━━ SHORTCUT FUNCTION ━━━
def _(
    key: str,
    lang: Optional[str] = None,
    **kwargs
) -> str:
    """Shortcut for i18n.get()"""
    return i18n.get(key, lang, **kwargs)