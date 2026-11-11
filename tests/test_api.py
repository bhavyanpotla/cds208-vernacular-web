"""API tests: the HTTP contract the frontend depends on.

These run against the real app object with an in-memory-ish SQLite file, so a
breaking change to a response shape fails here rather than in the browser.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    from api.main import app

    with TestClient(app) as test_client:
        yield test_client


def test_health_reports_mock_mode_without_a_key(client, monkeypatch):
    monkeypatch.delenv("SARVAM_API_KEY", raising=False)
    payload = client.get("/api/health").json()
    assert payload["status"] == "ok"
    assert payload["lessons"] == 4
    assert payload["languages"] == 5


def test_languages_endpoint_lists_five_with_scripts(client):
    rows = client.get("/api/languages").json()
    assert len(rows) == 5
    assert all(row["native"] and row["script"] for row in rows)


def test_lessons_are_localised(client):
    rows = client.get("/api/lessons?lang=hi-IN").json()
    assert len(rows) == 4
    assert any("पौधे" in row["title"] for row in rows)


def test_lesson_detail_never_leaks_answer_indices(client):
    payload = client.get("/api/lessons/science-photosynthesis-01?lang=en-IN").json()
    assert len(payload["segments"]) == 3
    assert payload["quiz"]
    assert "answer_index" not in payload["quiz"][0]


def test_unknown_lesson_returns_404(client):
    assert client.get("/api/lessons/nope?lang=en-IN").status_code == 404


def test_gloss_returns_meaning_and_provenance(client):
    payload = client.post("/api/gloss", json={"term": "chlorophyll", "lang": "hi-IN"}).json()
    assert payload["authored"] == "yes"
    assert payload["meaning"]


def test_translate_is_mock_labelled_without_a_key(client, monkeypatch):
    monkeypatch.delenv("SARVAM_API_KEY", raising=False)
    payload = client.post(
        "/api/translate", json={"text": "plant water food", "source": "en-IN", "target": "hi-IN"}
    ).json()
    assert payload["provider"] in {"mock", "cache"}
    assert payload["text"]


def test_same_language_translation_is_a_noop(client):
    payload = client.post(
        "/api/translate", json={"text": "hello", "source": "en-IN", "target": "en-IN"}
    ).json()
    assert payload["provider"] == "noop"


def test_tutor_answers_grounded_and_refuses_ungrounded(client, monkeypatch):
    monkeypatch.delenv("SARVAM_API_KEY", raising=False)
    grounded = client.post(
        "/api/tutor",
        json={
            "lesson_id": "science-photosynthesis-01",
            "question": "What do plants need to make food?",
            "lang": "hi-IN",
        },
    ).json()
    assert grounded["grounded"] is True
    assert grounded["refused"] is False

    refused = client.post(
        "/api/tutor",
        json={
            "lesson_id": "science-photosynthesis-01",
            "question": "Who won the cricket world cup?",
            "lang": "hi-IN",
        },
    ).json()
    assert refused["refused"] is True
    assert refused["text"]


def test_quiz_scores_and_returns_explanations(client):
    payload = client.post(
        "/api/quiz",
        json={"lesson_id": "science-sound-04", "answers": [0, 0, 0], "lang": "en-IN"},
    ).json()
    assert payload["percent"] == 100
    assert payload["passed"] is True
    assert len(payload["explanations"]) == 3


def test_recommendation_always_names_a_real_lesson(client):
    payload = client.get("/api/recommend?lang=en-IN").json()
    assert payload["next_lesson_id"]
    assert payload["reason"]
    assert payload["title"]


def test_analytics_and_export_round_trip(client, tmp_path, monkeypatch):
    monkeypatch.setenv("VE_EXPORT_DIR", str(tmp_path / "exports"))
    analytics = client.get("/api/analytics").json()
    assert {"headline", "per_day", "by_language", "by_event", "struggle"} <= set(analytics)

    health = client.post("/api/export").json()
    assert health["rows"]["fact_events"] >= 0
    assert (tmp_path / "exports" / "fact_events.csv").exists()


def test_static_frontend_is_served(client):
    page = client.get("/")
    assert page.status_code == 200
    assert "Learn in the language you think in" in page.text


def test_bridge_endpoint_returns_a_tier(client):
    payload = client.post("/api/bridge", json={"text": "वे भी कमजोर पड़ रहे हैं"}).json()
    assert payload["tier"] in {"authored", "corpus", "approximate", "none"}
    assert 0.0 <= payload["confidence"] <= 1.0
    assert "label" in payload and "verified" in payload


def test_bridge_refuses_instead_of_inventing(client):
    payload = client.post("/api/bridge", json={"text": "मुझे क्रिकेट विश्व कप कब है"}).json()
    assert payload["tier"] == "none"
    assert payload["text"] == ""


def test_phrase_library_leads_with_classroom_targets(client):
    rows = client.get("/api/bridge/phrases?limit=10").json()
    assert rows, "phrase library must not be empty"
    assert rows[0]["id"].startswith("TGT-"), "targets must come before corpus-seeded rows"


def test_bridge_stats_reports_real_coverage(client):
    stats = client.get("/api/bridge/stats").json()
    assert "claim" in stats
    assert "verified" in stats["claim"]
