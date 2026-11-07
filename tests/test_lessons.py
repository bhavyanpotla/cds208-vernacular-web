"""Phase 2 tests: lesson loading, localisation, glossary, quiz scoring."""

from __future__ import annotations

import pytest

from core import db, events, lessons, quiz
from core import translate as translator


@pytest.fixture(autouse=True)
def clean_caches():
    translator.reset_memory_cache()
    lessons.reload()
    yield
    translator.reset_memory_cache()
    lessons.reload()


def _mock_mode(monkeypatch):
    monkeypatch.delenv("SARVAM_API_KEY", raising=False)
    monkeypatch.delenv("VE_PROVIDER", raising=False)


# --------------------------------------------------------------------- loading


def test_all_lessons_load_with_unique_ids():
    catalogue = lessons.all_lessons()
    assert len(catalogue) == 4
    ids = [item["id"] for item in catalogue]
    assert len(ids) == len(set(ids))
    for item in catalogue:
        assert item["segments"], f'{item["id"]} has no segments'
        assert item["quiz"], f'{item["id"]} has no quiz'


def test_every_lesson_has_english_and_hindi_authored():
    for item in lessons.all_lessons():
        for item_segment in item["segments"]:
            assert item_segment["text"].get("en-IN")
            assert item_segment["text"].get("hi-IN")


def test_key_terms_are_distinct_and_ordered():
    lesson = lessons.get("science-photosynthesis-01")
    terms = lessons.key_terms(lesson)
    assert terms[0] == "photosynthesis"
    assert len(terms) == len(set(terms))


def test_unknown_lesson_returns_none():
    assert lessons.get("does-not-exist") is None


# ----------------------------------------------------------------- localising


def test_authored_language_is_used_without_calling_the_provider(monkeypatch):
    _mock_mode(monkeypatch)
    lesson = lessons.get("science-photosynthesis-01")
    text = lessons.segment_text(lesson, lesson["segments"][0], "hi-IN")
    assert text.startswith("पौधे अपना भोजन")
    assert db.translation_stats()["total"] == 0, "authored text must not hit the service"


def test_missing_language_is_filled_by_the_service(monkeypatch):
    _mock_mode(monkeypatch)
    lesson = lessons.get("science-photosynthesis-01")
    text = lessons.segment_text(lesson, lesson["segments"][0], "te-IN")
    assert text
    assert db.translation_stats()["total"] == 1

    # a repeat read is served from the memory cache, so no second row appears
    again = lessons.segment_text(lesson, lesson["segments"][0], "te-IN")
    assert again == text
    assert db.translation_stats()["total"] == 1


def test_a_live_translation_is_reused_from_the_database(monkeypatch):
    from core import llm

    monkeypatch.setenv("SARVAM_API_KEY", "sk-test-not-a-real-key")
    monkeypatch.delenv("VE_PROVIDER", raising=False)
    monkeypatch.setattr(
        llm, "_post", lambda path, payload: {"translated_text": "మొక్కలు ఆహారం తయారు చేస్తాయి."}
    )
    lesson = lessons.get("science-photosynthesis-01")
    first = lessons.segment_text(lesson, lesson["segments"][0], "te-IN")
    assert db.translation_stats()["total"] == 1

    translator.reset_memory_cache()  # the DB row is now the only defence
    second = lessons.segment_text(lesson, lesson["segments"][0], "te-IN")
    assert second == first
    assert db.translation_stats()["total"] == 1, "the second read must come from the DB"


def test_glossary_entry_reports_provenance(monkeypatch):
    _mock_mode(monkeypatch)
    authored = lessons.glossary_entry("chlorophyll", "hi-IN")
    assert authored["authored"] == "yes"
    assert "हरा पदार्थ" in authored["meaning"]

    translated = lessons.glossary_entry("chlorophyll", "ta-IN")
    assert translated["authored"] == "translated"
    assert translated["meaning"]


def test_unknown_glossary_term_returns_none():
    assert lessons.glossary_entry("nonexistent-term", "hi-IN") is None


def test_quiz_question_is_localised(monkeypatch):
    _mock_mode(monkeypatch)
    lesson = lessons.get("maths-fractions-03")
    question = lessons.quiz_question(lesson, 0, "hi-IN")
    assert "अंश" in question["q"]
    assert len(question["options"]) == 3
    assert question["answer_index"] == 0


# ---------------------------------------------------------------------- quiz


def test_perfect_score_passes():
    result = quiz.score([0, 0, 0], [0, 0, 0])
    assert result == {"correct": 3, "total": 3, "percent": 100, "passed": True}


def test_below_pass_mark_fails():
    result = quiz.score([1, 1, 0], [0, 0, 0])
    assert result["correct"] == 1
    assert result["percent"] == 33
    assert result["passed"] is False


def test_skipped_answers_count_as_wrong_not_as_errors():
    result = quiz.score([None, 0, None], [0, 0, 0])
    assert result["correct"] == 1
    assert result["total"] == 3
    assert result["passed"] is False


def test_empty_quiz_does_not_divide_by_zero():
    assert quiz.score([], []) == {
        "correct": 0,
        "total": 0,
        "percent": 0,
        "passed": False,
    }


def test_record_attempt_writes_progress_and_events():
    lesson = lessons.get("science-water-cycle-02")
    result = quiz.score([0, 0, 0], quiz.answer_key(lesson))
    user_id = db.ensure_local_user()
    quiz.record_attempt(lesson, result, user_id=user_id, lang="hi-IN")

    stored = db.lesson_progress(user_id, lesson["id"])
    assert stored["status"] == "quiz_passed"
    assert stored["score"] == 1.0

    counts = events.event_counts()
    assert counts["quiz_submitted"] == 1
    assert counts["quiz_passed"] == 1


def test_failed_attempt_is_recorded_as_completed_not_passed():
    lesson = lessons.get("science-water-cycle-02")
    result = quiz.score([1, 1, 1], quiz.answer_key(lesson))
    user_id = db.ensure_local_user()
    quiz.record_attempt(lesson, result, user_id=user_id, lang="te-IN")

    assert db.lesson_progress(user_id, lesson["id"])["status"] == "completed"
    assert events.event_counts().get("quiz_passed") is None


def test_repeating_a_quiz_updates_the_row_instead_of_duplicating():
    lesson = lessons.get("science-sound-04")
    user_id = db.ensure_local_user()
    quiz.record_attempt(lesson, quiz.score([1, 1, 1], quiz.answer_key(lesson)), user_id=user_id)
    quiz.record_attempt(lesson, quiz.score([0, 0, 0], quiz.answer_key(lesson)), user_id=user_id)

    assert db.progress_summary(user_id)["lessons_touched"] == 1
    assert db.lesson_progress(user_id, lesson["id"])["status"] == "quiz_passed"
