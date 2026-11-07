"""The tutor agent: grounded answers, and an honest refusal when it cannot.

Two paths, one contract:

* **live** — Sarvam chat with a system prompt that carries the lesson segment
  and forbids invention.
* **offline** — a deterministic answer built from the lesson itself, used when
  there is no key and as the fallback when a provider call fails.

Both return ``{text, provider, grounded, refused, degraded}``. ``grounded`` is
computed here by lexical overlap with the lesson, not guessed from the model's
wording, so the flag in the UI and the event in the log mean the same thing in
mock mode and in production.
"""

from __future__ import annotations

import re
from typing import Any

from agents import phrases, prompts
from core import config, events, lessons, llm

MIN_QUESTION_CHARS = 3

_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "what", "why", "how", "when",
    "where", "who", "which", "does", "do", "did", "can", "could", "would",
    "should", "of", "in", "on", "at", "to", "for", "and", "or", "but", "it",
    "this", "that", "these", "those", "with", "from", "by", "as", "me", "my",
    "you", "your", "we", "our", "they", "them", "there", "here", "be", "been",
    "have", "has", "had", "will", "not", "no", "yes", "if", "then", "than",
    "so", "about", "into", "more", "most", "some", "any", "all", "just",
    "explain", "simpler", "example", "give", "tell", "please", "mean", "means",
}

_TOKEN = re.compile(r"[A-Za-z\u0900-\u0DFF]{3,}|\d+")


def _content_words(text: str) -> set[str]:
    """Lower-cased content words, crudely stemmed, with digits kept."""
    words = _TOKEN.findall((text or "").lower())
    return {word.rstrip("s") for word in words if word not in _STOPWORDS}


def is_grounded(question: str, lesson_text: str) -> bool:
    """True when the question shares vocabulary with the lesson.

    Deliberately conservative: a question with no overlap at all is treated as
    outside the lesson, and the tutor refuses rather than improvising. It is a
    lexical check, not a semantic one — which is why the live prompt still
    carries the anti-invention rule.
    """
    asked = _content_words(question)
    if not asked:
        return False
    body = _content_words(lesson_text)
    return any(word in body for word in asked)


def _lesson_body(lesson: dict[str, Any]) -> str:
    parts = [lessons.title(lesson, "en-IN")]
    parts += [item["text"].get("en-IN", "") for item in lesson.get("segments", [])]
    return " ".join(part for part in parts if part)


def _best_segment(lesson: dict[str, Any], question: str) -> dict[str, Any]:
    """The segment with the most overlap with the question; the first if none."""
    asked = _content_words(question)
    best, best_score = lesson["segments"][0], -1
    for item in lesson["segments"]:
        score = len(asked & _content_words(item["text"].get("en-IN", "")))
        if score > best_score:
            best, best_score = item, score
    return best


def offline_answer(
    lesson: dict[str, Any],
    question: str,
    lang: str,
    grounded: bool,
    user_id: int | None = None,
) -> str:
    """Deterministic, lesson-derived answer. No model, no invention."""
    followup = phrases.p("followup", lang)
    if grounded:
        target = _best_segment(lesson, question)
        body = lessons.segment_text(lesson, target, lang, user_id)
        return f'{phrases.p("from_lesson", lang)} {body}\n\n{followup}'

    hint_term = lessons.key_terms(lesson)[0] if lessons.key_terms(lesson) else lesson["id"]
    hint = f'{phrases.p("hint", lang)} "{hint_term}".'
    return f'{phrases.p("refusal", lang)}\n\n{hint}\n\n{followup}'


def answer(
    question: str,
    lesson: dict[str, Any],
    segment: dict[str, Any] | None = None,
    lang: str = "en-IN",
    history: list[dict[str, str]] | None = None,
    user_id: int | None = None,
) -> dict[str, Any]:
    """Answer one student question about one lesson. Never raises."""
    clean = (question or "").strip()
    if len(clean) < MIN_QUESTION_CHARS:
        return {
            "text": phrases.p("ask_title", lang),
            "provider": "noop",
            "grounded": False,
            "refused": False,
            "degraded": False,
        }

    body = _lesson_body(lesson)
    grounded = is_grounded(clean, body)
    target_segment = segment or _best_segment(lesson, clean)

    result: dict[str, Any]
    if config.is_mock_mode():
        result = {
            "text": offline_answer(lesson, clean, lang, grounded, user_id),
            "provider": "mock",
            "grounded": grounded,
            "refused": not grounded,
            "degraded": False,
        }
    else:
        system = prompts.tutor_system(
            grade=lesson.get("grade", 7),
            subject=lesson.get("subject", "science"),
            language=lang,
            lesson_title=lessons.title(lesson, lang, user_id),
            segment_text=lessons.segment_text(lesson, target_segment, lang, user_id),
            lesson_context=" ".join(
                lessons.segment_text(lesson, item, lang, user_id)
                for item in lesson.get("segments", [])
                if item["id"] != target_segment["id"]
            ),
        )
        messages = [{"role": "system", "content": system}]
        messages += (history or [])[-6:]
        messages.append({"role": "user", "content": clean})

        reply = llm.chat(messages)
        if reply.text:
            result = {
                "text": reply.text,
                "provider": reply.provider,
                "grounded": grounded,
                "refused": not grounded,
                "degraded": False,
            }
        else:
            result = {
                "text": offline_answer(lesson, clean, lang, grounded, user_id),
                "provider": "mock",
                "grounded": grounded,
                "refused": not grounded,
                "degraded": True,
            }

    events.log_event(
        "tutor_question_asked",
        user_id=user_id,
        lang=lang,
        lesson_id=lesson["id"],
        segment_id=target_segment["id"],
        chars=len(clean),
        provider=result["provider"],
        grounded=result["grounded"],
        degraded=result["degraded"],
    )
    if result["refused"]:
        events.log_event(
            "tutor_refused_ungrounded",
            user_id=user_id,
            lang=lang,
            lesson_id=lesson["id"],
            question=clean[:160],
        )
    return result
