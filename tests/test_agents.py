"""Phase 3 tests: the tutor's grounding rule and the recommender's fallbacks."""

from __future__ import annotations

import json

import pytest

from agents import coach, phrases, tutor
from core import db, events, lessons, llm
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


def _live_mode(monkeypatch):
    monkeypatch.setenv("SARVAM_API_KEY", "sk-test-not-a-real-key")
    monkeypatch.delenv("VE_PROVIDER", raising=False)


# -------------------------------------------------------------------- grounding


def test_is_grounded_detects_a_question_the_lesson_answers():
    lesson = lessons.get("science-photosynthesis-01")
    body = tutor._lesson_body(lesson)
    assert tutor.is_grounded("What do plants need to make food?", body) is True


def test_is_grounded_rejects_an_unrelated_question():
    lesson = lessons.get("science-photosynthesis-01")
    body = tutor._lesson_body(lesson)
    assert tutor.is_grounded("Who won the cricket world cup in 2011?", body) is False


def test_is_grounded_keeps_digits_so_maths_questions_work():
    lesson = lessons.get("maths-fractions-03")
    body = tutor._lesson_body(lesson)
    assert tutor.is_grounded("what is 3/4", body) is True


# ----------------------------------------------------------------- tutor answers


def test_grounded_question_is_answered_from_the_lesson(monkeypatch):
    _mock_mode(monkeypatch)
    lesson = lessons.get("science-photosynthesis-01")
    result = tutor.answer(
        "What do plants need to make food?",
        lesson=lesson,
        segment=lesson["segments"][0],
        lang="hi-IN",
        user_id=1,
    )
    assert result["grounded"] is True
    assert result["refused"] is False
    assert result["provider"] == "mock"
    assert "पौधे" in result["text"], "the answer is the lesson text, in Hindi"


def test_ungrounded_question_is_refused_not_invented(monkeypatch):
    _mock_mode(monkeypatch)
    lesson = lessons.get("science-photosynthesis-01")
    result = tutor.answer(
        "Who won the cricket world cup?",
        lesson=lesson,
        segment=lesson["segments"][0],
        lang="en-IN",
        user_id=1,
    )
    assert result["grounded"] is False
    assert result["refused"] is True
    assert phrases.p("refusal", "en-IN") in result["text"]
    assert "cricket" not in result["text"].lower()


def test_refusal_is_in_the_learners_language(monkeypatch):
    _mock_mode(monkeypatch)
    lesson = lessons.get("science-water-cycle-02")
    result = tutor.answer(
        "Who won the cricket world cup?",
        lesson=lesson,
        segment=lesson["segments"][0],
        lang="te-IN",
        user_id=1,
    )
    assert phrases.p("refusal", "te-IN") in result["text"]


def test_tutor_logs_both_the_question_and_the_refusal(monkeypatch):
    _mock_mode(monkeypatch)
    lesson = lessons.get("science-sound-04")
    tutor.answer("Who won the cricket world cup?", lesson=lesson, lang="hi-IN", user_id=1)
    counts = events.event_counts()
    assert counts["tutor_question_asked"] == 1
    assert counts["tutor_refused_ungrounded"] == 1


def test_empty_question_is_a_noop(monkeypatch):
    _mock_mode(monkeypatch)
    lesson = lessons.get("science-sound-04")
    result = tutor.answer("  ", lesson=lesson, lang="hi-IN", user_id=1)
    assert result["provider"] == "noop"
    assert events.event_counts() == {}


def test_live_provider_answer_is_used_when_it_returns(monkeypatch):
    _live_mode(monkeypatch)
    monkeypatch.setattr(
        llm, "chat", lambda messages, **kwargs: llm.ChatReply(text="आवाज़ कंपन से बनती है।", provider="sarvam")
    )
    lesson = lessons.get("science-sound-04")
    result = tutor.answer(
        "How is sound made?", lesson=lesson, segment=lesson["segments"][0], lang="hi-IN"
    )
    assert result["provider"] == "sarvam"
    assert result["text"] == "आवाज़ कंपन से बनती है।"


