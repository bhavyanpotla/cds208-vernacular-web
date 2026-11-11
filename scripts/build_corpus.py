"""Normalise a raw parallel corpus into the project's canonical schema.

Input:  a two-column TSV of `hindi<TAB>mundari` rows with no header (the shape
        most published corpora ship in).
Output: `mundari_pairs.tsv` with the nine-column schema the app consumes, plus
        `classroom_candidates.tsv` (a shortlist for a native speaker to review)
        and `stats.json`.

Design decisions worth knowing:

* Tabs, not commas. Hindi and Mundari sentences contain commas constantly and
  comma-quoting is the most common way a corpus silently corrupts on round-trip.
* Every row is tagged with its domain in `notes`. A corpus of news and legal
  sentences is not a corpus of classroom sentences, and the app should know the
  difference instead of pretending one covers the other.
* `confidence` is `exact` for a corpus-attested pair and `draft` for a row that
  only survived cleaning. `verified_by` stays empty until a human signs off, and
  the validator warns on that — it is the honest state, not an error.
* `license` is left as `UNVERIFIED` unless you pass one in. Do not guess a
  licence; confirm it with whoever published the corpus.

Usage:
    python scripts/build_corpus.py translation-hi-unr.tsv \
        --out-dir data --lang-code MUN --script devanagari \
        --source "hi-unr parallel corpus" --license UNVERIFIED
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import statistics
import unicodedata

HEADER = [
    "id", "hindi", "target", "script", "source",
    "license", "verified_by", "confidence", "notes",
]

DEVANAGARI = (0x0900, 0x097F)
OL_CHIKI = (0x1C50, 0x1C7F)

# Domain cue list for the classroom shortlist. Deliberately narrow: it is better
# to hand a reviewer 800 plausible rows than 17,000 irrelevant ones.
CLASSROOM_CUES = (
    "पाठ", "पुस्तक", "किताब", "बच्च", "स्कूल", "विद्यालय", "अध्यापक", "शिक्षक",
    "कक्षा", "छात्र", "पढ़", "लिख", "अक्षर", "संख्या", "गिनती", "पानी", "पौध",
    "पेड़", "भोजन", "सूरज", "हवा", "मिट्टी", "खेल", "गाना", "कहानी", "चित्र",
)

_WS = re.compile(r"\s+")
# Breadcrumbs and links survive web-scraped corpora: "Home > T-shirts > Listings".
# They are navigational noise, not sentences, and no amount of punctuation
# stripping makes them teachable. Drop the row.
_MARKUP = re.compile(r"[<>«»]|https?://|www\.|\[\d+\]|&[a-z]+;")


def script_ratio(text: str, block: tuple[int, int]) -> float:
    letters = [
        ord(ch) for ch in text
        if not ch.isspace() and not unicodedata.category(ch).startswith(("P", "N"))
    ]
    if not letters:
        return 0.0
    return sum(1 for cp in letters if block[0] <= cp <= block[1]) / len(letters)


def clean(text: str) -> str:
    """Collapse whitespace, strip zero-width joiners, drop stray quotes."""
    text = text.replace("\u200b", "").replace("\u200c", "").replace("\u200d", "")
    text = text.replace("\ufeff", "").replace("\ufffd", "")
    text = _WS.sub(" ", text).strip()
    return text.strip('"').strip()


def is_classroom(hindi: str) -> bool:
    return any(cue in hindi for cue in CLASSROOM_CUES)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("raw", type=pathlib.Path, help="two-column TSV, no header")
    parser.add_argument("--out-dir", type=pathlib.Path, default=pathlib.Path("data"))
    parser.add_argument("--lang-code", default="MUN")
    parser.add_argument("--script", default="devanagari")
    parser.add_argument("--source", default="unnamed corpus")
    parser.add_argument("--license", default="UNVERIFIED")
    parser.add_argument("--max-chars", type=int, default=300)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    block = DEVANAGARI if args.script == "devanagari" else OL_CHIKI
    raw_lines = args.raw.read_text(encoding="utf-8").split("\n")

    stats: dict[str, object] = {
        "input_file": args.raw.name,
        "input_rows": len([line for line in raw_lines if line.strip()]),
        "skipped_wrong_columns": 0,
        "skipped_empty_side": 0,
        "skipped_wrong_script": 0,
        "skipped_too_long": 0,
        "skipped_duplicate_pair": 0,
        "skipped_identical": 0,
        "skipped_markup": 0,
        "skipped_impure_target": 0,
        "kept": 0,
    }

    seen: set[tuple[str, str]] = set()
    rows: list[list[str]] = []
    counter = 0

    for line in raw_lines:
        if not line.strip():
            continue
        if line.count("\t") != 1:
            stats["skipped_wrong_columns"] = int(stats["skipped_wrong_columns"]) + 1
            continue
        left, right = (clean(part) for part in line.split("\t"))
        if not left or not right:
            stats["skipped_empty_side"] = int(stats["skipped_empty_side"]) + 1
            continue
        if script_ratio(left, DEVANAGARI) < 0.6 or script_ratio(right, block) < 0.6:
            stats["skipped_wrong_script"] = int(stats["skipped_wrong_script"]) + 1
            continue
        if len(left) > args.max_chars or len(right) > args.max_chars:
            stats["skipped_too_long"] = int(stats["skipped_too_long"]) + 1
            continue
        if left == right:
            stats["skipped_identical"] = int(stats["skipped_identical"]) + 1
            continue
        if _MARKUP.search(left) or _MARKUP.search(right):
            stats["skipped_markup"] = int(stats["skipped_markup"]) + 1
            continue
        # The target must be pure: a Mundari sentence rendered in Devanagari may
        # not carry Cyrillic, Arabic, stray Latin or math symbols. Contamination
        # like that comes from the source corpus, not from us.
        impure = [
            ch for ch in right
            if not ch.isspace()
            and not unicodedata.category(ch).startswith(("P", "N"))
            and not (block[0] <= ord(ch) <= block[1])
        ]
        if impure:
            stats["skipped_impure_target"] = int(stats["skipped_impure_target"]) + 1
            continue
        if (left, right) in seen:
            stats["skipped_duplicate_pair"] = int(stats["skipped_duplicate_pair"]) + 1
            continue
        seen.add((left, right))

        counter += 1
        rows.append([
            f"{args.lang_code}-{counter:05d}",
            left,
            right,
            args.script,
            args.source,
            args.license,
            "",                                   # verified_by: nobody yet
            "exact",                              # corpus-attested
            "domain=classroom" if is_classroom(left) else "domain=general",
        ])

    stats["kept"] = len(rows)

    canonical = args.out_dir / "mundari_pairs.tsv"
    with canonical.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\t".join(HEADER) + "\n")
        for row in rows:
            handle.write("\t".join(row) + "\n")

    classroom = [row for row in rows if row[8] == "domain=classroom"]
    shortlist = args.out_dir / "classroom_candidates.tsv"
    with shortlist.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\t".join(HEADER) + "\n")
        for row in classroom:
            handle.write("\t".join(row) + "\n")

    hindi_lengths = [len(row[1]) for row in rows]
    target_lengths = [len(row[2]) for row in rows]
    stats["length_chars"] = {
        "hindi_mean": round(statistics.mean(hindi_lengths), 1) if rows else 0,
        "hindi_median": statistics.median(hindi_lengths) if rows else 0,
        "hindi_max": max(hindi_lengths) if rows else 0,
        "target_mean": round(statistics.mean(target_lengths), 1) if rows else 0,
        "target_max": max(target_lengths) if rows else 0,
    }
    stats["classroom_candidates"] = len(classroom)
    stats["classroom_share_pct"] = round(100 * len(classroom) / len(rows), 1) if rows else 0
    stats["script"] = args.script
    stats["source"] = args.source
    stats["license"] = args.license
    stats["verified_rows"] = 0

    (args.out_dir / "stats.json").write_text(
        json.dumps(stats, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(json.dumps(stats, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
