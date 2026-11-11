"""Benchmark the tiered bridge against real data and realistic questions.

Run after building the corpus:
    python scripts/build_corpus.py translation-hi-unr.tsv --out-dir data ...
    python scripts/bench_bridge.py

It prints which tier answered, how confident it claims to be, and how long it
took — the three things the interface will show a teacher.
"""

from __future__ import annotations

import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import bridge  # noqa: E402

CLASSROOM = [
    "आज हम गिनती सीखेंगे",
    "अपनी किताब खोलो",
    "मेरे बाद दोहराओ",
    "यह क्या है",
    "पानी कहाँ से आता है",
    "पौधे को सूरज की रोशनी चाहिए",
    "एक से दस तक गिनो",
    "बोर्ड पर लिखो",
    "कल हम कहानी पढ़ेंगे",
    "ध्यान से सुनो",
    "इस चित्र में क्या दिख रहा है",
    "होमवर्क पूरा करके लाओ",
]

GENERAL = [
    "वे भी कमजोर पड़ रहे हैं",
    "मुझे क्रिकेट विश्व कप कब है",
    "कंपनी ने अपनी रिपोर्ट जारी की",
    "आज बारिश हो सकती है",
]


def run(label: str, queries: list[str]) -> None:
    print(f"\n{label}")
    print(f"{'query':<38} {'tier':<12} {'conf':>5}  {'ms':>5}  match")
    tiers: dict[str, int] = {}
    timings: list[float] = []
    for query in queries:
        started = time.perf_counter()
        match = bridge.lookup(query)
        elapsed = (time.perf_counter() - started) * 1000
        timings.append(elapsed)
        tiers[match.tier] = tiers.get(match.tier, 0) + 1
        print(
            f"{query[:36]:<38} {match.tier:<12} {match.confidence:>5.2f}  "
            f"{elapsed:>5.1f}  {(match.matched_hindi or '—')[:34]}"
        )
    print(f"  tiers: {tiers}")
    print(f"  latency: mean {statistics.mean(timings):.2f} ms, max {max(timings):.2f} ms")


def main() -> None:
    info = bridge.available()
    print("loaded:", info)
    print("claim :", bridge.coverage()["claim"])
    run("CLASSROOM PHRASES", CLASSROOM)
    run("GENERAL SENTENCES", GENERAL)


if __name__ == "__main__":
    main()
