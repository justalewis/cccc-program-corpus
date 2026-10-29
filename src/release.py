"""Assemble a release package of the corpus for deposit (Zenodo). Writes files only; uploads nothing.

Usage: python -I src/release.py <db_path> <stats.json> <out_root> <version>
Writes <out_root>/cccc-program-corpus-<version>/ with:
  data/*.csv                 the export tables (session descriptions and eShow keys left out)
  cccc-program-corpus.sqlite the same tables as one SQLite file
  datapackage.json           Frictionless Data Package: every table and column described
  DATA-DICTIONARY.md         the same descriptions as a readable page
  README.md, CITATION.cff, zenodo.json (deposit metadata draft), SHA256SUMS
and a zip of that folder beside it. Fields still marked [TO DECIDE] (ORCID, the NCTE statement, the DOI) need Justin before deposit.
"""
import csv, hashlib, json, os, shutil, sqlite3, sys, zipfile
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python -I leaves it off
from export import TABLES

TITLE = "CCCC Convention Program Corpus"
AUTHOR = {"name": "Lewis, Justin", "affiliation": "Olympic College", "orcid": "[TO DECIDE: ORCID]"}
LICENSE = "CC-BY-4.0"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
REPO = "https://github.com/justalewis/cccc-program-corpus"
CONTACT = "justalewis1@gmail.com"

