"""Quiz scoring and recording.

Scoring is pure arithmetic so it can be tested without Streamlit, a database
or a model. Recording is the only side effect, and it writes both the
``progress`` row and the event that the analytics pages read.
"""

from __future__ import annotations

from typing import Any

from core import db, events

PASS_MARK = 0.6


def score(answers: list[int | None], answer_key: list[int]) -> dict[str, Any]:
    """Compare submitted answers with the key.

    ``answers`` may contain ``None`` for a skipped question — a skip is wrong,
    not an error, so the student still gets a score and a reason.
    """
    total = len(answer_key)
    correct = sum(
        1
        for given, expected in zip(answers, answer_key, strict=False)
        if given is not None and int(given) == int(expected)
    )
    percent = round((correct / total) * 100) if total else 0
    return {
        "correct": correct,
        "total": total,
        "percent": percent,
        "passed": bool(total and (correct / total) >= PASS_MARK),
    }


def answer_key(lesson: dict[str, Any]) -> list[int]:
    return [int(question["answer_index"]) for question in lesson.get("quiz", [])]


def record_attempt(
    lesson: dict[str, Any],
    result: dict[str, Any],
    user_id: int | None = None,
    lang: str | None = None,
) -> None:
    """Write the progress row and the two events the dashboard reads."""
    status = "quiz_passed" if result["passed"] else "completed"
    if user_id is not None:
        db.upsert_progress(
            user_id=user_id,
            lesson_id=lesson["id"],
            segment_id=None,
            status=status,
            score=float(result["percent"]) / 100,
        )
    events.log_event(
        "quiz_submitted",
        user_id=user_id,
        lang=lang,
        lesson_id=lesson["id"],
        subject=lesson.get("subject"),
        score=result["percent"],
        correct=result["correct"],
        total=result["total"],
        passed=result["passed"],
    )
    if result["passed"]:
        events.log_event(
            "quiz_passed",
            user_id=user_id,
            lang=lang,
            lesson_id=lesson["id"],
            score=result["percent"],
        )
