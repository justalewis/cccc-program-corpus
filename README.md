# CCCC Program Corpus

Open, linked data from the CCCC convention programs, 1949–2027: sessions, the people listed in them, and their institutions (with ROR, IPEDS and Carnegie class, so two-year college participation can be counted).

Build plan and year-by-year inventory: https://claude.ai/artifact/ATiTrR28yzNNj3BWZe4BuQ

## Status (27 October 2026)

Phases 1 and 2: the eShow listings for 2024–2027 and the born-digital PDF programs for 2004–2023, in one database (15,038 sessions, 59,001 appearances, 18,890 people after exact-name clustering).

| Year | Source | Sessions | Listed people | Affiliation matched | Two-year people | Two-year share* |
|---|---|---|---|---|---|---|
| 2004 San Antonio | PDF | 587 | 2,052 | 96% | 112 | 6.0% |
| 2005 San Francisco | PDF | 536 | 2,044 | 95% | 184 | 9.9% |
| 2006 Chicago | PDF | 588 | 2,190 | 95% | 141 | 7.1% |
| 2007 New York | PDF | 627 | 2,214 | 96% | 172 | 8.5% |
| 2008 New Orleans | PDF | 489 | 1,761 | 95% | 129 | 8.2% |
| 2009 San Francisco | PDF | 662 | 2,231 | 95% | 180 | 9.0% |
| 2010 Louisville | PDF | 670 | 2,313 | 96% | 125 | 5.8% |
| 2011 Atlanta | PDF | 587 | 2,025 | 96% | 90 | 4.8% |
| 2012 St. Louis | PDF | 557 | 1,944 | 97% | 102 | 5.7% |
| 2013 Las Vegas | PDF | 544 | 1,839 | 96% | 115 | 6.9% |
| 2014 Indianapolis | PDF | 607 | 2,149 | 96% | 93 | 4.7% |
| 2015 Tampa | PDF | 618 | 2,234 | 96% | 97 | 4.8% |
| 2016 Houston | PDF | 570 | 2,109 | 96% | 113 | 6.0% |
| 2017 Portland, OR | PDF | 763 | 2,760 | 96% | 202 | 8.0% |
| 2018 Kansas City | PDF | 615 | 2,108 | 96% | 109 | 5.6% |
| 2019 Pittsburgh | PDF | 669 | 2,333 | 97% | 127 | 5.9% |
| 2020 Milwaukee (cancelled) | PDF | 712 | 2,296 | 96% | 122 | 5.8% |
| 2021 Virtual | PDF | 253 | 964 | 96% | 51 | 5.7% |
| 2022 Virtual | PDF | 447 | 1,472 | 95% | 52 | 4.0% |
| 2023 Chicago | PDF | 635 | 1,841 | 96% | 73 | 4.6% |
| 2024 Spokane | eShow | 513 | 1,563 | 97% | 90 | 7.1% |
| 2025 Baltimore | eShow | 867 | 1,963 | 96% | 99 | 5.7% |
| 2026 Cleveland | eShow | 725 | 1,645 | 96% | 65 | 4.6% |
| 2027 Milwaukee (pre-convention) | eShow | 829 | 1,426 | 95% | 42 | 3.7% |

\* Share of listed people at US institutions with an IPEDS record whose institution is two-year (IPEDS level 2, or Carnegie Basic 1–14). These are people *listed in the program*, not registrants or attendees. 2020 is the printed program of a convention that was cancelled. 2021 and 2022 were virtual. The 2027 listing will change before the convention. The source changes from PDF to eShow at 2024, so treat a step between 2023 and 2024 with care.

The eShow listings are complete against the PDF programs: 412 of 414 PDF session codes (2024), 777 of 779 (2025) and 662 of 682 (2026) appear in eShow. Scored against eShow for those three years, the PDF parser finds the listed names with precision 0.94–0.97 and recall 0.92–0.95.

## How it's built

```
build.sh                 runs everything below in order
src/schema.sql           tables: convention, source_document, session, appearance, person, institution, affiliation_match, link
src/parse_eshow.py       eShow listing pages (read from the capture WARC) -> sessions and appearances
src/parse_details.py     eShow detail views -> descriptions; takes the detail name/company only where it differs
src/extract_pdfs.py      program PDFs out of the capture WARCs -> build/pdf/
src/load_conventions.py  data/conventions.csv -> convention table (79 years)
src/parse_pdf.py         2004-2026 PDF programs -> sessions and appearances (font size + session codes)
src/score_pdf.py         PDF parse vs eShow, per session code
src/merge_pdf_titles.py  2024-2026: copy PDF paper titles onto eShow rows, drop the PDF rows
src/check_pdf_codes.py   compares eShow session codes with the PDF programs
src/match_ror.py         ROR v2 affiliation endpoint; accepts only ROR's "chosen" match (cached in data/ror_cache.jsonl)
src/apply_aliases.py     data/affiliation_aliases.csv -> ROR by exact name, country and city
src/enrich_ipeds.py      ROR -> Wikidata (P1771) -> IPEDS HD2023 (HD2008 for closed or merged colleges); data/affiliation_aliases_ipeds.csv
src/strip_places.py      "Old Dominion University, Norfolk, VA" -> the institution, when the dropped place is its own
src/build_persons.py     exact normalized name across all years
src/stats.py             per-year summary -> build/stats.json
src/export.py            CSVs (descriptions left out) -> build/export/
metadata.yml             Datasette metadata with the counting caveats
```

Inputs that are not in git: the private capture folder (`../CCCC-Program-Capture`, NCTE's files), `data/ipeds/HD2023.zip` and `HD2008.zip` (from https://nces.ed.gov/ipeds/datacenter/data/), and the ROR caches, which rebuild themselves.

To browse locally: `datasette build/corpus.db -m metadata.yml`

## Known limits

- People are joined across years only on an exact name. 3,614 clusters span more than one institution and are marked for review; that is where a move and a namesake look the same. Nothing fuzzy has been merged.
- About 4% of appearances with an affiliation have no matched institution: independent scholars, schools, publishers, and a long tail. `affiliation_matches` keeps ROR's top guess for each.
- PDF years: a session title that wraps after a colon loses its subtitle; some lines hold two people and are kept as one; affiliations in 2004–2018 carry the city and state as printed.
- 2008 has no Saturday file in the capture, so its counts are short.
- eShow person keys are per year (no key appears in two years).
- Session descriptions are NCTE's text and stay out of the exports until NCTE agrees.