TABLE_DOC = {
    "conventions": "One row per CCCC convention year, 1949–2027, with city and status. Most years before 1998 have no sessions in this release.",
    "sessions": "One row per session as printed in the program. Codes and titles are as printed; 2024–2027 also carry eShow's session type, tracks, times and rooms.",
    "appearances": "One row per name listed in a session, with the name, affiliation and paper title exactly as printed, and the person and institution they were matched to.",
    "people": "Name clusters that join appearances across years. See `method` for how each cluster was formed.",
    "groups": "Special interest groups, caucuses, standing groups and consortia that held meetings in the programs' special-interest slots (codes FSIG, TSIG, WSIG, PSIG; eShow type Special Interest Group/Business Meeting from 2024), grouped by the name in the session title. A slot also held one-off topical discussions, which appear as single-year entries.",
    "source_documents": "The program file or page each session and appearance was read from.",
    "institutions": "Institutions matched to printed affiliations: ROR records, with IPEDS data for US colleges.",
    "affiliation_matches": "Each distinct printed affiliation and the institution it was matched to, with the matching method.",
}
FIELD_DOC = {
    "conventions": {
        "year": ("integer", "Convention year (primary key)."),
        "city": ("string", "Host city as NCTE lists it; 'Virtual' for 2021 and 2022."),
        "venue": ("string", "Not filled."),
        "theme": ("string", "Convention theme, from NCTE's past-conventions page."),
        "chair": ("string", "Program chair, from the same page."),
        "dates": ("string", "Convention dates as NCTE lists them."),
        "site": ("string", "Site as NCTE lists it, including '(Cancelled)' or 'Virtual Convention'."),
        "status": ("string", "held, cancelled (2020), virtual (2021, 2022) or upcoming (2027)."),
    },
    "sessions": {
        "id": ("string", "Session id: eshow:<key> (2024–2027), pdf:<year>:<code> (1999, 2004–2023) or html:<year>:<code> (1998, 1999)."),
        "year": ("integer", "Convention year."),
        "source_document_id": ("string", "The document the session was read from (source_documents.id)."),
        "parent_id": ("string", "For a presentation inside a combined panel (2024), the panel's session id."),
        "code": ("string", "Session code as printed, normalized to LETTER.NUMBER (B.32, MW.6)."),
        "title": ("string", "Session title as printed."),
        "session_type": ("string", "eShow session type (2024–2027): Concurrent Panel, Individual 30-Minute Presentation, Roundtable Session, Workshop, Poster ..."),
        "audience_level": ("string", "2024 only: Two-year, Four-year, Graduate level, ' | ' separated."),
        "tracks": ("string", "eShow proposal areas and extra type labels (2025–2026), ' | ' separated."),
        "area": ("string", "Proposal area printed above the session in the PDF programs (2004-2017, 2019-2026), as CCCC named it that year; empty where the program prints none."),
        "area_group": ("string", "The area mapped onto a family that holds across renamings (data/area_crosswalk.csv). A draft crosswalk, not CCCC's."),
        "group_id": ("string", "For a session held in a special-interest slot: the group it belongs to (groups.id)."),
        "topic_tags": ("string", "2018 only: the three hashtags printed above each session, in place of an area."),
        "dates": ("string", "eShow date(s), ' | ' separated."),
        "time_label": ("string", "eShow time as printed, with time zone."),
        "room": ("string", "eShow room."),
        "cancelled": ("integer", "1 if eShow marks the session cancelled."),
    },
    "appearances": {
        "id": ("integer", "Row id."),
        "year": ("integer", "Convention year."),
        "session_id": ("string", "sessions.id."),
        "ord": ("integer", "Order of the name within the session."),
        "role": ("string", "Role label printed before the name, as printed: Chair, Speakers, Respondent, Workshop Leader ..."),
        "role_group": ("string", "Role folded into chair, speaker, respondent, facilitator (workshop, roundtable and discussion leaders) or other."),
        "name_as_printed": ("string", "Name exactly as printed."),
        "affiliation_as_printed": ("string", "Affiliation exactly as printed, including any city and state."),
        "paper_title": ("string", "Individual paper title where the program prints one (about half of appearances)."),
        "person_id": ("string", "people.id."),
        "institution_id": ("string", "institutions.id; empty when the affiliation was not matched."),
        "source_document_id": ("string", "source_documents.id."),
        "page": ("integer", "PDF page the name appears on (PDF years)."),
    },
    "people": {
        "id": ("string", "Person id: p:<folded name>, with ~<institution> appended when a reviewer split a name into different people."),
        "display_name": ("string", "The most common printed form of the name."),
        "method": ("string", "exact-name: one institution or none. exact-name;moves: several institutions, one per year, never returning to an earlier one (read as one person changing jobs). exact-name;review: two institutions in one year, or a return; not yet checked. reviewed-same / reviewed-split: checked by a person. near-name-reviewed: two spellings of a name joined by a person."),
    },
    "groups": {
        "id": ("string", "Group id, built from the normalized name."),
        "name": ("string", "Name as most often printed, without suffixes such as SIG, Business Meeting or Standing Group."),
        "kind": ("string", "caucus, standing group, consortium, special interest group, or interest-slot session (a slot whose titles never say what kind of group it is). Follows the latest year's wording, since many SIGs became standing groups."),
        "first_year": ("integer", "First convention with a session under this name."),
        "last_year": ("integer", "Last convention with a session under this name."),
        "years": ("integer", "Number of conventions with a session under this name."),
        "sessions": ("integer", "Number of sessions under this name."),
    },
    "source_documents": {
        "id": ("string", "Document id."),
        "year": ("integer", "Convention year."),
        "kind": ("string", "pdf, html (Wayback Machine replay) or eshow-listing."),
        "url": ("string", "Original URL, or the program file's name for PDFs."),
        "rights": ("string", "Rights holder and how the copy was made."),
    },
    "institutions": {
        "id": ("string", "ror:<ROR id> for ROR records, ipeds:<UNITID> for colleges matched only in IPEDS."),
        "name": ("string", "ROR or IPEDS name."),
        "ror_id": ("string", "ROR id."),
        "wikidata": ("string", "Wikidata item, where ROR gives one."),
        "ipeds_unitid": ("string", "IPEDS UNITID (US colleges)."),
        "sector": ("integer", "IPEDS SECTOR (1 public four-year ... 9 private for-profit less-than-two-year)."),
        "iclevel": ("integer", "IPEDS ICLEVEL: 1 four-year or above, 2 at least two but less than four years, 3 less than two years."),
        "two_year": ("integer", "1 when ICLEVEL is 2 or the Carnegie Basic class is 1–14 (associate's colleges)."),
        "carnegie_basic": ("integer", "Carnegie Basic classification (2021 from IPEDS HD2023; 2005 from HD2008 for closed colleges)."),
        "country": ("string", "Country code from ROR."),
        "kind": ("string", "ROR type: education, company, nonprofit, government ..."),
        "control": ("integer", "IPEDS CONTROL: 1 public, 2 private nonprofit, 3 private for-profit."),
        "state": ("string", "IPEDS state (US colleges)."),
        "lat": ("number", "IPEDS latitude."),
        "lon": ("number", "IPEDS longitude."),
        "hbcu": ("integer", "1 if IPEDS flags a historically Black college or university."),
        "tribal": ("integer", "1 if IPEDS flags a tribal college.")
    },
    "affiliation_matches": {
        "affiliation_as_printed": ("string", "A distinct printed affiliation."),
        "institution_id": ("string", "Matched institution; empty when none was accepted."),
        "method": ("string", "ror-affiliation-chosen (ROR's own confident match), alias or ipeds-alias (curated list), ipeds-exact-name, place-stripped (a trailing city or state removed, then matched, when that place is the institution's own); ror-affiliation-top:<id> and ror-chosen-refused:<id> record a guess that was not accepted."),
        "score": ("number", "ROR's score for its match, where there is one."),
    },
}

