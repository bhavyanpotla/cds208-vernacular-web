"""Validate a corpus file against the project's nine-column schema.

This is the answer to "does it conform" — a command and an exit code, not an
opinion. Errors fail the build; warnings are legal but printed so nobody forgets
they exist.

Usage:
    python scripts/validate_corpus.py data/mundari_pairs.tsv
    python scripts/validate_corpus.py data/mundari_pairs.tsv --max-errors 5

Exit code 0 when there are no errors, 1 otherwise.
"""

from __future__ import annotations

import argparse
import pathlib
import sys
import unicodedata

HEADER = [
    "id", "hindi", "target", "script", "source",
    "license", "verified_by", "confidence", "notes",
]

SCRIPTS = {"devanagari", "ol_chiki", "warang_chiti", "tolang_siki"}
CONFIDENCE = {"exact", "near", "draft"}

# Allowed codepoint ranges per script. Devanagari and Ol Chiki are stable and
# verified here; the two newer scripts are intentionally permissive until their
# ranges are pinned from the Unicode data rather than from memory.
RANGES = {
    "devanagari": [(0x0900, 0x097F), (0xA8E0, 0xA8FF), (0x0020, 0x0020), (0x0964, 0x0965)],
    "ol_chiki": [(0x1C50, 0x1C7F), (0x0020, 0x0020), (0x0964, 0x0965)],
    "warang_chiti": [(0x16B00, 0x16B8F), (0x0020, 0x0020)],
    "tolang_siki": [(0x0000, 0x10FFFF)],
}


def allowed(script: str, text: str) -> list[str]:
    ranges = RANGES.get(script, [])
    bad = []
    for ch in text:
        if ch.isspace() or unicodedata.category(ch).startswith(("P", "N")):
            continue
        cp = ord(ch)
        if not any(low <= cp <= high for low, high in ranges):
            bad.append(ch)
    return bad


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=pathlib.Path)
    parser.add_argument("--max-errors", type=int, default=20)
    parser.add_argument("--max-chars", type=int, default=300)
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []

    raw = args.path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        errors.append("file starts with a UTF-8 BOM; strip it")
    text = raw.decode("utf-8", errors="replace")
    if "\ufffd" in text:
        errors.append("file contains U+FFFD replacement characters (bad encoding)")
    if "\r" in text:
        errors.append("file contains CR characters; use LF line endings only")

    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]

    if not lines:
        print("empty file")
        sys.exit(1)

    header = lines[0].split("\t")
    if header != HEADER:
        errors.append(f"header mismatch\n  expected: {HEADER}\n  found:    {header}")

    seen_ids: set[str] = set()
    seen_pairs: set[tuple[str, str]] = set()
    verified = 0
    unverified_licence = 0
    confidence_counts: dict[str, int] = {}
    script_counts: dict[str, int] = {}

    for number, line in enumerate(lines[1:], start=2):
        if not line.strip():
            errors.append(f"line {number}: blank line inside the file")
            continue
        fields = line.split("\t")
        if len(fields) != len(HEADER):
            errors.append(f"line {number}: {len(fields)} fields, expected {len(HEADER)}")
            continue

        row = dict(zip(HEADER, fields, strict=True))
        row_id, hindi, target = row["id"], row["hindi"], row["target"]
        script, confidence = row["script"], row["confidence"]

        if row_id in seen_ids:
            errors.append(f"line {number}: duplicate id {row_id}")
        seen_ids.add(row_id)

        if not hindi.strip() or not target.strip():
            errors.append(f"line {number}: empty hindi or target")

        if script not in SCRIPTS:
            errors.append(f"line {number}: script {script!r} not in {sorted(SCRIPTS)}")
        else:
            script_counts[script] = script_counts.get(script, 0) + 1
            bad = allowed(script, target)
            if bad:
                errors.append(
                    f"line {number}: target has characters outside {script}: "
                    f"{''.join(sorted(set(bad)))[:12]!r}"
                )

        if confidence not in CONFIDENCE:
            errors.append(f"line {number}: confidence {confidence!r} not in {sorted(CONFIDENCE)}")
        confidence_counts[confidence] = confidence_counts.get(confidence, 0) + 1

        if len(hindi) > args.max_chars:
            warnings.append(f"line {number}: hindi is {len(hindi)} chars (limit {args.max_chars})")

        if (hindi, target) in seen_pairs:
            warnings.append(f"line {number}: duplicate (hindi, target) pair")
        seen_pairs.add((hindi, target))

        if hindi.strip() == target.strip():
            warnings.append(f"line {number}: hindi and target are identical")

        if row["verified_by"].strip():
            verified += 1
        if row["license"] in {"", "UNVERIFIED"}:
            unverified_licence += 1

    if unverified_licence:
        warnings.append(
            f"{unverified_licence} rows carry an unverified licence — confirm the "
            "corpus licence before these ship in a demo"
        )

    total = len(lines) - 1
    print(f"file      {args.path}")
    print(f"rows      {total}")
    print(f"scripts   {script_counts}")
    print(f"confidence{confidence_counts}")
    print(f"verified  {verified}/{total}")
    print(f"errors    {len(errors)}")
    print(f"warnings  {len(warnings)}")

    for message in errors[: args.max_errors]:
        print(f"  ERROR   {message}")
    if len(errors) > args.max_errors:
        print(f"  ... {len(errors) - args.max_errors} more errors")

    for message in warnings[: min(args.max_errors, 5)]:
        print(f"  WARN    {message}")
    if len(warnings) > 5:
        print(f"  ... {len(warnings) - 5} more warnings (licence and duplicate noise)")

    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