def test_provider_failure_falls_back_to_the_offline_answer(monkeypatch):
    _live_mode(monkeypatch)
    monkeypatch.setattr(
        llm, "chat", lambda messages, **kwargs: llm.ChatReply(text="", provider="mock", degraded=True, error="timeout")
    )
    lesson = lessons.get("science-sound-04")
    result = tutor.answer(
        "How is sound made?", lesson=lesson, segment=lesson["segments"][0], lang="hi-IN"
    )
    assert result["provider"] == "mock"
    assert result["degraded"] is True
    assert result["text"], "the student still gets a lesson-derived answer"


# ------------------------------------------------------------------ recommender


def test_recommender_works_with_an_empty_database(monkeypatch):
    _mock_mode(monkeypatch)
    result = coach.recommend(user_id=None, lang="en-IN")
    assert result["next_lesson_id"] in lessons.lesson_ids()
    assert result["source"] == "rules"
    assert result["reason"]


def test_passing_a_lesson_moves_the_recommendation_on(monkeypatch):
    _mock_mode(monkeypatch)
    user_id = db.ensure_local_user()
    first = coach.rule_based(user_id, "en-IN")["next_lesson_id"]

    db.upsert_progress(user_id, first, None, "quiz_passed", 1.0)
    second = coach.rule_based(user_id, "en-IN")

    assert second["next_lesson_id"] != first
    assert second["difficulty"] == "core"


def test_a_failed_quiz_means_revisit_the_same_lesson(monkeypatch):
    _mock_mode(monkeypatch)
    user_id = db.ensure_local_user()
    lesson_id = lessons.lesson_ids()[0]
    db.upsert_progress(user_id, lesson_id, None, "completed", 0.33)

    result = coach.rule_based(user_id, "en-IN")
    assert result["next_lesson_id"] == lesson_id
    assert result["difficulty"] == "easy"
    assert "33%" in result["reason"]


def test_everything_passed_means_stretch(monkeypatch):
    _mock_mode(monkeypatch)
    user_id = db.ensure_local_user()
    for index, lesson_id in enumerate(lessons.lesson_ids()):
        db.upsert_progress(user_id, lesson_id, None, "quiz_passed", 0.7 + index * 0.05)

    result = coach.rule_based(user_id, "en-IN")
    assert result["difficulty"] == "stretch"
    assert result["next_lesson_id"] in lessons.lesson_ids()


def test_reason_is_localised(monkeypatch):
    _mock_mode(monkeypatch)
    user_id = db.ensure_local_user()
    result = coach.rule_based(user_id, "hi-IN")
    assert "अभी खोला नहीं" in result["reason"]


def test_unparsable_model_output_falls_back_to_the_rules(monkeypatch):
    _live_mode(monkeypatch)
    monkeypatch.setattr(
        llm, "chat", lambda messages, **kwargs: llm.ChatReply(text="I think lesson two?", provider="sarvam")
    )
    user_id = db.ensure_local_user()
    result = coach.recommend(user_id, "en-IN")
    assert result["source"] == "rules"
    assert result["next_lesson_id"] in lessons.lesson_ids()


def test_model_cannot_recommend_an_id_outside_the_catalogue(monkeypatch):
    _live_mode(monkeypatch)
    payload = json.dumps(
        {
            "next_lesson_id": "made-up-lesson",
            "difficulty": "core",
            "reason": "Trust me.",
            "focus_terms": ["x"],
        }
    )
    monkeypatch.setattr(
        llm, "chat", lambda messages, **kwargs: llm.ChatReply(text=payload, provider="sarvam")
    )
    result = coach.recommend(db.ensure_local_user(), "en-IN")
    assert result["source"] == "rules"
    assert result["next_lesson_id"] in lessons.lesson_ids()


def test_valid_model_output_is_accepted_and_logged(monkeypatch):
    _live_mode(monkeypatch)
    target = lessons.lesson_ids()[1]
    payload = json.dumps(
        {
            "next_lesson_id": target,
            "difficulty": "stretch",
            "reason": "You are ready for this one.",
            "focus_terms": ["chlorophyll"],
        }
    )
    monkeypatch.setattr(
        llm, "chat", lambda messages, **kwargs: llm.ChatReply(text=payload, provider="sarvam")
    )
    result = coach.recommend(db.ensure_local_user(), "en-IN")

    assert result["source"] == "model"
    assert result["next_lesson_id"] == target
    assert result["difficulty"] == "stretch"
    assert events.event_counts()["recommendation_shown"] == 1
