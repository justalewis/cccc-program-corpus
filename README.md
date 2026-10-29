# CCCC Program Corpus

Cite the data: Lewis, Justin. *CCCC Convention Program Corpus*, version 0.1.0. Zenodo, 2026. https://doi.org/10.5281/zenodo.23751615

Open, linked data from the CCCC convention programs, 1949–2027: sessions, the people listed in them, and their institutions (with ROR, IPEDS and Carnegie class, so two-year college participation can be counted).

Build plan and year-by-year inventory: https://claude.ai/artifact/ATiTrR28yzNNj3BWZe4BuQ

## Status (28 October 2026)

The eShow listings for 2024–2027, the born-digital PDF programs for 2004–2023, and the 1998 and 1999 programs from the Wayback Machine, in one database: 16,166 sessions, 63,791 appearances, and 19,207 names after exact-name clustering. 1994–1997 survive online only as front pages with no program, and 2000–2003 not at all.

| Year | Source | Sessions | Listed people | Affiliation matched | Two-year people | Two-year share* |
|---|---|---|---|---|---|---|
| 1998 Chicago | Web (Wayback) | 496 | 1,911 | 94% | 114 | 6.8% |
| 1999 Atlanta (10 of 14 sections) | PDF (Wayback) | 530 | 1,484 | 96% | 112 | 8.2% |
| 2004 San Antonio | PDF | 587 | 2,008 | 96% | 111 | 6.0% |
| 2005 San Francisco | PDF | 536 | 1,999 | 96% | 190 | 10.3% |
| 2006 Chicago | PDF | 588 | 2,157 | 96% | 151 | 7.6% |
| 2007 New York | PDF | 627 | 2,183 | 97% | 172 | 8.6% |
| 2008 New Orleans | PDF | 591 | 2,080 | 96% | 159 | 8.4% |
| 2009 San Francisco | PDF | 662 | 2,232 | 96% | 181 | 9.0% |
| 2010 Louisville | PDF | 670 | 2,288 | 97% | 131 | 6.1% |
| 2011 Atlanta | PDF | 587 | 2,010 | 97% | 92 | 4.9% |
| 2012 St. Louis | PDF | 557 | 1,935 | 98% | 107 | 6.0% |
| 2013 Las Vegas | PDF | 544 | 1,850 | 97% | 126 | 7.4% |
| 2014 Indianapolis | PDF | 607 | 2,136 | 97% | 99 | 5.1% |
| 2015 Tampa | PDF | 618 | 2,233 | 97% | 106 | 5.2% |
| 2016 Houston | PDF | 570 | 2,105 | 97% | 120 | 6.2% |
| 2017 Portland, OR | PDF | 763 | 2,764 | 97% | 210 | 8.1% |
| 2018 Kansas City | PDF | 615 | 2,104 | 97% | 118 | 6.0% |
| 2019 Pittsburgh | PDF | 669 | 2,325 | 97% | 131 | 6.0% |
| 2020 Milwaukee (cancelled) | PDF | 712 | 2,284 | 97% | 122 | 5.7% |
| 2021 Virtual | PDF | 253 | 963 | 97% | 58 | 6.4% |
| 2022 Virtual | PDF | 447 | 1,473 | 96% | 57 | 4.2% |
| 2023 Chicago | PDF | 635 | 1,837 | 97% | 74 | 4.6% |
| 2024 Spokane | eShow | 513 | 1,562 | 97% | 91 | 7.2% |
| 2025 Baltimore | eShow | 867 | 1,957 | 96% | 99 | 5.7% |
| 2026 Cleveland | eShow | 725 | 1,641 | 96% | 65 | 4.6% |
| 2027 Milwaukee (pre-convention) | eShow | 829 | 1,392 | 96% | 42 | 3.7% |

\* Share of listed people at US institutions with an IPEDS record whose institution is two-year (IPEDS level 2, or Carnegie Basic 1–14). These are people *listed in the program*, not registrants or attendees. 1999 counts only the ten letter sections whose PDFs survive (E, F, K and M are titles only). 2020 is the printed program of a convention that was cancelled. 2021 and 2022 were virtual. The 2027 listing will change before the convention. The source changes from PDF to eShow at 2024, so treat a step between 2023 and 2024 with care.

