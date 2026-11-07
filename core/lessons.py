"""Lesson content: load, localise, segment.

Lessons are data, not code — one JSON per lesson in ``content/lessons``, with
the segments authored in English and Hindi. Any language that is not authored
inline is filled by the translation service on first read and cached in
SQLite, which is exactly the pipeline the whole product is about: a content
gap that closes itself instead of a dropdown that changes nothing.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from core import config
from core import translate as translator

LESSON_DIR = config.CONTENT_DIR / "lessons"
GLOSSARY_PATH = config.CONTENT_DIR / "glossary.json"
SOURCE_LANG = "en-IN"


def reload() -> None:
    """Drop the in-process cache — used by tests and the content sync script."""
    _load_all.cache_clear()
    _glossary.cache_clear()


@lru_cache(maxsize=1)
def _load_all() -> tuple[dict[str, Any], ...]:
    lessons: list[dict[str, Any]] = []
    if not LESSON_DIR.exists():  # pragma: no cover - guards a broken checkout
        return tuple()
    for path in sorted(LESSON_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:  # pragma: no cover
            print(f"[lessons] skipping {path.name}: {exc}")
            continue
        if "id" not in data:
            data["id"] = path.stem
        lessons.append(data)
    return tuple(lessons)


def all_lessons() -> list[dict[str, Any]]:
    return list(_load_all())


def get(lesson_id: str) -> dict[str, Any] | None:
    return next((lesson for lesson in _load_all() if lesson["id"] == lesson_id), None)


def lesson_ids() -> list[str]:
    return [lesson["id"] for lesson in _load_all()]


def by_subject() -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for lesson in _load_all():
        grouped.setdefault(lesson.get("subject", "other"), []).append(lesson)
    return grouped


def segment(lesson: dict[str, Any], segment_id: str) -> dict[str, Any] | None:
    return next(
        (item for item in lesson.get("segments", []) if item["id"] == segment_id), None
    )


def key_terms(lesson: dict[str, Any]) -> list[str]:
    """Every distinct term in the lesson, in first-appearance order."""
    seen: list[str] = []
    for item in lesson.get("segments", []):
        for term in item.get("key_terms", []):
            if term not in seen:
                seen.append(term)
    return seen


# ------------------------------------------------------------------ localising


def localise(
    mapping: dict[str, str],
    lang: str,
    context: str,
    *,
    user_id: int | None = None,
) -> str:
    """Return ``mapping[lang]``, or translate it from the source language.

    Authored content always wins; the service is only called for a gap, and it
    caches the result in the ``translations`` table, so the second reader of
    the same lesson pays nothing.
    """
    if not mapping:
        return ""
    if mapping.get(lang):
        return mapping[lang]
    base = mapping.get(SOURCE_LANG) or next(iter(mapping.values()))
    result = translator.translate(
        base, source=SOURCE_LANG, target=lang, user_id=user_id, context=context
    )
    return result["text"]


def title(lesson: dict[str, Any], lang: str, user_id: int | None = None) -> str:
    return localise(
        lesson.get("title", {}), lang, f"lesson_title:{lesson['id']}", user_id=user_id
    )


def summary(lesson: dict[str, Any], lang: str, user_id: int | None = None) -> str:
    return localise(
        lesson.get("summary", {}), lang, f"lesson_summary:{lesson['id']}", user_id=user_id
    )


def segment_text(
    lesson: dict[str, Any],
    item: dict[str, Any],
    lang: str,
    user_id: int | None = None,
) -> str:
    return localise(
        item.get("text", {}),
        lang,
        f"segment:{lesson['id']}:{item['id']}",
        user_id=user_id,
    )


def quiz_question(
    lesson: dict[str, Any],
    index: int,
    lang: str,
    user_id: int | None = None,
) -> dict[str, Any]:
    """One quiz question with its text, options and explanation localised."""
    raw = lesson["quiz"][index]
    ctx = f"quiz:{lesson['id']}:{index}"
    return {
        "index": index,
        "q": localise(raw["q"], lang, f"{ctx}:q", user_id=user_id),
        "options": [
            localise({"en-IN": option}, lang, f"{ctx}:o{i}", user_id=user_id)
            if isinstance(option, str)
            else option
            for i, option in enumerate(raw["options"][SOURCE_LANG])
        ],
        "answer_index": int(raw["answer_index"]),
        "explain": localise(
            raw.get("explain", {}), lang, f"{ctx}:e", user_id=user_id
        )
        if raw.get("explain")
        else "",
    }


# ------------------------------------------------------------------- glossary


@lru_cache(maxsize=1)
def _glossary() -> dict[str, dict[str, str]]:
    if not GLOSSARY_PATH.exists():  # pragma: no cover
        return {}
    return json.loads(GLOSSARY_PATH.read_text(encoding="utf-8"))


def glossary_terms() -> list[str]:
    return sorted(_glossary())


def glossary_entry(
    term: str, lang: str, user_id: int | None = None
) -> dict[str, str] | None:
    """The explanation for ``term`` in ``lang``, translated if not authored."""
    entry = _glossary().get(term)
    if not entry:
        return None
    return {
        "term": term,
        "meaning": localise(entry, lang, f"glossary:{term}", user_id=user_id),
        "authored": "yes" if entry.get(lang) else "translated",
    }
