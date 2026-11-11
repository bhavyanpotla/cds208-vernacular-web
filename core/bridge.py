"""Tiered Hindi → Mundari bridge with a confidence label that means something.

The corpus is 17,729 general-domain sentence pairs. Only about 6% of it touches
classroom vocabulary, so matching a teacher's "today we will learn counting"
against it directly produces syntactically parallel, pedagogically useless
output. This module therefore answers in tiers and says which tier answered:

    tier 1  authored      a hand-written classroom phrase, ideally verified
    tier 2  corpus        an exact match in the parallel corpus
    tier 3  approximate   best partial overlap in the corpus, clearly labelled
    tier 4  none          no match — say so instead of inventing one

The tier is the product. A number like "98% confidence" invented by a model is
worthless; "matched tier 1, verified by a Mundari speaker" is checkable.

Data files (both optional, both degrade cleanly):

    data/classroom_phrases.tsv   id hindi english mundari source verified_by confidence notes
    data/mundari_pairs.tsv       id hindi target script source license verified_by confidence notes

Nothing here imports a web framework or a model. It is a lookup with a spine.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from core import config

DATA_DIR = config.BASE_DIR / "data"
AUTHORED_PATH = DATA_DIR / "classroom_phrases.tsv"
CORPUS_PATH = DATA_DIR / "mundari_pairs.tsv"

AUTHORED_HEADER = [
    "id", "hindi", "english", "mundari", "source", "verified_by", "confidence", "notes",
]
CORPUS_HEADER = [
    "id", "hindi", "target", "script", "source", "license", "verified_by", "confidence", "notes",
]

CONFIDENCE = {
    "authored_verified": 0.98,
    "authored_draft": 0.60,
    "corpus": 0.85,
    "approximate": 0.40,
    "none": 0.0,
}

APPROXIMATE_FLOOR = 0.60   # Jaccard overlap required before we call it a match

_PUNCT = re.compile(r"[।॥,;:!?\"'“”‘’()\[\]{}<>«»…·•–—-]")
_SPACE = re.compile(r"\s+")
_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


def normalise(text: str) -> str:
    """Comparable form: NFC, no punctuation, no digit variance, single spaces."""
    text = unicodedata.normalize("NFC", text or "")
    text = text.translate(_DEVANAGARI_DIGITS)
    text = _PUNCT.sub(" ", text)
    text = _SPACE.sub(" ", text).strip()
    return text


def tokens(text: str) -> set[str]:
    return {token for token in normalise(text).split(" ") if token}


@dataclass(frozen=True)
class Match:
    """One answer, with everything the interface needs to be honest about it."""

    text: str
    tier: str                 # authored | corpus | approximate | none
    confidence: float
    label: str                # human-readable, shown next to the result
    matched_hindi: str = ""
    matched_id: str = ""
    source: str = ""
    verified: bool = False
    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "tier": self.tier,
            "confidence": round(self.confidence, 2),
            "label": self.label,
            "matched_hindi": self.matched_hindi,
            "matched_id": self.matched_id,
            "source": self.source,
            "verified": self.verified,
            "note": self.note,
        }


@dataclass
class Store:
    authored: dict[str, dict[str, str]] = field(default_factory=dict)
    corpus: dict[str, dict[str, str]] = field(default_factory=dict)
    index: dict[str, set[str]] = field(default_factory=dict)
    token_sets: dict[str, set[str]] = field(default_factory=dict)
    authored_rows: int = 0
    authored_verified: int = 0
    corpus_rows: int = 0


def _read_tsv(path: Path, header: list[str]) -> list[dict[str, str]]:
    if not path.exists():
        return []
    rows: list[dict[str, str]] = []
    lines = path.read_text(encoding="utf-8").split("\n")
    if not lines or lines[0].split("\t") != header:
        return []
    for line in lines[1:]:
        if not line.strip():
            continue
        fields = line.split("\t")
        if len(fields) != len(header):
            continue
        rows.append(dict(zip(header, fields, strict=True)))
    return rows


@lru_cache(maxsize=1)
def _store() -> Store:
    store = Store()

    for row in _read_tsv(AUTHORED_PATH, AUTHORED_HEADER):
        key = normalise(row["hindi"])
        if not key or not row["mundari"].strip():
            continue
        store.authored_rows += 1
        if row["verified_by"].strip():
            store.authored_verified += 1
        store.authored[key] = row

    for row in _read_tsv(CORPUS_PATH, CORPUS_HEADER):
        key = normalise(row["hindi"])
        if not key or not row["target"].strip():
            continue
        store.corpus_rows += 1
        store.corpus.setdefault(key, row)          # first wins; corpus is deduped
        token_set = tokens(row["hindi"])
        store.token_sets[key] = token_set          # computed once, not per query
        for token in token_set:
            store.index.setdefault(token, set()).add(key)

    return store


def reload() -> None:
    """Drop the caches — after a reviewer edits the phrase sheet."""
    _store.cache_clear()


def available() -> dict[str, Any]:
    store = _store()
    return {
        "authored_rows": store.authored_rows,
        "authored_verified": store.authored_verified,
        "corpus_rows": store.corpus_rows,
        "corpus_present": CORPUS_PATH.exists(),
        "authored_present": AUTHORED_PATH.exists(),
    }


def lookup(text: str, *, allow_approximate: bool = True) -> Match:
    """Translate one Hindi utterance into Mundari, in tiers. Never invents."""
    store = _store()
    clean = (text or "").strip()
    key = normalise(clean)

    if not key:
        return Match("", "none", 0.0, "empty input", note="nothing to translate")

    # tier 1 — authored classroom phrase
    authored = store.authored.get(key)
    if authored:
        verified = bool(authored["verified_by"].strip())
        return Match(
            text=authored["mundari"],
            tier="authored",
            confidence=CONFIDENCE["authored_verified"] if verified else CONFIDENCE["authored_draft"],
            label="authored" + (" · verified" if verified else " · draft"),
            matched_hindi=authored["hindi"],
            matched_id=authored["id"],
            source=authored["source"],
            verified=verified,
            note="" if verified else "not yet checked by a Mundari speaker",
        )

    # tier 2 — exact corpus match
    exact = store.corpus.get(key)
    if exact:
        return Match(
            text=exact["target"],
            tier="corpus",
            confidence=CONFIDENCE["corpus"],
            label="corpus match",
            matched_hindi=exact["hindi"],
            matched_id=exact["id"],
            source=exact["source"],
            verified=bool(exact["verified_by"].strip()),
            note="attested in the corpus, not hand-verified",
        )

    # tier 3 — best partial overlap, explicitly approximate
    if allow_approximate and store.index:
        asked = tokens(clean)
        candidates: dict[str, int] = {}
        for token in asked:
            for candidate_key in store.index.get(token, ()):  # inverted index
                candidates[candidate_key] = candidates.get(candidate_key, 0) + 1
        # only the rows sharing the most words can win on Jaccard, so cap the set:
        # this is what keeps a live console under a few milliseconds
        shortlist = sorted(candidates.items(), key=lambda item: item[1], reverse=True)[:200]
        best_key, best_score = "", 0.0
        for candidate_key, _ in shortlist:
            candidate_tokens = store.token_sets.get(candidate_key, set())
            score = len(asked & candidate_tokens) / max(len(asked | candidate_tokens), 1)
            if score > best_score:
                best_key, best_score = candidate_key, score
        if best_key and best_score >= APPROXIMATE_FLOOR:
            row = store.corpus[best_key]
            return Match(
                text=row["target"],
                tier="approximate",
                confidence=round(CONFIDENCE["approximate"] + 0.35 * best_score, 3),
                label=f"approximate · {int(best_score * 100)}% word overlap",
                matched_hindi=row["hindi"],
                matched_id=row["id"],
                source=row["source"],
                verified=False,
                note="closest sentence in the corpus, not a translation of your words",
            )

    # tier 4 — refuse, honestly
    return Match(
        "",
        "none",
        0.0,
        "no match",
        note=(
            f"no authored phrase and no corpus row close enough "
            f"({store.authored_rows} authored, {store.corpus_rows} corpus)"
        ),
    )


def coverage() -> dict[str, Any]:
    """What the interface prints next to the result: real counts, no rounding up."""
    info = available()
    return {
        **info,
        "authored_verified_pct": round(
            100 * info["authored_verified"] / info["authored_rows"], 1
        ) if info["authored_rows"] else 0.0,
        "claim": (
            f'{info["authored_verified"]} verified classroom phrases · '
            f'{info["corpus_rows"]} corpus sentences (unverified)'
        ),
    }
