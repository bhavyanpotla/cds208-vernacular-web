"""Power BI export: four CSVs and a health file.

The report is not a separate script the user has to remember to run — it is a
projection of the same ``events`` and ``translations`` tables the app writes on
every click. Run it from the Analytics page button or from a script.

Power BI reads ``exports/`` as a folder source, so a refresh picks up all four
files at once. ``_health.json`` is the guard: if a table is stale or a column is
mostly null, the Analytics page says so instead of shipping a pretty lie.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from core import config, db, events, lessons

# props keys promoted to real columns so Power BI can slice on them
PROMOTED = (
    ("provider", "provider"),
    ("source", "source_lang"),
    ("target", "target_lang"),
    ("latency_ms", "latency_ms"),
    ("lesson_id", "lesson_id"),
    ("segment_id", "segment_id"),
    ("term", "term"),
    ("score", "score"),
    ("passed", "passed"),
    ("difficulty", "difficulty"),
    ("grounded", "grounded"),
    ("context", "context"),
)

FACT_FILES = ("fact_events.csv", "fact_translations.csv", "dim_lessons.csv", "dim_users.csv")


def _promote_props(events_df: pd.DataFrame) -> pd.DataFrame:
    """Turn the JSON ``props`` blob into typed columns, then drop the blob."""
    if events_df.empty:
        for _, column in PROMOTED:
            events_df[column] = pd.Series(dtype="object")
        return events_df.drop(columns=["props"], errors="ignore")

    props = events_df["props"].apply(
        lambda raw: json.loads(raw) if isinstance(raw, str) and raw else {}
    )
    for prop_key, column in PROMOTED:
        events_df[column] = props.apply(lambda item, key=prop_key: item.get(key))
    return events_df.drop(columns=["props"], errors="ignore")


def _read_all() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    with db.get_conn() as conn:
        events_df = pd.read_sql_query("SELECT * FROM events", conn)
        translations_df = pd.read_sql_query("SELECT * FROM translations", conn)
        users_df = pd.read_sql_query(
            "SELECT id, name, email, ui_language, created_at FROM users", conn
        )
    return events_df, translations_df, users_df


def _lesson_dimension() -> pd.DataFrame:
    rows = [
        {
            "id": lesson["id"],
            "subject": lesson.get("subject", "other"),
            "grade": lesson.get("grade"),
            "title_en": lesson.get("title", {}).get("en-IN", lesson["id"]),
            "segments": len(lesson.get("segments", [])),
            "questions": len(lesson.get("quiz", [])),
            "terms": len(lessons.key_terms(lesson)),
        }
        for lesson in lessons.all_lessons()
    ]
    return pd.DataFrame(rows)


def _with_time_columns(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or "created_at" not in frame:
        frame["date"] = pd.Series(dtype="object")
        frame["hour"] = pd.Series(dtype="object")
        return frame
    stamp = pd.to_datetime(frame["created_at"], errors="coerce")
    frame["date"] = stamp.dt.date.astype("string")
    frame["hour"] = stamp.dt.hour
    return frame


def run_export(out_dir: str | Path | None = None) -> dict[str, Any]:
    """Write the four CSVs plus ``_health.json``. Returns the health payload."""
    started = time.perf_counter()
    out = Path(out_dir) if out_dir else config.export_dir()
    out.mkdir(parents=True, exist_ok=True)

    events_df, translations_df, users_df = _read_all()

    fact_events = _with_time_columns(_promote_props(events_df.copy()))
    fact_translations = _with_time_columns(translations_df.copy())
    if not fact_translations.empty:
        fact_translations["chars"] = fact_translations["source_text"].str.len()
        fact_translations["source_text"] = fact_translations["source_text"].str.slice(0, 200)

    dim_lessons = _lesson_dimension()
    dim_users = users_df.copy()

    fact_events.to_csv(out / "fact_events.csv", index=False)
    fact_translations.to_csv(out / "fact_translations.csv", index=False)
    dim_lessons.to_csv(out / "dim_lessons.csv", index=False)
    dim_users.to_csv(out / "dim_users.csv", index=False)

    counts = events.event_counts()
    requested = counts.get("translation_requested", 0)
    served = counts.get("translation_served", 0)
    answered = requested + served

    null_rate = {
        column: round(float(fact_events[column].isna().mean()), 3)
        for column in ("provider", "target_lang", "lang", "lesson_id")
        if column in fact_events
    }

    health: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "duration_ms": int((time.perf_counter() - started) * 1000),
        "provider_mode": config.provider_mode(),
        "rows": {
            "fact_events": int(len(fact_events)),
            "fact_translations": int(len(fact_translations)),
            "dim_lessons": int(len(dim_lessons)),
            "dim_users": int(len(dim_users)),
        },
        "null_rate": null_rate,
        "event_types_fired": len(counts),
        "event_types_documented": len(events.EVENT_NAMES),
        "events_never_fired": sorted(events.EVENT_NAMES - set(counts)),
        "cache_hit_rate": round(served / answered, 3) if answered else 0.0,
        "warnings": [],
    }

    if health["rows"]["fact_events"] == 0:
        health["warnings"].append("fact_events is empty — click through the app first.")
    if health["cache_hit_rate"] == 0 and requested > 3:
        health["warnings"].append("no cache hits despite repeated translations.")
    stale = [
        name
        for name in FACT_FILES
        if not (out / name).exists() or (out / name).stat().st_size < 20
    ]
    if stale:
        health["warnings"].append(f"missing or tiny files: {', '.join(stale)}")

    (out / "_health.json").write_text(
        json.dumps(health, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    events.log_event(
        "export_refreshed",
        rows=health["rows"]["fact_events"],
        duration_ms=health["duration_ms"],
        warnings=len(health["warnings"]),
    )
    return health


def read_health(out_dir: str | Path | None = None) -> dict[str, Any] | None:
    path = (Path(out_dir) if out_dir else config.export_dir()) / "_health.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ live charts
# Small queries so the in-app page tells the same story as the .pbix without
# needing the export to have run first.


def events_per_day() -> pd.DataFrame:
    with db.get_conn() as conn:
        return pd.read_sql_query(
            "SELECT date(created_at) AS day, COUNT(*) AS events FROM events"
            " GROUP BY day ORDER BY day",
            conn,
        )


def events_by_language() -> pd.DataFrame:
    with db.get_conn() as conn:
        return pd.read_sql_query(
            "SELECT COALESCE(lang, 'unknown') AS language, COUNT(*) AS events FROM events"
            " GROUP BY language ORDER BY events DESC",
            conn,
        )


def events_by_name() -> pd.DataFrame:
    with db.get_conn() as conn:
        return pd.read_sql_query(
            "SELECT event_name, COUNT(*) AS events FROM events"
            " GROUP BY event_name ORDER BY events DESC",
            conn,
        )


def terms_most_translated(limit: int = 10) -> pd.DataFrame:
    """The struggle list: which terms students keep tapping."""
    with db.get_conn() as conn:
        return pd.read_sql_query(
            "SELECT json_extract(props, '$.term') AS term, COUNT(*) AS taps FROM events"
            " WHERE event_name = 'term_glossed' AND term IS NOT NULL"
            " GROUP BY term ORDER BY taps DESC LIMIT ?",
            conn,
            params=(limit,),
        )


def headline_numbers() -> dict[str, Any]:
    counts = events.event_counts()
    requested = counts.get("translation_requested", 0)
    served = counts.get("translation_served", 0)
    with db.get_conn() as conn:
        sessions = conn.execute(
            "SELECT COUNT(DISTINCT session_id) AS n FROM events WHERE session_id IS NOT NULL"
        ).fetchone()["n"]
        learners = conn.execute(
            "SELECT COUNT(DISTINCT user_id) AS n FROM events WHERE user_id IS NOT NULL"
        ).fetchone()["n"]
        latency = conn.execute(
            "SELECT AVG(latency_ms) AS v FROM translations WHERE latency_ms IS NOT NULL"
        ).fetchone()["v"]
    answered = requested + served
    return {
        "events": sum(counts.values()),
        "sessions": int(sessions or 0),
        "learners": int(learners or 0),
        "translations": requested,
        "cache_hit_rate": round(served / answered, 3) if answered else 0.0,
        "avg_latency_ms": int(latency or 0),
        "tutor_turns": counts.get("tutor_question_asked", 0),
        "refusals": counts.get("tutor_refused_ungrounded", 0),
        "quizzes": counts.get("quiz_submitted", 0),
    }
