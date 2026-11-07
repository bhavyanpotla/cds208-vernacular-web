"""Phase 1 tests: the provider adapter and the translation service.

The contract being tested is the one the whole app depends on:
empty and same-language calls cost nothing, mock mode never pretends to be
real, a second identical call is served from cache, and a provider failure
degrades instead of raising.
"""

from __future__ import annotations

import pytest

from core import config, db, events, llm
from core import translate as translator


@pytest.fixture(autouse=True)
def clean_memory_cache():
    translator.reset_memory_cache()
    yield
    translator.reset_memory_cache()


def _mock_mode(monkeypatch):
    monkeypatch.delenv("SARVAM_API_KEY", raising=False)
    monkeypatch.delenv("VE_PROVIDER", raising=False)


def _live_mode(monkeypatch):
    monkeypatch.setenv("SARVAM_API_KEY", "sk-test-not-a-real-key")
    monkeypatch.delenv("VE_PROVIDER", raising=False)


# ------------------------------------------------------------------ no-op paths


def test_empty_text_is_a_noop_and_writes_nothing():
    result = translator.translate("   ", source="en-IN", target="hi-IN")
    assert result["provider"] == "noop"
    assert result["text"] == ""
    assert db.translation_stats()["total"] == 0


def test_same_language_passes_through_untouched():
    result = translator.translate("The plant makes food.", source="en-IN", target="en-IN")
    assert result["provider"] == "noop"
    assert result["text"] == "The plant makes food."
    assert db.translation_stats()["total"] == 0


# ------------------------------------------------------------------ mock mode


def test_mock_mode_is_labelled_not_faked(monkeypatch):
    _mock_mode(monkeypatch)
    result = translator.translate("Chlorophyll absorbs light.", source="en-IN", target="hi-IN")
    assert result["provider"] == "mock"
    assert "mock" in result["text"].lower()
    assert result["degraded"] is False


def test_mock_dictionary_translates_known_words(monkeypatch):
    _mock_mode(monkeypatch)
    result = translator.translate("plant water food", source="en-IN", target="hi-IN")
    assert result["text"] == "पौधा पानी भोजन"


def test_mock_translation_is_stored_and_logged(monkeypatch):
    _mock_mode(monkeypatch)
    translator.translate("Chlorophyll absorbs light.", source="en-IN", target="te-IN")
    assert db.translation_stats()["total"] == 1
    assert events.event_counts().get("translation_requested") == 1


# --------------------------------------------------------------------- caching


def test_second_identical_call_is_served_from_cache(monkeypatch):
    _mock_mode(monkeypatch)
    first = translator.translate("The leaf is green.", source="en-IN", target="hi-IN")
    second = translator.translate("The leaf is green.", source="en-IN", target="hi-IN")

    assert first["provider"] == "mock"
    assert second["provider"] == "cache"
    assert second["cached"] is True
    assert second["text"] == first["text"]
    assert db.translation_stats()["total"] == 1, "cache hit must not write a second row"


def test_memory_cache_is_skipped_across_provider_modes(monkeypatch):
    _mock_mode(monkeypatch)
    translator.translate("The leaf is green.", source="en-IN", target="hi-IN")
    _live_mode(monkeypatch)
    # A mock result must never be served once a key is present.
    assert translator.memory_cache_size() == 1
    result = translator.translate("The leaf is green.", source="en-IN", target="hi-IN")
    assert result["provider"] != "cache" or "mock" not in result["text"].lower()


def test_mock_results_are_not_reused_from_the_db(monkeypatch):
    _mock_mode(monkeypatch)
    translator.translate("The leaf is green.", source="en-IN", target="hi-IN")
    translator.reset_memory_cache()
    # Same text, same mode, memory cleared: the DB row is a mock row, so it is
    # not treated as a cache hit — it is recomputed.
    result = translator.translate("The leaf is green.", source="en-IN", target="hi-IN")
    assert result["provider"] == "mock"
    assert db.translation_stats()["total"] == 2


# ------------------------------------------------------- provider degradation


def test_provider_error_degrades_to_mock_without_raising(monkeypatch):
    _live_mode(monkeypatch)

    def boom(*args, **kwargs):
        raise RuntimeError("connection reset by peer")

    monkeypatch.setattr(llm, "_post", boom)
    result = translator.translate("The leaf is green.", source="en-IN", target="hi-IN")

    assert result["provider"] == "mock"
    assert result["degraded"] is True
    assert "connection reset" in (result["error"] or "")
    assert events.event_counts().get("translation_failed") == 1


def test_live_success_is_reported_as_sarvam(monkeypatch):
    _live_mode(monkeypatch)
    monkeypatch.setattr(
        llm, "_post", lambda path, payload: {"translated_text": "पत्ती हरी है।"}
    )
    result = translator.translate("The leaf is green.", source="en-IN", target="hi-IN")
    assert result["provider"] == "sarvam"
    assert result["text"] == "पत्ती हरी है।"
    assert result["degraded"] is False


# ------------------------------------------------------------------- chunking


def test_long_text_is_chunked_under_the_provider_limit():
    sentence = "Plants need sunlight to make food. "  # 37 chars
    long_text = sentence * 60  # ~2220 chars, over the 1000-char limit
    chunks = llm._chunk(long_text.strip(), limit=llm.MAYURA_MAX_CHARS)
    assert len(chunks) >= 3
    assert all(len(chunk) <= llm.MAYURA_MAX_CHARS for chunk in chunks)
    assert "".join(chunks).replace(" ", "") == long_text.strip().replace(" ", "")


def test_chunking_keeps_short_text_in_one_piece():
    assert llm._chunk("Short sentence.", limit=1000) == ["Short sentence."]


# ------------------------------------------------------------------- config


def test_translate_model_defaults_to_mayura(monkeypatch):
    monkeypatch.delenv("TRANSLATE_MODEL", raising=False)
    assert config.translate_model() == "mayura:v1"
