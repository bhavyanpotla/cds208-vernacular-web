"""Tiered bridge tests: the tier is the product, so the tier is what we assert."""

from __future__ import annotations

import pytest

from core import bridge

AUTHORED = (
    "id\thindi\tenglish\tmundari\tsource\tverified_by\tconfidence\tnotes\n"
    "CLS-001\tआज हम गिनती सीखेंगे\ttoday we will learn counting\tआज हम गिनती सीखेंगे (mun)\t"
    "hand\tSP\texact\tsigned off by a Mundari speaker\n"
    "CLS-002\tअपनी किताब खोलो\topen your book\tअपनी किताब खोलो (mun)\t"
    "hand\t\t draft\tdraft row\n"
)

CORPUS = (
    "id\thindi\ttarget\tscript\tsource\tlicense\tverified_by\tconfidence\tnotes\n"
    "MUN-00001\tवे भी कमजोर पड़ रहे हैं\tइनकु कमजोरोःतानाको\tdevanagari\tcorpus\tUNVERIFIED\t\texact\t\n"
    "MUN-00002\tउन्होंने शादी करने का भी वादा किया था\tइनिः आड़ानदि रिका राः किरिआओ जोमला\tdevanagari\tcorpus\tUNVERIFIED\t\texact\t\n"
)


@pytest.fixture()
def store(tmp_path, monkeypatch):
    authored = tmp_path / "classroom_phrases.tsv"
    corpus = tmp_path / "mundari_pairs.tsv"
    authored.write_text(AUTHORED, encoding="utf-8")
    corpus.write_text(CORPUS, encoding="utf-8")
    monkeypatch.setattr(bridge, "AUTHORED_PATH", authored)
    monkeypatch.setattr(bridge, "CORPUS_PATH", corpus)
    bridge.reload()
    yield
    bridge.reload()


def test_normalise_strips_punctuation_and_digits():
    assert bridge.normalise("  आज  हम, गिनती सीखेंगे। ") == "आज हम गिनती सीखेंगे"
    assert bridge.normalise("पाठ ३") == "पाठ 3"


def test_authored_phrase_wins_and_reports_verification(store):
    match = bridge.lookup("आज हम गिनती सीखेंगे")
    assert match.tier == "authored"
    assert match.verified is True
    assert match.confidence == pytest.approx(0.98)
    assert "verified" in match.label


def test_unverified_authored_row_is_labelled_draft(store):
    match = bridge.lookup("अपनी किताब खोलो")
    assert match.tier == "authored"
    assert match.verified is False
    assert match.confidence == pytest.approx(0.60)
    assert "draft" in match.label
    assert "not yet checked" in match.note


def test_authored_match_survives_punctuation_and_spacing(store):
    assert bridge.lookup("  आज हम गिनती सीखेंगे।  ").tier == "authored"


def test_exact_corpus_match_is_tier_two(store):
    match = bridge.lookup("वे भी कमजोर पड़ रहे हैं")
    assert match.tier == "corpus"
    assert match.text == "इनकु कमजोरोःतानाको"
    assert match.verified is False
    assert match.confidence == pytest.approx(0.85)


def test_partial_overlap_is_labelled_approximate(store):
    match = bridge.lookup("वे भी कमजोर पड़ रहे थे")
    assert match.tier == "approximate"
    assert "approximate" in match.label
    assert match.confidence < 0.85


def test_unrelated_text_refuses_instead_of_inventing(store):
    match = bridge.lookup("मुझे क्रिकेट विश्व कप कब है")
    assert match.tier == "none"
    assert match.text == ""
    assert match.confidence == 0.0
    assert "no authored phrase" in match.note


def test_empty_input_is_handled(store):
    match = bridge.lookup("   ")
    assert match.tier == "none"
    assert "empty" in match.label


def test_coverage_reports_real_counts(store):
    info = bridge.coverage()
    assert info["authored_rows"] == 2
    assert info["authored_verified"] == 1
    assert info["authored_verified_pct"] == 50.0
    assert info["corpus_rows"] == 2
    assert "1 verified classroom phrases" in info["claim"]


def test_missing_corpus_degrades_to_authored_only(tmp_path, monkeypatch):
    authored = tmp_path / "classroom_phrases.tsv"
    authored.write_text(AUTHORED, encoding="utf-8")
    monkeypatch.setattr(bridge, "AUTHORED_PATH", authored)
    monkeypatch.setattr(bridge, "CORPUS_PATH", tmp_path / "absent.tsv")
    bridge.reload()
    assert bridge.lookup("वे भी कमजोर पड़ रहे हैं").tier == "none"
    assert bridge.lookup("आज हम गिनती सीखेंगे").tier == "authored"
    assert bridge.available()["corpus_present"] is False
    bridge.reload()
