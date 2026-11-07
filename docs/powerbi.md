# Power BI: building the report from `exports/`

The app writes four CSVs plus a health file. Power BI Desktop reads that folder,
so one refresh picks up everything. This is the exact sequence to follow.

## 1. Generate the data

Run the app, click around for two or three minutes — open a lesson, tap a term,
translate a sentence, ask the tutor one question it can answer and one it cannot,
take a quiz. Then open **Analytics → Refresh export**.

That writes into `exports/`:

| File | Grain | Key columns |
|---|---|---|
| `fact_events.csv` | one row per user action | `event_name`, `created_at`, `date`, `hour`, `lang`, `user_id`, `session_id`, `provider`, `target_lang`, `latency_ms`, `lesson_id`, `term`, `score`, `passed`, `grounded`, `context` |
| `fact_translations.csv` | one row per provider call | `source_lang`, `target_lang`, `provider`, `latency_ms`, `chars`, `created_at`, `date` |
| `dim_lessons.csv` | one row per lesson | `id`, `subject`, `grade`, `title_en`, `segments`, `questions`, `terms` |
| `dim_users.csv` | one row per learner | `id`, `name`, `ui_language`, `created_at` |
| `_health.json` | export metadata | row counts, null rates, cache hit rate, events never fired |

## 2. Load it

1. Power BI Desktop → **Get data** → **Text/CSV** → pick `exports/fact_events.csv` → **Load**.
2. Repeat for `fact_translations.csv`, `dim_lessons.csv`, `dim_users.csv`.
3. Better, for repeat refreshes: **Get data** → **Folder** → `exports` → **Combine & Transform**.
   In Power Query, keep only the four `*.csv` files (filter out `_health.json`),
   then **Expand** the content column. Name the query `FactEvents` if you only
   need the events table.

Check the types Power BI guessed: `date` should be Date, `score` and `latency_ms`
Whole Number, `passed` and `grounded` True/False. Fix any that came in as text —
`passed` arriving as text is the usual reason a DAX `TRUE` filter silently
returns nothing.

## 3. Relationships

Model view, then drag:

- `fact_events[lesson_id]` → `dim_lessons[id]` (many-to-one)
- `fact_events[user_id]` → `dim_users[id]` (many-to-one)
- `fact_translations[user_id]` → `dim_users[id]` (many-to-one)

Do **not** relate `fact_events` to `fact_translations` directly — they are two
different grains and a relationship between them will double-count. Relate both
to `dim_users` and `dim_lessons`, or keep them as separate pages.

If you build a `dim_languages` table (code, English name, native name, script),
relate `fact_events[lang]` and `fact_translations[target_lang]` to it. That is
what makes the language page sort in a sensible order.

## 4. Measures

New measure on `FactEvents` for each of these:

```dax
Active Learners = DISTINCTCOUNT ( fact_events[user_id] )

Sessions = DISTINCTCOUNT ( fact_events[session_id] )

Total Events = COUNTROWS ( fact_events )

Translations =
CALCULATE ( COUNTROWS ( fact_events ), fact_events[event_name] = "translation_requested" )

Cache Hits =
CALCULATE ( COUNTROWS ( fact_events ), fact_events[event_name] = "translation_served" )

Cache Hit % = DIVIDE ( [Cache Hits], [Translations] + [Cache Hits] )

Avg Latency (ms) = AVERAGE ( fact_events[latency_ms] )

Lessons Opened =
CALCULATE ( DISTINCTCOUNT ( fact_events[lesson_id] ), fact_events[event_name] = "lesson_opened" )

Lessons Completed =
CALCULATE ( DISTINCTCOUNT ( fact_events[lesson_id] ), fact_events[event_name] = "lesson_completed" )

Completion Rate = DIVIDE ( [Lessons Completed], [Lessons Opened] )

Quiz Pass % =
DIVIDE (
    CALCULATE ( COUNTROWS ( fact_events ), fact_events[event_name] = "quiz_submitted", fact_events[passed] = TRUE ),
    CALCULATE ( COUNTROWS ( fact_events ), fact_events[event_name] = "quiz_submitted" )
)

Tutor Turns =
CALCULATE ( COUNTROWS ( fact_events ), fact_events[event_name] = "tutor_question_asked" )

Honest Refusals =
CALCULATE ( COUNTROWS ( fact_events ), fact_events[event_name] = "tutor_refused_ungrounded" )

Refusal Rate = DIVIDE ( [Honest Refusals], [Tutor Turns] )

Terms Tapped =
CALCULATE ( COUNTROWS ( fact_events ), fact_events[event_name] = "term_glossed" )
```

Two of those are worth a sentence in the report: **Cache Hit %** is the cost
story, and **Refusal Rate** is the safety story. Most projects have neither.

## 5. Three pages, in this order

The order is the argument. Each page answers one question.

**Page 1 — Engagement.** Cards for Active Learners, Sessions, Total Events.
Line chart of `Total Events` by `date`. Bar chart of events by `event_name`.
Slicer on `date`. *Question: is anyone using it, and what are they doing?*

**Page 2 — Language.** Matrix with `source_lang` on rows and `target_lang` on
columns, values `[Translations]`. Bar chart of `[Translations]` by target
language. Card for `[Avg Latency (ms)]`, card for `[Cache Hit %]`. Slicer on
`provider` (sarvam / mock / cache). *Question: which languages are used, and how
fast is the engine?*

**Page 3 — Learning outcomes.** Histogram of `score` from `fact_events` where
`event_name = "quiz_submitted"`. Bar of `[Quiz Pass %]` by lesson subject.
Table of `term` sorted by `[Terms Tapped]` descending — the struggle list.
Cards for `[Tutor Turns]` and `[Refusal Rate]`. *Question: are they learning,
and where do they get stuck?*

Set `dim_lessons[title_en]` as the tooltip field on the lesson visuals so a
hover names the lesson instead of showing an id.

## 6. Save and refresh

Save as `docs/vernacular-analytics.pbix` and commit it. The CSVs stay
gitignored; the report is a template that points at the folder.

To refresh: click through the app → **Analytics → Refresh export** in the app →
back in Power BI, **Refresh**. All three pages update. If a visual goes blank,
open `_health.json` first: an empty `fact_events` or a warning there explains it
faster than clicking around the model.

## 7. What to say in the viva

"The dashboard is not a separate analysis. Every visual traces to an event the
app wrote when a student did something, and the same queries feed the in-app
Analytics page — so the two can never disagree. If a feature does not appear in
this report, it is because it is not instrumented, and the coverage audit in
`_health.json` tells me exactly which events have never fired."
