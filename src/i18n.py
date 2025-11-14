"""
Internationalization (i18n) support for MCP server.
Supports English and Ukrainian languages.
"""
import json
import os
from pathlib import Path
from typing import Optional


class I18n:
    """Internationalization helper class."""

    SUPPORTED_LANGUAGES = ["en", "uk"]
    DEFAULT_LANGUAGE = "en"

    def __init__(self, language: Optional[str] = None):
        """
        Initialize i18n with specified language.

        Args:
            language: Language code ('en' or 'uk'). Defaults to 'en'.
        """
        self.language = language or self.DEFAULT_LANGUAGE
        if self.language not in self.SUPPORTED_LANGUAGES:
            self.language = self.DEFAULT_LANGUAGE

        self.translations = self._load_translations()

    def _load_translations(self) -> dict:
        """Load translations from JSON file."""
        translations_dir = Path(__file__).parent / "translations"
        translation_file = translations_dir / f"{self.language}.json"

        if not translation_file.exists():
            # Fallback to default language
            translation_file = translations_dir / f"{self.DEFAULT_LANGUAGE}.json"

        with open(translation_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def t(self, key: str, **kwargs) -> str:
        """
        Translate a key with optional parameters.

        Args:
            key: Translation key in dot notation (e.g., 'messages.address_saved')
            **kwargs: Parameters to format into the translation string

        Returns:
            Translated and formatted string

        Example:
            >>> i18n = I18n('en')
            >>> i18n.t('messages.address_saved', address='м. Київ, Вул. Хрещатик, 1')
            '✓ Address saved: м. Київ, Вул. Хрещатик, 1...'
        """
        keys = key.split('.')
        value = self.translations

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return key  # Return key if translation not found

        if value is None:
            return key

        # Format with parameters if provided
        if kwargs:
            try:
                return value.format(**kwargs)
            except (KeyError, ValueError):
                return value

        return value

    def set_language(self, language: str):
        """
        Change the current language.

        Args:
            language: Language code ('en' or 'uk')
        """
        if language in self.SUPPORTED_LANGUAGES:
            self.language = language
            self.translations = self._load_translations()

    def get_language(self) -> str:
        """Get current language code."""
        return self.language

    def get_supported_languages(self) -> list[str]:
        """Get list of supported language codes."""
        return self.SUPPORTED_LANGUAGES


# Global i18n instance (will be configured from config)
_i18n_instance: Optional[I18n] = None


def get_i18n() -> I18n:
    """
    Get global i18n instance.

    Returns:
        Global I18n instance
    """
    global _i18n_instance
    if _i18n_instance is None:
        # Import here to avoid circular dependency
        try:
            from .config import config
        except ImportError:
            from config import config
        language = config.get_language() if hasattr(config, 'get_language') else 'en'
        _i18n_instance = I18n(language)
    return _i18n_instance


def set_language(language: str):
    """
    Set language for global i18n instance.

    Args:
        language: Language code ('en' or 'uk')
    """
    global _i18n_instance
    if _i18n_instance is None:
        _i18n_instance = I18n(language)
    else:
        _i18n_instance.set_language(language)
