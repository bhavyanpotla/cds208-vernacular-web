"""Phase 4 tests: the export pipeline and the numbers the dashboard reads."""

from __future__ import annotations

import json

import pytest

from core import db, events, export, lessons


@pytest.fixture(autouse=True)
def clean_caches():
    lessons.reload()
    yield
    lessons.reload()


def _seed(user_id: int | None = None) -> None:
    """A handful of realistic events, enough for every chart to have data."""
    events.log_event("app_opened", user_id=user_id, lang="en-IN", session_id="s1")
    events.log_event(
        "translation_requested",
        user_id=user_id,
        lang="hi-IN",
        session_id="s1",
        source="en-IN",
        target="hi-IN",
        provider="mock",
        latency_ms=42,
        context="translate_page",
    )
    events.log_event(
        "translation_served",
        user_id=user_id,
        lang="hi-IN",
        session_id="s1",
        source="en-IN",
        target="hi-IN",
        layer="db",
    )
    events.log_event(
        "term_glossed",
        user_id=user_id,
        lang="te-IN",
        session_id="s1",
        lesson_id="science-photosynthesis-01",
        term="chlorophyll",
    )
    events.log_event(
        "term_glossed",
        user_id=user_id,
        lang="te-IN",
        session_id="s1",
        lesson_id="science-photosynthesis-01",
        term="chlorophyll",
    )
    events.log_event(
        "quiz_submitted",
        user_id=user_id,
        lang="hi-IN",
        session_id="s1",
        lesson_id="science-photosynthesis-01",
        score=100,
        passed=True,
    )
    db.save_translation(
        "The leaf is green.", "en-IN", "hi-IN", "पत्ती हरी है।", "mock", 42, user_id=user_id
    )


def test_export_writes_all_five_files(tmp_path):
    health = export.run_export(tmp_path)
    for name in export.FACT_FILES:
        assert (tmp_path / name).exists(), f"{name} missing"
    assert (tmp_path / "_health.json").exists()
    assert health["rows"]["dim_lessons"] == len(lessons.all_lessons())


def test_props_are_promoted_to_columns(tmp_path):
    _seed()
    export.run_export(tmp_path)
    frame = __import__("pandas").read_csv(tmp_path / "fact_events.csv")

    assert {"provider", "target_lang", "latency_ms", "lesson_id", "term"} <= set(frame.columns)
    assert "props" not in frame.columns

    translations = frame[frame["event_name"] == "translation_requested"].iloc[0]
    assert translations["target_lang"] == "hi-IN"
    assert int(translations["latency_ms"]) == 42


def test_time_columns_are_added(tmp_path):
    _seed()
    export.run_export(tmp_path)
    frame = __import__("pandas").read_csv(tmp_path / "fact_events.csv")
    assert "date" in frame.columns
    assert frame["date"].notna().all()


def test_health_counts_match_the_files(tmp_path):
    _seed()
    health = export.run_export(tmp_path)
    frame = __import__("pandas").read_csv(tmp_path / "fact_events.csv")
    # the export itself logs export_refreshed after counting, so the file may be one ahead
    assert health["rows"]["fact_events"] in {len(frame), len(frame) - 1}
    assert health["provider_mode"] in {"mock", "sarvam"}
    assert 0.0 <= health["cache_hit_rate"] <= 1.0


def test_empty_database_still_writes_valid_files(tmp_path):
    health = export.run_export(tmp_path)
    assert (tmp_path / "fact_events.csv").exists()
    assert health["rows"]["fact_events"] == 0
    assert any("empty" in warning for warning in health["warnings"])
    assert health["cache_hit_rate"] == 0.0


def test_event_coverage_audit_lists_unfired_events(tmp_path):
    health = export.run_export(tmp_path)
    assert health["event_types_documented"] == len(events.EVENT_NAMES)
    assert "word_saved" in health["events_never_fired"]
    assert "app_opened" not in health["events_never_fired"] or health["rows"]["fact_events"] == 0


def test_health_file_is_reloadable(tmp_path):
    export.run_export(tmp_path)
    reloaded = export.read_health(tmp_path)
    assert reloaded["rows"]["dim_lessons"] == len(lessons.all_lessons())
    json.dumps(reloaded)  # must be plain JSON


def test_struggle_list_ranks_tapped_terms():
    _seed()
    terms = export.terms_most_translated()
    assert list(terms["term"])[0] == "chlorophyll"
    assert int(terms["taps"].iloc[0]) == 2


def test_headline_numbers_read_from_the_log():
    _seed()
    numbers = export.headline_numbers()
    assert numbers["events"] >= 6
    assert numbers["translations"] == 1
    assert numbers["cache_hit_rate"] == 0.5
    assert numbers["quizzes"] == 1
    assert numbers["avg_latency_ms"] == 42


def test_export_logs_its_own_event(tmp_path):
    export.run_export(tmp_path)
    assert events.event_counts().get("export_refreshed") == 1
