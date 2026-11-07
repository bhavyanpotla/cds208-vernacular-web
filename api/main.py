"""FastAPI over the existing services — the API the HTML frontend talks to.

Nothing in ``core`` or ``agents`` changed shape to be served here: the routes
call the same functions the Streamlit pages called. That is the payoff for
keeping Streamlit imports out of the service layer.

Run:
    uvicorn api.main:app --reload --port 8000
Then open http://127.0.0.1:8000/
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agents import coach, phrases
from agents import tutor as tutor_agent
from api import context
from core import config, db, events, export, lessons, quiz
from core import translate as translator
from core.i18n import UI_STRINGS, t

app = FastAPI(title="Vernacular Learning Platform", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

events.set_session_resolver(context.resolve)
db.init_db()


def learner_id() -> int:
    """Resolved per request, not at import: the test suite swaps the DB per test."""
    resolved = context.USER.get()
    return resolved if resolved is not None else db.ensure_local_user()


@app.middleware("http")
async def bind_session(request: Request, call_next):
    """Every request carries a browser session id; fall back to a process one."""
    sid = request.headers.get("x-session-id") or f"srv-{uuid.uuid4().hex[:8]}"
    context.SESSION.set(sid)
    context.USER.set(db.ensure_local_user())
    response = await call_next(request)
    response.headers["x-session-id"] = sid
    return response


# --------------------------------------------------------------------- models


class TranslateIn(BaseModel):
    text: str = Field(min_length=0, max_length=2000)
    source: str = "en-IN"
    target: str = "hi-IN"


class GlossIn(BaseModel):
    term: str
    lang: str = "en-IN"


class TutorIn(BaseModel):
    lesson_id: str
    segment_id: str | None = None
    question: str = Field(min_length=1, max_length=1000)
    lang: str = "en-IN"
    history: list[dict[str, str]] = Field(default_factory=list)


class QuizIn(BaseModel):
    lesson_id: str
    answers: list[int | None] = Field(default_factory=list)
    lang: str = "en-IN"


# --------------------------------------------------------------------- basics


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "mode": config.provider_mode(),
        "languages": len(config.LANG_CODES),
        "lessons": len(lessons.all_lessons()),
        "glossary_terms": len(lessons.glossary_terms()),
        "events": sum(events.event_counts().values()),
    }


@app.get("/api/languages")
def languages() -> list[dict[str, str]]:
    return [{"code": code, **config.LANGUAGES[code]} for code in config.LANG_CODES]


@app.get("/api/ui-strings")
def ui_strings(lang: str = config.DEFAULT_LANG) -> dict[str, str]:
    return {key: t(key, lang) for key in UI_STRINGS}


@app.get("/api/phrases")
def tutor_phrases(lang: str = config.DEFAULT_LANG) -> dict[str, str]:
    return {
        key: phrases.p(key, lang)
        for key in ("ask_title", "simpler", "example", "context", "grounded", "outside", "mock_note")
    }


# -------------------------------------------------------------------- lessons


@app.get("/api/lessons")
def lesson_list(lang: str = config.DEFAULT_LANG) -> list[dict[str, Any]]:
    return [
        {
            "id": lesson["id"],
            "subject": lesson.get("subject"),
            "grade": lesson.get("grade"),
            "title": lessons.title(lesson, lang),
            "summary": lessons.summary(lesson, lang),
            "segments": len(lesson["segments"]),
            "questions": len(lesson["quiz"]),
        }
        for lesson in lessons.all_lessons()
    ]


@app.get("/api/lessons/{lesson_id}")
def lesson_detail(lesson_id: str, lang: str = config.DEFAULT_LANG) -> JSONResponse:
    lesson = lessons.get(lesson_id)
    if lesson is None:
        return JSONResponse({"error": "lesson not found"}, status_code=404)

    events.log_event(
        "lesson_opened",
        lesson_id=lesson_id,
        subject=lesson.get("subject"),
        grade=lesson.get("grade"),
        read_lang=lang,
    )
    return JSONResponse(
        {
            "id": lesson["id"],
            "subject": lesson.get("subject"),
            "grade": lesson.get("grade"),
            "title": lessons.title(lesson, lang),
            "summary": lessons.summary(lesson, lang),
            "segments": [
                {
                    "id": item["id"],
                    "text": lessons.segment_text(lesson, item, lang),
                    "terms": item.get("key_terms", []),
                }
                for item in lesson["segments"]
            ],
            # answers are deliberately not sent — they come back after submitting
            "quiz": [
                {
                    "index": index,
                    "q": lessons.quiz_question(lesson, index, lang)["q"],
                    "options": lessons.quiz_question(lesson, index, lang)["options"],
                }
                for index in range(len(lesson["quiz"]))
            ],
            "progress": db.lesson_progress(learner_id(), lesson_id),
        }
    )


@app.post("/api/gloss")
def gloss(payload: GlossIn) -> dict[str, Any]:
    entry = lessons.glossary_entry(payload.term, payload.lang)
    if entry is None:
        return {"term": payload.term, "meaning": None, "authored": "missing"}
    events.log_event(
        "term_glossed", term=payload.term, read_lang=payload.lang, authored=entry["authored"]
    )
    return entry


@app.post("/api/quiz")
def submit_quiz(payload: QuizIn) -> dict[str, Any]:
    lesson = lessons.get(payload.lesson_id)
    if lesson is None:
        return {"error": "lesson not found"}
    result = quiz.score(payload.answers, quiz.answer_key(lesson))
    quiz.record_attempt(lesson, result, user_id=learner_id(), lang=payload.lang)
    return {
        **result,
        "explanations": [
            {
                "index": index,
                "explain": lessons.quiz_question(lesson, index, payload.lang)["explain"],
                "answer": lessons.quiz_question(lesson, index, payload.lang)["options"][
                    lesson["quiz"][index]["answer_index"]
                ],
            }
            for index in range(len(lesson["quiz"]))
        ],
    }


# ------------------------------------------------------------------ translate


@app.post("/api/translate")
def translate(payload: TranslateIn) -> dict[str, Any]:
    return translator.translate(
        payload.text,
        source=payload.source,
        target=payload.target,
        user_id=learner_id(),
        context="web_translate",
    )


@app.get("/api/translate/recent")
def recent_translations(limit: int = 8) -> list[dict[str, Any]]:
    return db.recent_translations(limit=limit)


@app.get("/api/translate/stats")
def translation_stats() -> dict[str, Any]:
    return db.translation_stats()


# ---------------------------------------------------------------------- tutor


@app.post("/api/tutor")
def ask_tutor(payload: TutorIn) -> dict[str, Any]:
    lesson = lessons.get(payload.lesson_id)
    if lesson is None:
        return {"error": "lesson not found"}
    segment = lessons.segment(lesson, payload.segment_id) if payload.segment_id else None
    return tutor_agent.answer(
        payload.question,
        lesson=lesson,
        segment=segment,
        lang=payload.lang,
        history=payload.history[-6:],
        user_id=learner_id(),
    )


# ------------------------------------------------------------- progress/coach


@app.get("/api/progress")
def progress(lang: str = config.DEFAULT_LANG) -> dict[str, Any]:
    summary = db.progress_summary(learner_id())
    rows = []
    for lesson in lessons.all_lessons():
        row = db.lesson_progress(learner_id(), lesson["id"]) or {}
        rows.append(
            {
                "id": lesson["id"],
                "title": lessons.title(lesson, lang),
                "subject": lesson.get("subject"),
                "grade": lesson.get("grade"),
                "status": row.get("status") or "not started",
                "score": round(float(row.get("score") or 0) * 100)
                if row.get("score") is not None
                else None,
            }
        )
    return {"summary": summary, "lessons": rows}


@app.get("/api/recommend")
def recommend(lang: str = config.DEFAULT_LANG) -> dict[str, Any]:
    result = coach.recommend(learner_id(), lang)
    lesson = lessons.get(result["next_lesson_id"])
    result["title"] = lessons.title(lesson, lang) if lesson else result["next_lesson_id"]
    return result


# ------------------------------------------------------------------ analytics


@app.get("/api/analytics")
def analytics() -> dict[str, Any]:
    headline = export.headline_numbers()
    return {
        "headline": headline,
        "per_day": export.events_per_day().to_dict(orient="records"),
        "by_language": export.events_by_language().to_dict(orient="records"),
        "by_event": export.events_by_name().head(10).to_dict(orient="records"),
        "struggle": export.terms_most_translated().to_dict(orient="records"),
        "health": export.read_health(),
    }


@app.post("/api/export")
def run_export() -> dict[str, Any]:
    return export.run_export()


# ------------------------------------------------------------- static frontend

app.mount("/", StaticFiles(directory=str(config.WEB_DIR), html=True), name="web")