def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def main(db_path, stats_path, out_root, version):
    out = os.path.join(out_root, f"cccc-program-corpus-{version}")
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(os.path.join(out, "data"))
    con = sqlite3.connect(db_path)
    rel = sqlite3.connect(os.path.join(out, "cccc-program-corpus.sqlite"))
    resources, counts = [], {}
    for name, q in TABLES.items():
        cur = con.execute(q)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        counts[name] = len(rows)
        docs = FIELD_DOC[name]
        missing = [c for c in cols if c not in docs]
        assert not missing, f"undocumented columns in {name}: {missing}"
        with open(os.path.join(out, "data", name + ".csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(cols); w.writerows(rows)
        types = {"integer": "INTEGER", "number": "REAL", "string": "TEXT"}
        rel.execute(f"CREATE TABLE {name} (" + ", ".join(f"{c} {types[docs[c][0]]}" for c in cols) + ")")
        rel.executemany(f"INSERT INTO {name} VALUES ({','.join('?' * len(cols))})", rows)
        resources.append({"name": name, "path": f"data/{name}.csv", "format": "csv", "encoding": "utf-8",
                          "description": TABLE_DOC[name],
                          "schema": {"fields": [{"name": c, "type": docs[c][0], "description": docs[c][1]} for c in cols]}})
    rel.commit(); rel.execute("VACUUM"); rel.close()

    stats = json.load(open(stats_path, encoding="utf-8"))["years"]
    years = sorted(int(y) for y, s in stats.items() if s["sessions"])
    today = date.today().isoformat()
    pkg = {"name": "cccc-program-corpus", "title": TITLE, "version": version, "created": today,
           "licenses": [{"name": LICENSE, "path": LICENSE_URL, "title": "Creative Commons Attribution 4.0 International"}], "contributors": [{"title": AUTHOR["name"], "role": "author"}],
           "description": "Sessions and listed participants from the programs of the Conference on College Composition and Communication (CCCC), parsed from NCTE's program files.",
           "resources": resources}
    json.dump(pkg, open(os.path.join(out, "datapackage.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    with open(os.path.join(out, "DATA-DICTIONARY.md"), "w", encoding="utf-8") as f:
        f.write(f"# {TITLE}: data dictionary ({version})\n\n")
        for r in resources:
            f.write(f"## {r['name']} ({counts[r['name']]:,} rows)\n\n{r['description']}\n\n| Column | Type | Description |\n|---|---|---|\n")
            for fld in r["schema"]["fields"]:
                f.write(f"| `{fld['name']}` | {fld['type']} | {fld['description']} |\n")
            f.write("\n")

    covered = ", ".join(str(y) for y in years if y < 2004) + f", and {min(y for y in years if y >= 2004)}–{max(years)}"
    readme = README.format(title=TITLE, version=version, today=today, covered=covered, license=LICENSE, repo=REPO, contact=CONTACT,
                           sessions=counts["sessions"], appearances=counts["appearances"], people=counts["people"],
                           institutions=counts["institutions"], author=AUTHOR["name"])
    open(os.path.join(out, "README.md"), "w", encoding="utf-8").write(readme)
    open(os.path.join(out, "CITATION.cff"), "w", encoding="utf-8").write(CITATION.format(
        title=TITLE, version=version, today=today, license=LICENSE, orcid=AUTHOR["orcid"]))
    zen = {"title": f"{TITLE} ({version})", "upload_type": "dataset", "version": version, "publication_date": today,
           "creators": [AUTHOR], "license": "cc-by-4.0", "access_right": "open",
           "keywords": ["CCCC", "Conference on College Composition and Communication", "rhetoric and composition",
                        "writing studies", "conference programs", "two-year colleges"],
           "description": f"<p>Sessions and listed participants from CCCC convention programs ({covered}), parsed from NCTE's program files: {counts['sessions']:,} sessions and {counts['appearances']:,} listed appearances. Names, affiliations and titles are as printed; affiliations are matched to ROR and IPEDS. Counts are of people listed in the program, not attendees. Session descriptions are not included.</p>",
           "notes": "[TO DECIDE: NCTE notice or permission statement]",
           "related_identifiers": [{"identifier": "https://pinakes.wacclearinghouse.org", "relation": "isSupplementTo", "resource_type": "other"}]}
    json.dump(zen, open(os.path.join(out, "zenodo.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    shutil.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "DATA-LICENSE.txt"), os.path.join(out, "DATA-LICENSE.txt"))
    files = sorted(os.path.relpath(os.path.join(d, n), out).replace("\\", "/") for d, _, ns in os.walk(out) for n in ns)
    with open(os.path.join(out, "SHA256SUMS"), "w", encoding="utf-8", newline="\n") as f:
        for p in files:
            f.write(f"{sha(os.path.join(out, p))} *{p}\n")
    zpath = out + ".zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files + ["SHA256SUMS"]:
            z.write(os.path.join(out, p), f"cccc-program-corpus-{version}/{p}")
    print(f"release {version}: {counts} -> {out} ({os.path.getsize(zpath) / 1e6:.1f} MB zip)")

README = """# {title}

Version {version}, built {today}. Data license: CC BY 4.0 (`DATA-LICENSE.txt`); code license: MIT. Suggested credit: Lewis, Justin. *CCCC Convention Program Corpus.* {repo}

Sessions and listed participants from the programs of the Conference on College Composition and Communication (CCCC), the annual convention of CCCC, which is part of the National Council of Teachers of English (NCTE). This release covers {covered}: {sessions:,} sessions, {appearances:,} listed appearances, {people:,} name clusters and {institutions:,} matched institutions.

## Sources

- **1998:** the convention's web program, replayed from the Internet Archive's Wayback Machine.
- **1999:** the PDF program for the ten letter sections whose files survive in the Wayback Machine, plus every session title from the web program's session pages (sections E, F, K and M have titles only).
- **2004–2023:** NCTE's born-digital program PDFs.
- **2024–2027:** NCTE's eShow session listings, with paper titles copied from the 2024–2026 PDF programs. 2027 is the listing before the convention and will change.

1994–1997 survive online only as front pages, and 2000–2003 not at all; those years, and 1949–1993, need the printed programs. NCTE holds the rights to the programs themselves. This release contains facts drawn from them (who was listed, in which session, from which institution, under which title) and leaves out NCTE's session descriptions.

## What is in it

`data/` holds one CSV per table, and `cccc-program-corpus.sqlite` holds the same tables in one file. `DATA-DICTIONARY.md` and `datapackage.json` describe every column.

- `appearances` is the core table: one row per name per session, with the name, affiliation and paper title exactly as printed.
- `people` joins appearances across years. Names are joined only when they match exactly (after case, punctuation and accents are folded), plus any pairs a person has reviewed. Check `method` before counting careers.
- `institutions` and `affiliation_matches` link printed affiliations to ROR records and, for US colleges, to IPEDS, which says whether a college is two-year.

## Counting with care

- These are people **listed in the program**, not registrants or attendees.
- 2020 is the program of a convention that was cancelled. 2021 and 2022 were virtual.
- The source changes from PDF to eShow at 2024, so a step between 2023 and 2024 may come from the source.
- About 3% of appearances that print an affiliation have no matched institution: independent scholars, schools, publishers and a long tail.
- In the PDF years the parser finds listed names with precision 0.94–0.97 and recall 0.92–0.95, measured against eShow for 2024–2026, the years both exist.
- Where a program ran two presenters into one entry, the parser splits it at a common first name followed by an institution. A second person printed with no institution after the name stays merged.

## How it was built

The capture is a private WARC copy of NCTE's program files and eShow pages, made in October 2026. The parsing code (PyMuPDF for the PDFs, BeautifulSoup for eShow and the 1998 pages), the alias lists and the build script are in the project repository: {repo}

## Citation

{author}. *{title}*, version {version}. [TO DECIDE: Zenodo DOI]

## Corrections

Anyone listed can ask for a correction, a merge or a split of their name: {contact}
"""

CITATION = """cff-version: 1.2.0
message: "If you use this dataset, please cite it as below."
type: dataset
title: "{title}"
version: "{version}"
date-released: "{today}"
license: "{license}"
authors:
  - family-names: "Lewis"
    given-names: "Justin"
    affiliation: "Olympic College"
    orcid: "{orcid}"
"""

if __name__ == "__main__":
    main(*sys.argv[1:5])
