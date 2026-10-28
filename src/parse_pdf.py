"""Rule-based parser for the born-digital CCCC program PDFs (2004-2026).

Usage: python -I src/parse_pdf.py <pdf_dir> <db_path> [year ...]
pdf_dir holds the PDFs extracted from the capture WARC (names as in SOURCES below).

A session starts at a line that begins with a session code (B.32, MW.6, C-7, F.06).
Inside a session, people are listed after role labels ("Chair:", "Speakers:", ...);
each entry is "Name, Affiliation[, City][, "Paper title"]" and may wrap across lines.
Every appearance records the PDF page and the bounding box of its first line.
"""
import os, re, sqlite3, sys
import pymupdf

SOURCES = {
    2004: ["2004__2004completeprogram.pdf"],
    2005: ["2005__2005completeprogram.pdf"],
    2006: ["2006__2006programwednesday.pdf", "2006__2006programthursday.pdf", "2006__2006programfriday.pdf", "2006__2006programsaturday.pdf"],
    2007: ["2007__2007completeprogram.pdf"],
    2008: ["2008__2008programwednesday.pdf", "2008__2008programthursday.pdf", "2008__2008programfriday.pdf"],
    2009: ["2009__2009completeprogram.pdf"],
    2010: ["2010__cccc2010-program.pdf"],
    2011: ["2011__program__entire-prog.pdf"],
    2012: ["2012__program__program2012.pdf"],
    2013: ["2013__program__program2013.pdf"],
    2014: ["2014__program__program.pdf"],
    2015: ["2015__program__wed.pdf", "2015__program__thurs.pdf", "2015__program__fri.pdf", "2015__program__sat.pdf"],
    2016: ["2016__program__2016program.pdf"],
    2017: ["2017__program__2017program.pdf"],
    2018: ["2018__program__program.pdf"],
    2019: ["2019__02__CCCC2019FullProgram.pdf"],
    2020: ["2020__02__2020CCCCFM.pdf", "2018__06__2020CCCCThurs.pdf", "2020__02__2020CCCCFri.pdf", "2020__02__2020CCCCSat.pdf"],
    2021: ["2021__04__2021-CCCC-program_4-15-21.pdf"],
    2022: ["2022__02__2022-CCCC-conv-A-M-sessions-2-21-22.pdf", "2022__03__2022-cccc-conv-Thurs-Sat-sessions-3-11-22.pdf", "2022__03__2022-cccc-conv-On-Demand-sessions-3-8-22.pdf"],
    2023: ["2023__01__2023-CCCC-Conv-revised-program2.pdf"],
    2024: ["2018__06__2024-CCCC-Conv-Program-final-3-24.pdf"],
    2025: ["2018__06__4Cs-2025-4-6.pdf"],
    2026: ["2018__06__2026-final-CCCC-program.pdf"],
}

CODE = re.compile(r"^([A-Z]{1,4})\s?[.\-–]\s?(\d{1,3})\b\s*(.*)$")
ROLE = re.compile(r"^((?:Co-)?Chairs?|Session Chairs?|Speakers?|Presenters?|Panelists?|Respondents?|Facilitators?|Moderators?|"
                  r"Roundtable Leaders?|Workshop Leaders?|Discussion Leaders?|Leaders?|Keynote Speakers?|Featured Speakers?|"
                  r"Workshop Facilitators?|Table Leaders?|Discussants?|Reviewers?|Introducers?|Hosts?|Organizers?)\s*:\s*(.*)$")
NOISE = re.compile(r"(\.indd\b|^\d{1,2}/\d{1,2}/\d{2,4}\s+\d|^CCCC CONVENTION|^\d{1,4}$|^\s*$|"
                   r"^(Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day,?\s+\d{1,2}(:\d\d)?\s*[–\-]|"
                   r"^(Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day,?\s+(\d{1,2}:\d\d|\d{1,2}\s*(a|p)\.m)|"
                   r"^(Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day,?\s+(March|April|Feb)|"
                   r"^Session [A-Z]{1,3}\b)")
