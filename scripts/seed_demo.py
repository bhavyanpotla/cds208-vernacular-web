"""Seed a demo dataset so a fresh deployment has something to show.

Streamlit Community Cloud gives the app an ephemeral filesystem, so the SQLite
file is recreated empty on every restart. Run this once after a deploy (or from
the app's own analytics page) to fill the dashboard with a plausible week of
activity instead of an empty report.

Usage:
    python scripts/seed_demo.py            # ~120 events across 3 languages
    python scripts/seed_demo.py --reset    # wipe the database first
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import db, events, lessons, quiz  # noqa: E402
from core import translate as translator  # noqa: E402

LANGS = ["hi-IN", "te-IN", "ta-IN", "bn-IN"]
QUESTIONS = [
    ("What do plants need to make food?", True),
    ("How is sound made?", True),
    ("What does the denominator tell you?", True),
    ("Who won the cricket world cup?", False),
    ("What is the capital of France?", False),
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo events for the dashboard.")
    parser.add_argument("--reset", action="store_true", help="delete the database first")
    parser.add_argument("--sessions", type=int, default=6, help="simulated sessions")
    args = parser.parse_args()

    if args.reset:
        db.reset_db()
    db.init_db()

    random.seed(7)
    user_id = db.ensure_local_user()
    catalogue = lessons.all_lessons()
    written = 0

    for session in range(args.sessions):
        lang = random.choice(LANGS)
        session_id = f"seed-{session:02d}"
        events.log_event("app_opened", user_id=user_id, lang=lang, session_id=session_id, provider="mock")
        written += 1

        for lesson in random.sample(catalogue, k=2):
            events.log_event(
                "lesson_opened",
                user_id=user_id,
                lang=lang,
                session_id=session_id,
                lesson_id=lesson["id"],
                subject=lesson["subject"],
                grade=lesson["grade"],
                read_lang=lang,
            )
            written += 1

            for term in lessons.key_terms(lesson)[:2]:
                events.log_event(
                    "term_glossed",
                    user_id=user_id,
                    lang=lang,
                    session_id=session_id,
                    lesson_id=lesson["id"],
                    term=term,
                    authored="translated",
                )
                written += 1

            translator.translate(
                lessons.segment_text(lesson, lesson["segments"][0], "en-IN"),
                source="en-IN",
                target=lang,
                user_id=user_id,
                context=f"seed:{lesson['id']}",
            )
            written += 1

            answers = [question["answer_index"] for question in lesson["quiz"]]
            if random.random() < 0.35:
                answers[0] = (answers[0] + 1) % len(lesson["quiz"][0]["options"])
            result = quiz.score(answers, quiz.answer_key(lesson))
            quiz.record_attempt(lesson, result, user_id=user_id, lang=lang)
            written += 2

        for _question, _ in random.sample(QUESTIONS, k=2):
            lesson = random.choice(catalogue)
            events.log_event(
                "tutor_question_asked",
                user_id=user_id,
                lang=lang,
                session_id=session_id,
                lesson_id=lesson["id"],
                provider="mock",
                grounded=True,
            )
            written += 1

    health_rows = db.progress_summary(user_id)
    print(f"seeded {written} events for user {user_id}")
    print(f"progress: {health_rows}")
    print(f"event counts: {events.event_counts()}")


if __name__ == "__main__":
    main()
