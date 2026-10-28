# CCCC Program Corpus

Open, linked data from the CCCC convention programs, 1949–2027: sessions, the people listed in them, and their institutions (with ROR, IPEDS and Carnegie class, so two-year college participation can be counted).

Build plan and year-by-year inventory: https://claude.ai/artifact/ATiTrR28yzNNj3BWZe4BuQ

## Status (28 October 2026)

The eShow listings for 2024–2027, the born-digital PDF programs for 2004–2023, and the 1998 and 1999 programs from the Wayback Machine, in one database: 16,064 sessions, 63,284 appearances, and 20,627 names after exact-name clustering. 1994–1997 survive online only as index pages, and 2000–2003 not at all.

| Year | Source | Sessions | Listed people | Affiliation matched | Two-year people | Two-year share* |
|---|---|---|---|---|---|---|
| 1998 Chicago | Web (Wayback) | 496 | 1,915 | 94% | 107 | 6.4% |
| 1999 Atlanta (10 of 14 sections) | PDF (Wayback) | 530 | 1,526 | 94% | 108 | 7.9% |
| 2004 San Antonio | PDF | 587 | 2,062 | 96% | 112 | 6.0% |
| 2005 San Francisco | PDF | 536 | 2,048 | 95% | 184 | 9.8% |
| 2006 Chicago | PDF | 588 | 2,202 | 95% | 144 | 7.2% |
| 2007 New York | PDF | 627 | 2,214 | 97% | 166 | 8.3% |
| 2008 New Orleans | PDF | 489 | 1,782 | 95% | 133 | 8.3% |
| 2009 San Francisco | PDF | 662 | 2,248 | 95% | 181 | 9.0% |
| 2010 Louisville | PDF | 670 | 2,332 | 97% | 128 | 5.9% |
| 2011 Atlanta | PDF | 587 | 2,040 | 97% | 92 | 4.9% |
| 2012 St. Louis | PDF | 557 | 1,963 | 97% | 105 | 5.8% |
| 2013 Las Vegas | PDF | 544 | 1,860 | 95% | 116 | 6.8% |
| 2014 Indianapolis | PDF | 607 | 2,149 | 96% | 93 | 4.8% |
| 2015 Tampa | PDF | 618 | 2,238 | 96% | 97 | 4.8% |
| 2016 Houston | PDF | 570 | 2,113 | 96% | 113 | 5.9% |
| 2017 Portland, OR | PDF | 763 | 2,767 | 97% | 205 | 8.0% |
| 2018 Kansas City | PDF | 615 | 2,108 | 96% | 113 | 5.8% |
| 2019 Pittsburgh | PDF | 669 | 2,330 | 97% | 131 | 6.0% |
| 2020 Milwaukee (cancelled) | PDF | 712 | 2,290 | 97% | 122 | 5.7% |
| 2021 Virtual | PDF | 253 | 966 | 97% | 58 | 6.4% |
| 2022 Virtual | PDF | 447 | 1,475 | 96% | 57 | 4.3% |
| 2023 Chicago | PDF | 635 | 1,839 | 96% | 74 | 4.6% |
| 2024 Spokane | eShow | 513 | 1,563 | 97% | 90 | 7.1% |
| 2025 Baltimore | eShow | 867 | 1,963 | 96% | 99 | 5.7% |
| 2026 Cleveland | eShow | 725 | 1,645 | 96% | 65 | 4.6% |
| 2027 Milwaukee (pre-convention) | eShow | 829 | 1,426 | 95% | 42 | 3.7% |

\* Share of listed people at US institutions with an IPEDS record whose institution is two-year (IPEDS level 2, or Carnegie Basic 1–14). These are people *listed in the program*, not registrants or attendees. 1999 counts only the ten letter sections whose PDFs survive (E, F, K and M are titles only). 2020 is the printed program of a convention that was cancelled. 2021 and 2022 were virtual. The 2027 listing will change before the convention. The source changes from PDF to eShow at 2024, so treat a step between 2023 and 2024 with care.

