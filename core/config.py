"""Environment, feature flags and the language registry.

This is the only module that reads ``os.environ``. Everything else asks
``config`` for a value, which keeps tests free of environment juggling and
makes the mock-mode switch a one-line change.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
EXPORT_DIR = BASE_DIR / "exports"
CONTENT_DIR = BASE_DIR / "content"
WEB_DIR = BASE_DIR / "web"
ASSETS_DIR = WEB_DIR / "assets"

load_dotenv(BASE_DIR / ".env")

APP_NAME = "Vernacular Learning Platform"
APP_SHORT = "Vernacular"
DEFAULT_LANG = "en-IN"

# Five languages, done properly. Adding one is a single dict entry plus its
# UI strings in core/i18n.py — nothing else in the app hardcodes a language.
LANGUAGES: dict[str, dict[str, str]] = {
    "en-IN": {"label": "English", "native": "English", "script": "Latin"},
    "hi-IN": {"label": "Hindi", "native": "हिन्दी", "script": "Devanagari"},
    "bn-IN": {"label": "Bengali", "native": "বাংলা", "script": "Bengali"},
    "ta-IN": {"label": "Tamil", "native": "தமிழ்", "script": "Tamil"},
    "te-IN": {"label": "Telugu", "native": "తెలుగు", "script": "Telugu"},
}

LANG_CODES: list[str] = list(LANGUAGES)
INDIC_LANG_CODES: list[str] = [code for code in LANG_CODES if code != DEFAULT_LANG]


def _env(name: str, default: str = "") -> str:
    """Read an env var, treating blank and placeholder values as unset."""
    value = (os.getenv(name) or "").strip()
    if value.lower() in {"", "none", "null", "your_key_here", "<your_key>"}:
        return default
    return value


def sarvam_api_key() -> str:
    return _env("SARVAM_API_KEY")


def provider_mode() -> str:
    """The provider the app will actually use right now: ``sarvam`` or ``mock``.

    A key present but no network still resolves to ``sarvam`` here — the
    adapter in ``core/llm.py`` (Phase 1) degrades to mock at call time and
    says so. This function only answers "is a key configured".
    """
    if _env("VE_PROVIDER", "auto").lower() == "mock":
        return "mock"
    return "sarvam" if sarvam_api_key() else "mock"


def is_mock_mode() -> bool:
    return provider_mode() == "mock"


def export_dir() -> Path:
    """Where the Power BI CSVs land. ``VE_EXPORT_DIR`` overrides it (tests)."""
    override = _env("VE_EXPORT_DIR")
    return Path(override) if override else EXPORT_DIR


def db_path() -> Path:
    """SQLite file location. ``VE_DB_PATH`` overrides it (used by tests)."""
    override = _env("VE_DB_PATH")
    return Path(override) if override else DATA_DIR / "app.db"


def translate_model() -> str:
    """Sarvam translation model. mayura:v1 handles 1000 chars per request."""
    return _env("TRANSLATE_MODEL", "mayura:v1")


def translate_mode() -> str:
    """formal | modern-colloquial | classic-colloquial | code-mixed."""
    return _env("TRANSLATE_MODE", "modern-colloquial")


def chat_model() -> str:
    """Sarvam chat model, on the OpenAI-compatible /v1/chat/completions route."""
    return _env("CHAT_MODEL", "sarvam-m")


def request_timeout() -> int:
    return int(_env("VE_REQUEST_TIMEOUT", "20"))


def request_retries() -> int:
    return int(_env("VE_REQUEST_RETRIES", "1"))


def flag(name: str, default: bool = False) -> bool:
    """Boolean feature flag, e.g. ``flag("VE_ENABLE_SPEECH")``."""
    raw = _env(name)
    if not raw:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


def speech_enabled() -> bool:
    """Speech is on the cut list; this keeps it a flag, not a rewrite."""
    return flag("VE_ENABLE_SPEECH", default=False)


def generated_quiz_enabled() -> bool:
    return flag("VE_ENABLE_GENERATED_QUIZ", default=False)