Scored against the programs' own Index of Participants (`src/check_index.py`, six years where the program ends with one), the parser's (person, session) pairs reach:

| Year | Precision | Recall | Main reason for misses |
|---|---|---|---|
| 2004 | 0.87 | 0.82 | special-interest sessions printed without codes; Research Network Forum |
| 2005 | 0.93 | 0.92 | |
| 2007 | 0.97 | 0.94 | |
| 2008 | 0.94 | 0.92 | |
| 2010 | 0.93 | 0.89 | Research Network Forum (113 pairs) |
| 2011 | 0.94 | 0.89 | |

The Research Network Forum (code RN.1) is one event with 90 to 110 presenters a year in these programs that the parser does not read. The index is not a perfect standard (it can omit or misprint a code), so these describe agreement.

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
src/build_persons.py     exact normalized name across all years; sorts multi-institution names into moves and review; applies data/person_decisions*.csv and data/name_merges*.csv
src/stats.py             per-year summary -> build/stats.json
src/build_groups.py      the special-interest slots (FSIG, TSIG, WSIG) grouped by name -> sgroup, session.group_id (data/group_aliases.csv joins variants)
src/fetch_themes.py       NCTE past-conventions page -> data/themes.csv (dates, sites, themes, program chairs)
src/link_pinakes.py      suggested links from convention papers to Pinakes articles -> build/links/pinakes_suggestions.csv (needs a Pinakes dump)
src/review_links.py      the suggested pairs as a decision page -> build/review/links.html
src/build_links.py       suggestions plus data/link_decisions*.csv -> the link table
src/review_crosswalk.py  the area headings and their draft families, as a decision page -> build/review/crosswalk.html
src/parse_areas.py       the proposal area above each session in the PDF programs -> session.area, area_group (data/area_crosswalk.csv)
src/review_people.py     the names still marked review, as a decision page -> build/review/people.html
src/near_names.py        pairs of names that differ by a middle initial, nickname, surname part or one letter and share an institution -> build/review/near-names.html
src/review_sample.py     40 random PDF sessions beside their page images -> build/review/index.html (private: NCTE's pages; run by hand)
src/export.py            CSVs (descriptions left out) -> build/export/
src/release.py           release package for deposit: CSVs, SQLite, data dictionary, CITATION.cff, zenodo.json draft (run by hand; uploads nothing)
metadata.yml             Datasette metadata with the counting caveats
```

Inputs that are not in git: the private capture folder (`../CCCC-Program-Capture`, NCTE's files), `data/ipeds/HD2023.zip` and `HD2008.zip` (from https://nces.ed.gov/ipeds/datacenter/data/), and the ROR caches, which rebuild themselves.

To browse locally: `datasette build/corpus.db -m metadata.yml`

Reader (research interface): https://cccc-program-reader.fly.dev, built from `reader/`. Run locally with `READER_DB=build/reader.db flask --app reader/app.py run`; build `reader.db` with `python -I reader/build_reader.py <release_dir> build/reader.db`.

Public view: https://cccc-program-corpus.fly.dev (Datasette over the release database; see `docs/deploy.md`).

## Reviewing

- `build/review/index.html`: 40 random PDF sessions beside the program page. Tick what's wrong and download the CSV.
- `build/review/people.html` (all decided on 28 October 2026): the 318 names that appear at two institutions in the same year, or return to an earlier one. Choose same person, different people or not sure, then download `person_decisions.csv` into `data/` and rebuild. "Different" splits the name into one person per institution.
- `build/review/near-names.html`: about 1,600 pairs of names that are probably one person printed two ways (a middle initial, a nickname, part of a hyphenated surname, or one letter), sharing an institution. Each group has a button to mark all its undecided pairs as the same person. Download `name_merges.csv` into `data/` and rebuild.

- `build/review/crosswalk.html`: the 51 area headings CCCC used, each with the family my draft puts it in (15 families). Change a family, add one, or give a heading a different family in a given year. Download `area_crosswalk.csv` over `data/area_crosswalk.csv` and rebuild.

- `build/review/links.html`: 407 pairs of a convention paper and a Pinakes article it may have become (all of tiers B and C, plus a random 150 of tier A to measure precision). Choose Same work, Different or Not sure and download `link_decisions.csv` into `data/`. Made from `build/links/pinakes_suggestions.csv`, which `src/link_pinakes.py` writes from a dump of the Pinakes API.

All five open straight from the file in an ordinary browser.

## Code archive

The code (the reader, the build pipeline, the review pages and the tests) is archived on Zenodo through GitHub releases, separately from the data. Cite the code: Lewis, Justin. *CCCC Program Reader: code for the CCCC Convention Program Corpus*, version 0.1.1. Zenodo, 2026. https://doi.org/10.5281/zenodo.23753772 (this DOI covers all versions; version 0.1.1 is https://doi.org/10.5281/zenodo.23753773). Each release is a snapshot of this repository; `.zenodo.json` holds its metadata and `THIRD-PARTY-NOTICES.md` lists what was not written here.

## License

Code: MIT (`LICENSE`). Data: Creative Commons Attribution 4.0 International, CC BY 4.0 (`DATA-LICENSE.txt`). Credit: Lewis, Justin. *CCCC Convention Program Corpus*, version 0.1.0. https://doi.org/10.5281/zenodo.23751615 (Zenodo, published 29 October 2026). The programs belong to NCTE; the data holds facts printed in them (names, affiliations, titles, session codes) and our matching and groupings, and leaves out NCTE's session descriptions. Corrections: justalewis1@gmail.com.

## Tests

`python -m pytest tests` (needs `build/reader.db`). The reader tests check that every page loads and is marked noindex, that person pages exist only for people listed at two or more conventions, that suppressed people have no page, that network views respect their thresholds, that no private column (descriptions, eShow keys, call text) is in the database or exports, and that title matching uses word boundaries. The unit tests cover the splitter, the name matcher, group names, area cleaning and the Pinakes author key, and guard against a backspace character sneaking into source through a shell heredoc.

## Planning notes

- `docs/tools-and-interface.md`: what the data can support (28 tools) and an interface sketch.
- `docs/pinakes-links-plan.md`: linking convention papers to Pinakes articles (pilot: `src/link_pinakes.py`).
- `docs/deploy.md`: the deploy recommendation (private Datasette on Fly.io first, Pinakes later).
- Release: `python -I src/release.py build/corpus.db build/stats.json build/release v0.1.0-draft`. Fields still marked [TO DECIDE] (ORCID, an NCTE statement, the DOI) need Justin before deposit.

## Known limits

- People are joined across years on an exact name, plus reviewed pairs. Justin Lewis checked 1,608 near-name pairs (a middle initial, a nickname, a typo, part of a hyphenated surname) and joined all but one (Susan Miller and Susan Miller-Cochran are two people), and checked the 318 names at two institutions in one year or returning to an earlier one (all one person). 3,406 names move from one institution to the next without overlap or return and are taken as one person changing jobs; 26 merged names now show two institutions in one year and are marked for a look. Names that differ in other ways stay separate.
- About 4% of appearances with an affiliation have no matched institution: independent scholars, schools, publishers, and a long tail. `affiliation_matches` keeps ROR's top guess for each, and the ones refused for sharing no word with the string are marked `ror-chosen-refused`.
- PDF years: where the program ran two presenters into one entry, the parser splits it at a common first name (from `data/first_names.txt`) that ends a comma segment and has an institution after it. That catches the 2009 "A, Univ X, and B, Univ Y" pattern and most others; a second person with no institution after the name stays merged. Affiliations in 2004–2018 carry the city and state as printed.
- 1994–1997: the archived pages hold no program. The 1994 "presenter index" lists about a dozen papers posted online, the 1996 site links to session pages that were never captured, and 1995 and 1997 have only a front page.
- 1998: sections A and J are cut short in the captured pages. 1999: sections E, F, K and M have titles only.
- eShow person keys are per year (no key appears in two years).
- Session descriptions are NCTE's text and stay out of the exports until NCTE agrees.