SUFFIX = re.compile(r"^(Jr\.?|Sr\.?|II|III|IV)$")
QUOTES_OPEN, QUOTES_CLOSE = "“", "”"

def lines_of(pdf_path):
    """Yield (page_no, bbox, text, size) for every text line, in reading order per page."""
    doc = pymupdf.open(pdf_path)
    for pno, page in enumerate(doc, 1):
        d = page.get_text("dict", sort=False)
        for block in d["blocks"]:
            for line in block.get("lines", []):
                text = "".join(s["text"] for s in line["spans"]).replace(" ", " ").replace("\t", " ")
                text = re.sub(r"\s+", " ", text).strip()
                if text:
                    size = max((s["size"] for s in line["spans"] if s["text"].strip()), default=0)
                    yield pno, tuple(round(v, 1) for v in line["bbox"]), text, round(size, 1)

def open_quotes(s):
    return (s.count(QUOTES_OPEN) - s.count(QUOTES_CLOSE)) + (s.count('"') % 2)

def split_entries(lines):
    """Join wrapped lines into person entries. lines: [(page, bbox, text)]."""
    entries, cur = [], None
    for pg, bb, t in lines:
        if cur is None:
            cur = [pg, bb, t]; continue
        joined = cur[2]
        if open_quotes(joined) > 0 or joined.endswith((",", "-", "–", "/", "&", " and")) or t.startswith((QUOTES_OPEN, '"', "(")) \
           or (t[:1].islower()):
            if joined.endswith("-") and t[:1].islower() and joined[-2:-1].isalpha():
                joined = joined[:-1]  # a line-break hyphen: "Composi-" + "tion"
                cur[2] = (joined + t).strip()
            else:
                cur[2] = (joined + ("" if joined.endswith(("-", "/")) else " ") + t).strip()
        else:
            entries.append(cur); cur = [pg, bb, t]
    if cur:
        entries.append(cur)
    return entries

def parse_entry(text):
    title = None
    m = re.search(r"[“\"](.+?)[”\"]\s*$", text) or re.search(r"[“\"](.+)$", text)
    if m:
        title = m.group(1).strip().rstrip("”\"").strip()
        text = text[:m.start()].strip().rstrip(",").strip()
    parts = [p.strip() for p in text.split(",") if p.strip()]
    if not parts:
        return None
    i = 1
    while i < len(parts) and SUFFIX.match(parts[i]):
        i += 1
    name = ", ".join(parts[:i])
    aff = ", ".join(parts[i:]) or None
    return name, aff, title

NOT_NAME = re.compile(r"\d|:|;|\b(Room|Level|Ballroom|Hall|Sessions?|Center|Hotel|Press|Publishers?|Event|Network|Program|Workshops?|"
                      r"Conference|Convention|Statement|Committee|Caucus|Fellowship|Award|Online|Books?|Edition|Available|University|"
                      r"College|Writing|Rhetoric|Composition|Literacy|Teaching|Members?)\b")

def plausible_name(name):
    words = name.split()
    return (1 < len(words) <= 5 and name[:1].isupper() and not name.isupper()
            and not NOT_NAME.search(name) and not re.search(r"\b(and|the|of|in|for|with|this|you)\b", name))