The eShow listings are complete against the PDF programs: 412 of 414 PDF session codes (2024), 777 of 779 (2025) and 662 of 682 (2026) appear in eShow. Scored against eShow for those three years, the PDF parser finds the listed names with precision 0.94–0.97 and recall 0.92–0.95.

## How it's built

```
build.sh                 runs everything below in order
src/schema.sql           tables: convention, source_document, session, appearance, person, institution, affiliation_match, link
src/parse_eshow.py       eShow listing pages (read from the capture WARC) -> sessions and appearances
src/parse_details.py     eShow detail views -> descriptions; takes the detail name/company only where it differs
src/extract_pdfs.py      program PDFs out of the capture WARCs -> build/pdf/
src/load_conventions.py  data/conventions.csv -> convention table (79 years)
src/parse_pdf.py         1999 and 2004-2026 PDF programs -> sessions and appearances (font size + session codes)
src/parse_html_1990s.py  1998 web program; 1999 session titles for the sections whose PDFs are lost
src/score_pdf.py         PDF parse vs eShow, per session code
src/merge_pdf_titles.py  2024-2026: copy PDF paper titles onto eShow rows, drop the PDF rows
src/check_pdf_codes.py   compares eShow session codes with the PDF programs
src/match_ror.py         ROR v2 affiliation endpoint; accepts ROR's "chosen" match only when it shares a word with the string (cached in data/ror_cache.jsonl)
src/apply_aliases.py     data/affiliation_aliases.csv -> ROR by exact name, country and city
src/enrich_ipeds.py      ROR -> Wikidata (P1771) -> IPEDS HD2023 (HD2008 for closed or merged colleges); data/affiliation_aliases_ipeds.csv
src/strip_places.py      "Old Dominion University, Norfolk, VA" -> the institution, when the dropped place is its own
src/build_persons.py     exact normalized name across all years; sorts multi-institution names into moves and review; applies data/person_decisions*.csv
src/stats.py             per-year summary -> build/stats.json
src/review_people.py     the names still marked review, as a decision page -> build/review/people.html
src/review_sample.py     40 random PDF sessions beside their page images -> build/review/index.html (private: NCTE's pages; run by hand)
src/export.py            CSVs (descriptions left out) -> build/export/
metadata.yml             Datasette metadata with the counting caveats
```

Inputs that are not in git: the private capture folder (`../CCCC-Program-Capture`, NCTE's files), `data/ipeds/HD2023.zip` and `HD2008.zip` (from https://nces.ed.gov/ipeds/datacenter/data/), and the ROR caches, which rebuild themselves.

To browse locally: `datasette build/corpus.db -m metadata.yml`

## Reviewing

- `build/review/index.html`: 40 random PDF sessions beside the program page. Tick what's wrong and download the CSV.
- `build/review/people.html`: the 319 names that appear at two institutions in the same year, or return to an earlier one. Choose same person, different people or not sure, then download `person_decisions.csv` into `data/` and rebuild. "Different" splits the name into one person per institution.

Both open straight from the file in an ordinary browser.

## Known limits

- People are joined across years only on an exact name. Of the names at more than one institution, 3,534 move from one to the next without overlap or return and are taken as one person changing jobs; 319 wait on `people.html`. Nothing fuzzy has been merged.
- About 4% of appearances with an affiliation have no matched institution: independent scholars, schools, publishers, and a long tail. `affiliation_matches` keeps ROR's top guess for each, and the ones refused for sharing no word with the string are marked `ror-chosen-refused`.
- PDF years: some lines hold two people and are kept as one; affiliations in 2004–2018 carry the city and state as printed.
- 1998: sections A and J are cut short in the captured pages. 1999: sections E, F, K and M have titles only.
- 2008 has no Saturday file in the capture, so its counts are short.
- eShow person keys are per year (no key appears in two years).
- Session descriptions are NCTE's text and stay out of the exports until NCTE agrees.
