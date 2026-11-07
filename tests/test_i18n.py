"""Every UI string must exist in every supported language.

This is the test that keeps the vernacular claim honest: a missing translation
does not crash the app (it falls back to English), which is exactly why it would
otherwise go unnoticed until an examiner switches the language and sees a
half-English page.
"""

from __future__ import annotations

from core import config
from core.i18n import UI_STRINGS, coverage, t


def test_every_key_has_every_language():
    missing = {
        key: [code for code in config.LANG_CODES if not entry.get(code)]
        for key, entry in UI_STRINGS.items()
    }
    missing = {key: codes for key, codes in missing.items() if codes}
    assert not missing, f"missing translations: {missing}"


def test_no_translation_is_blank_or_english_placeholder():
    for key, entry in UI_STRINGS.items():
        for code, value in entry.items():
            assert value.strip(), f"{key}/{code} is blank"
            assert value != "TODO", f"{key}/{code} is a placeholder"


def test_coverage_is_complete_for_every_language():
    total = len(UI_STRINGS)
    assert coverage() == {code: total for code in config.LANG_CODES}


def test_indic_languages_use_their_own_script():
    """A Hindi string must contain Devanagari, a Telugu one Telugu, and so on."""
    ranges = {
        "hi-IN": (0x0900, 0x097F),
        "bn-IN": (0x0980, 0x09FF),
        "ta-IN": (0x0B80, 0x0BFF),
        "te-IN": (0x0C00, 0x0C7F),
    }
    for code, (low, high) in ranges.items():
        sample = t("tagline", code)
        assert any(low <= ord(char) <= high for char in sample), (
            f"{code} string is not in its own script: {sample!r}"
        )


def test_unknown_language_falls_back_to_english():
    assert t("tagline", "fr-FR") == UI_STRINGS["tagline"]["en-IN"]
