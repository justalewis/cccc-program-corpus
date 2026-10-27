# CCCC Program Corpus

Open, linked data from the CCCC convention programs, 1949–2027: sessions, the people listed in them, and their institutions (with ROR, IPEDS and Carnegie class, so two-year college participation can be counted).

Build plan and year-by-year inventory: https://claude.ai/artifact/ATiTrR28yzNNj3BWZe4BuQ

## Status (27 October 2026)

Phase 1 pilot: the eShow session listings for 2024–2027.

| Year | Sessions | Child presentations | Listed people | Matched to an institution | Two-year share* |
|---|---|---|---|---|---|
| 2024 Spokane | 531 | 309 | 1,563 | 1,347 | 7.1% |
| 2025 Baltimore | 885 | 0 | 1,963 | 1,819 | 5.8% |
| 2026 Cleveland | 748 | 0 | 1,645 | 1,481 | 4.7% |
| 2027 Milwaukee (pre-convention) | 829 | 0 | 1,426 | 1,197 | 3.7% |

\* Share of listed people at US institutions with an IPEDS record whose institution is two-year (IPEDS level 2, or Carnegie 2021 Basic 1–14). These are people *listed in the program*, not registrants or attendees, and the 2027 listing will change before the convention.

The eShow listings are complete against the PDF programs: 412 of 414 PDF session codes (2024), 777 of 779 (2025) and 662 of 682 (2026) appear in eShow.

## How it's built

```
build.sh                 runs everything below in order
src/schema.sql           tables: convention, source_document, session, appearance, person, institution, affiliation_match, link
src/parse_eshow.py       eShow listing pages (read from the capture WARC) -> sessions and appearances
src/parse_details.py     eShow detail views -> descriptions; fixes name/affiliation splits
src/check_pdf_codes.py   compares eShow session codes with the PDF programs
src/match_ror.py         ROR v2 affiliation endpoint; accepts only ROR's "chosen" match (cached in data/ror_cache.jsonl)
src/apply_aliases.py     data/affiliation_aliases.csv -> ROR by exact name, country and city
src/enrich_ipeds.py      ROR -> Wikidata (P1771) -> IPEDS HD2023: sector, level, Carnegie class, two-year flag
src/build_persons.py     one eShow key = one person within a year; exact normalized name across years
src/stats.py             per-year summary -> build/stats.json
src/export.py            CSVs (descriptions left out) -> build/export/
metadata.yml             Datasette metadata with the counting caveats
```

Inputs that are not in git: the private capture folder (`../CCCC-Program-Capture`, NCTE's files), `data/ipeds/HD2023.zip` (from https://nces.ed.gov/ipeds/datacenter/data/HD2023.zip), and the ROR caches, which rebuild themselves.

To browse locally: `datasette build/corpus.db -m metadata.yml`

## Known limits

- People are joined across years only on an exact name. 206 clusters span more than one institution and are marked for review; nothing fuzzy has been merged.
- About 1 in 9 listed people has no matched institution. `affiliation_matches` keeps ROR's top guess and score for each unmatched string, and the most frequent ones are the next additions to `data/affiliation_aliases.csv`.
- eShow person keys are per year (no key appears in two years).
- Session descriptions are NCTE's text and stay out of the exports until NCTE agrees.
