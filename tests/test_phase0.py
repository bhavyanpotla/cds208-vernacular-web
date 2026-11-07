"""Phase 0 tests: config, i18n and the event log.

Each test points ``VE_DB_PATH`` at a temp file, so the suite never touches
the real database and runs identically on a clean checkout.
"""

from __future__ import annotations

import json

import pytest

from core import config, db, events


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setenv("VE_DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    yield


def test_language_registry_is_complete():
    assert config.DEFAULT_LANG == "en-IN"
    assert len(config.LANG_CODES) == 5
    for code in config.LANG_CODES:
        entry = config.LANGUAGES[code]
        assert entry["native"].strip(), f"{code} has no native label"
        assert entry["script"].strip(), f"{code} has no script name"


def test_missing_key_means_mock_mode(monkeypatch):
    monkeypatch.delenv("SARVAM_API_KEY", raising=False)
    monkeypatch.delenv("VE_PROVIDER", raising=False)
    assert config.provider_mode() == "mock"
    assert config.is_mock_mode() is True


def test_key_present_means_live_mode(monkeypatch):
    monkeypatch.setenv("SARVAM_API_KEY", "sk-test-not-a-real-key")
    monkeypatch.delenv("VE_PROVIDER", raising=False)
    assert config.provider_mode() == "sarvam"


def test_translation_falls_back_to_english():
    from core.i18n import UI_STRINGS, coverage, t

    assert t("tagline", "en-IN") == UI_STRINGS["tagline"]["en-IN"]
    assert t("tagline", "xx-XX") == UI_STRINGS["tagline"]["en-IN"]
    assert t("no_such_key", "hi-IN") == "no_such_key"
    assert coverage()["hi-IN"] > 0


def test_event_is_appended_with_props():
    events.log_event(
        "translation_requested",
        user_id=1,
        lang="te-IN",
        session_id="sess-test",
        source_lang="en-IN",
        target_lang="te-IN",
        chars=42,
    )
    rows = events.recent_events(limit=1)
    assert len(rows) == 1
    assert rows[0]["event_name"] == "translation_requested"
    assert rows[0]["lang"] == "te-IN"
    props = json.loads(rows[0]["props"])
    assert props["target_lang"] == "te-IN"
    assert props["chars"] == 42


def test_events_are_append_only():
    for index in range(3):
        events.log_event("page_viewed", user_id=1, page=f"p{index}")
    counts = events.event_counts()
    assert counts["page_viewed"] == 3
    assert len(events.recent_events(limit=10)) == 3


def test_init_db_is_idempotent():
    db.init_db()
    db.init_db()
    user_id = db.ensure_local_user()
    assert db.ensure_local_user() == user_id
    assert user_id >= 1
