"""The personalisation agent: decides the next lesson, and says why.

The deterministic rules are the product. A model may phrase the reason better,
but it never gets to choose an id outside the catalogue, and if it returns
anything unparsable we fall straight back to the rules — so the recommender
still returns a valid lesson with an empty database, a dead provider or a
junk response. That is the acceptance test for this phase.
"""

from __future__ import annotations

import json
from typing import Any

from agents import prompts
from core import config, db, events, lessons, llm
from core import translate as translator

# Authored in English and Hindi; other languages are filled by the service and
# cached, exactly like lesson content.
REASONS: dict[str, dict[str, str]] = {
    "start": {
        "en-IN": 'You have not opened "{title}" yet. Start there — it is short and '
        "sets up the rest of the topic.",
        "hi-IN": 'आपने "{title}" अभी खोला नहीं है। वहीं से शुरू करें — यह छोटा है और '
        "आगे के विषय की नींव रखता है।",
    },
    "revisit": {
        "en-IN": 'You scored {score}% on "{title}". Read it once more, then retake the '
        "quiz — the same terms come back.",
        "hi-IN": '"{title}" में आपको {score}% मिले। इसे एक बार फिर पढ़ें, फिर प्रश्नोत्तरी '
        "दोबारा दें — वही शब्द फिर आएँगे।",
    },
    "stretch": {
        "en-IN": 'You have passed everything so far. Go back to "{title}" and try to '
        "explain it to someone else — that is the real test.",
        "hi-IN": 'आपने अब तक सब कुछ पास कर लिया है। "{title}" पर लौटें और किसी और को '
        "समझाने की कोशिश करें — यही असली परीक्षा है।",
    },
}


def _reason_text(key: str, lang: str, **kwargs: Any) -> str:
    authored = REASONS[key]
    template = authored.get(lang)
    if template:
        return template.format(**kwargs)
    english = authored["en-IN"].format(**kwargs)
    if lang == "en-IN":
        return english
    return translator.translate(
        english, source="en-IN", target=lang, context=f"recommendation:{key}"
    )["text"]


def _progress_map(user_id: int | None) -> dict[str, dict[str, Any]]:
    if not user_id:
        return {}
    return {
        lesson["id"]: (db.lesson_progress(user_id, lesson["id"]) or {})
        for lesson in lessons.all_lessons()
    }


def rule_based(user_id: int | None, lang: str) -> dict[str, Any]:
    """Deterministic recommendation. Always returns a valid lesson id."""
    catalogue = lessons.all_lessons()
    if not catalogue:  # pragma: no cover - guards a broken checkout
        raise RuntimeError("no lessons available to recommend")

    progress = _progress_map(user_id)
    scored = {
        lesson_id: float(row["score"] or 0)
        for lesson_id, row in progress.items()
        if row.get("status") in {"completed", "quiz_passed"}
    }
    failed = [lid for lid, row in progress.items() if row.get("status") == "completed"]
    unread = [lesson["id"] for lesson in catalogue if not progress.get(lesson["id"])]

    if failed:
        target = min(failed, key=lambda lid: scored.get(lid, 0.0))
        lesson = lessons.get(target)
        return {
            "next_lesson_id": target,
            "difficulty": "easy",
            "reason": _reason_text(
                "revisit",
                lang,
                title=lessons.title(lesson, lang, user_id),
                score=round(scored.get(target, 0.0) * 100),
            ),
            "focus_terms": lessons.key_terms(lesson)[:3],
            "source": "rules",
        }

    if unread:
        target = unread[0]
        lesson = lessons.get(target)
        return {
            "next_lesson_id": target,
            "difficulty": "core",
            "reason": _reason_text("start", lang, title=lessons.title(lesson, lang, user_id)),
            "focus_terms": lessons.key_terms(lesson)[:3],
            "source": "rules",
        }

    weakest = min(scored, key=lambda lid: scored[lid]) if scored else catalogue[0]["id"]
    lesson = lessons.get(weakest)
    return {
        "next_lesson_id": weakest,
        "difficulty": "stretch",
        "reason": _reason_text("stretch", lang, title=lessons.title(lesson, lang, user_id)),
        "focus_terms": lessons.key_terms(lesson)[:3],
        "source": "rules",
    }


def _model_recommend(user_id: int | None, lang: str, fallback: dict[str, Any]) -> dict[str, Any]:
    """Ask the model to phrase a plan; keep the rules' answer if it misbehaves."""
    catalogue = lessons.all_lessons()
    ids = [lesson["id"] for lesson in catalogue]
    payload = {
        "lesson_ids": ids,
        "recent_lessons": list(_progress_map(user_id).keys()),
        "quiz_scores": {
            lid: round(float(row["score"] or 0) * 100)
            for lid, row in _progress_map(user_id).items()
            if row.get("score") is not None
        },
        "ui_language": lang,
        "rule_based_suggestion": fallback["next_lesson_id"],
    }
    reply = llm.chat(
        [
            {
                "role": "system",
                "content": prompts.personalise_system(
                    json.dumps(payload, ensure_ascii=False), lang
                ),
            },
            {"role": "user", "content": "Recommend the next lesson."},
        ],
        temperature=0.2,
        max_tokens=300,
    )
    if not reply.text:
        return fallback

    try:
        cleaned = reply.text.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
        parsed = json.loads(cleaned)
        next_id = parsed.get("next_lesson_id")
        if next_id not in ids:
            return fallback
        difficulty = parsed.get("difficulty")
        return {
            "next_lesson_id": next_id,
            "difficulty": difficulty if difficulty in {"easy", "core", "stretch"} else "core",
            "reason": str(parsed.get("reason") or fallback["reason"])[:400],
            "focus_terms": [str(term) for term in (parsed.get("focus_terms") or [])][:3]
            or fallback["focus_terms"],
            "source": "model",
        }
    except (json.JSONDecodeError, TypeError, ValueError):
        return fallback


def recommend(user_id: int | None, lang: str = "en-IN") -> dict[str, Any]:
    """The one entry point the Progress page calls."""
    fallback = rule_based(user_id, lang)
    result = fallback
    if not config.is_mock_mode():
        result = _model_recommend(user_id, lang, fallback)

    events.log_event(
        "recommendation_shown",
        user_id=user_id,
        lang=lang,
        next_lesson_id=result["next_lesson_id"],
        difficulty=result["difficulty"],
        source=result["source"],
    )
    return result
