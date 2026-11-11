# Provenance — Mundari parallel corpus

## Source

| Field | Value |
|---|---|
| File supplied | `translation-hi-unr.tsv` (3.6 MB) |
| Shape | two columns, `hindi<TAB>mundari`, no header row, UTF-8 |
| Language pair | Hindi → Mundari, **both sides in Devanagari** |
| Licence | **UNVERIFIED — confirm before any public or demo use** |
| Rows in, non-empty | 17,826 |
| Rows kept | **17,729** |
| Rows dropped | 97 |

The filename and shape match the convention used by published Hindi–`unr`
parallel corpora (`unr` is the ISO 639-3 code for Mundari). That is a strong
hint about origin, **not a licence**. Until the exact licence is confirmed with
whoever published it, every row carries `license = UNVERIFIED` and the validator
warns on the whole file. Do not ship this in a public demo until that line
changes.

## What was dropped, and why

| Reason | Rows |
|---|---|
| Wrong column count (stray quote characters on their own lines) | 17 |
| Empty side | 1 |
| Identical Hindi and Mundari text | 22 |
| Exact duplicate pair | 5 |
| Web-scraped markup — breadcrumbs (`Home > T-shirts > Listings`), URLs, entities | 44 |
| Target contaminated with non-Devanagari letters (Cyrillic, Arabic, stray Latin, `+=`) | 8 |

None of these are loss. The breadcrumb rows are navigation from a scraped
website, not sentences, and the contaminated rows would have rendered as broken
script in the classroom display.

## What is *not* verified

**Zero rows have been checked by a native Mundari speaker.** `verified_by` is
empty on all 17,729 rows and `confidence = exact` means only "attested in the
source corpus", not "correct". This is the honest state, and the app must print
it: a corpus-attested pair and a human-verified pair are different things, and
the interface should never blur them.

## Domain fit — the finding that matters

This is a general corpus, not a classroom corpus. Measured against a narrow
school-vocabulary cue list (पाठ, पुस्तक, बच्चे, स्कूल, अध्यापक, कक्षा, पानी, पौध,
भोजन, गिनती, कहानी …):

| Metric | Value |
|---|---|
| Rows touching classroom vocabulary | **1,023 of 17,729 — 5.8%** |
| Hindi length | mean 38 chars, median 38, max 79 |
| Mundari length | mean 41 chars, max 129 |

So roughly 94% of this corpus is news, legal and administrative prose. Feeding a
teacher's "today we will learn counting" into it will match on surface tokens and
return something syntactically parallel and pedagogically useless.

Two consequences, both already reflected in the build:

1. `classroom_candidates.tsv` extracts the 1,023 plausible rows so a native
   speaker can review a short list instead of 17,000 irrelevant ones.
2. The product needs a **small hand-authored classroom phrase set** as the first
   match tier, with the corpus as the second tier and the lexicon as the third.
   Confidence labels must reflect the tier, not the row count.

## Files

| File | Rows | Purpose |
|---|---|---|
| `mundari_pairs.tsv` | 17,729 | canonical corpus, nine-column schema |
| `classroom_candidates.tsv` | 1,023 | shortlist for native-speaker review |
| `stats.json` | — | every count in this document, machine-readable |
| `build_corpus.py` | — | raw TSV → canonical, reproducible |
| `validate_corpus.py` | — | schema + script + licence checks, exit code |

Reproduce with:

```bash
python scripts/build_corpus.py translation-hi-unr.tsv \
    --out-dir data --lang-code MUN --script devanagari \
    --source "hi-unr parallel corpus" --license UNVERIFIED

python scripts/validate_corpus.py data/mundari_pairs.tsv
```

## Open items

1. **Confirm the licence.** Blocks public demo use.
2. **Native-speaker review** of `classroom_candidates.tsv` — start with 150 rows,
   not 1,023. Fill `verified_by` as you go; the validator counts them.
3. **Author 40–60 classroom phrases by hand** (greetings, instructions,
   numbers 1–20, "open your book", "repeat after me"). This set carries the demo,
   not the corpus.
4. Decide whether the Mundari should render in **Devanagari or Ol Chiki**. This
   corpus is Devanagari; the reference product claims Ol Chiki. Ol Chiki needs a
   transliteration table that does not exist in this file.