def parse_pdf(path):
    sessions, cur, role, role_lines, role_size = [], None, None, [], None
    all_lines = [l for l in lines_of(path) if not NOISE.search(l[2])]

    def flush_role():
        nonlocal role_lines
        if cur is not None and role and role_lines:
            entries = split_entries(role_lines)
            if len(entries) > 40:  # a run this long is spill-over from ads or front matter
                entries = []
            for pg, bb, t in entries:
                p = parse_entry(t)
                if p and plausible_name(p[0]):
                    cur["people"].append(dict(role=role, name=p[0], aff=p[1], title=p[2], page=pg, bbox=bb))
        role_lines = []

    for idx, (pg, bb, t, size) in enumerate(all_lines):
        m = CODE.match(t)
        if m and len(t) < 200:
            flush_role(); role_size = None
            cur = dict(code=f"{m.group(1)}.{int(m.group(2))}", title=m.group(3).strip(), page=pg, people=[], title_open=not m.group(3).strip())
            sessions.append(cur); role = None
            continue
        if cur is None:
            continue
        # a line right before the next session code is a topic-cluster label, not a person
        nxt = all_lines[idx + 1][2] if idx + 1 < len(all_lines) else ""
        # leaving the session: type size changes, or an all-caps heading, or a run of prose
        if role and role_size and (abs(size - role_size) > 0.6 or (t.isupper() and len(t) > 12)):
            flush_role(); role = None; cur = None
            continue
        if CODE.match(nxt) and not ROLE.match(t) and open_quotes(" ".join(x[2] for x in role_lines)) <= 0:
            flush_role(); role = None
            continue
        r = ROLE.match(t)
        if r:
            flush_role()
            role = r.group(1); role_size = size
            if r.group(2):
                role_lines.append((pg, bb, r.group(2)))
            continue
        if role:
            role_lines.append((pg, bb, t))
        elif cur["title_open"] and len(cur["title"]) < 160:
            cur["title"] = (cur["title"] + " " + t).strip()
            if len(t) < 45 or t.endswith((".", "?")):
                cur["title_open"] = False
    flush_role()
    return sessions

def main(pdf_dir, db_path, *years):
    con = sqlite3.connect(db_path)
    con.executescript(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql"), encoding="utf-8").read())
    cols = [r[1] for r in con.execute("pragma table_info(appearance)")]
    for col in ("paper_title", "page", "bbox"):
        if col not in cols:
            con.execute(f"ALTER TABLE appearance ADD COLUMN {col} TEXT")
    targets = [int(y) for y in years] or sorted(SOURCES)
    for year in targets:
        con.execute("INSERT OR IGNORE INTO convention(year) VALUES (?)", (year,))
        n_s = n_p = 0
        seen_codes = set()
        for fname in SOURCES[year]:
            path = os.path.join(pdf_dir, fname)
            if not os.path.exists(path):
                print(f"  missing {fname}"); continue
            doc_id = f"pdf-{year}-{fname}"
            con.execute("DELETE FROM appearance WHERE source_document_id=?", (doc_id,))
            con.execute("DELETE FROM session WHERE source_document_id=?", (doc_id,))
            con.execute("INSERT OR REPLACE INTO source_document(id, year, kind, url, rights) VALUES (?,?,?,?,?)",
                        (doc_id, year, "pdf", fname, "NCTE; private capture"))
            for s in parse_pdf(path):
                if s["code"] in seen_codes or not s["people"]:
                    continue  # duplicate code (index pages, repeats) or no people listed
                seen_codes.add(s["code"])
                sid = f"pdf:{year}:{s['code']}"
                con.execute("INSERT OR REPLACE INTO session(id, year, source_document_id, code, title) VALUES (?,?,?,?,?)",
                            (sid, year, doc_id, s["code"], s["title"][:400] or None))
                for i, p in enumerate(s["people"], 1):
                    con.execute("""INSERT INTO appearance(session_id, ord, role, name_as_printed, affiliation_as_printed, paper_title, page, bbox, source_document_id)
                                   VALUES (?,?,?,?,?,?,?,?,?)""", (sid, i, p["role"], p["name"], p["aff"], p["title"], p["page"], str(p["bbox"]), doc_id))
                n_s += 1; n_p += len(s["people"])
        con.commit()
        print(f"{year}: sessions {n_s}, appearances {n_p}")

if __name__ == "__main__":
    main(*sys.argv[1:])
