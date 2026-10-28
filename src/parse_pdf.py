"""Rule-based parser for the born-digital CCCC program PDFs (1999, 2004-2026).

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
    1999: [f"99__program__{x}.pdf" for x in ("a", "b", "c", "d", "g", "h", "i", "j", "l", "n", "wed-workshops", "sat-workshops")],
    2004: ["2004__2004completeprogram.pdf"],
    2005: ["2005__2005completeprogram.pdf"],
    2006: ["2006__2006programwednesday.pdf", "2006__2006programthursday.pdf", "2006__2006programfriday.pdf", "2006__2006programsaturday.pdf"],
    2007: ["2007__2007completeprogram.pdf"],
    2008: ["2008__2008completeprogram.pdf"],  # found live 28 Oct 2026; the day files lacked Saturday
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

LOCATION = re.compile(r"\b(Room|Floor|Level|Ballroom|Salon|Hotel|Hilton|Hyatt|Marriott|Sheraton|Westin|Convention Center|Exhibit Hall|Wing|Online|Virtual)\b")
OPEN_END = re.compile(r"(:|,|;|[-–—]|\b(and|or|of|in|on|for|to|the|a|an|with|from|at|by|as|into|through|about|between))$", re.I)

def join_title(title, line):
    """Join a wrapped title line; a line ending in a hyphen ("Cross-") joins without a space."""
    return (title + ("" if title.endswith("-") else " ") + line).strip()

def title_continues(title):
    """A title that ends on a colon, comma or function word goes on to the next line."""
    return bool(OPEN_END.search(title.strip()))

LIGATURES = {"ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl"}

def lines_of(pdf_path):
    """Yield (page_no, bbox, text, size) for every text line, in reading order per page."""
    doc = pymupdf.open(pdf_path)
    for pno, page in enumerate(doc, 1):
        d = page.get_text("dict", sort=False)
        for block in d["blocks"]:
            for line in block.get("lines", []):
                text = "".join(s["text"] for s in line["spans"]).replace(" ", " ").replace("\t", " ")
                text = re.sub(r"\s+", " ", text).strip()
                # Some programs set "fi"/"fl" as ligatures followed by a stray space ("Sheffi eld").
                text = re.sub("([ﬀ-ﬄ]) ?", lambda m: LIGATURES[m.group(1)], text)
                # The 1999 PDFs expose curly quotes as Windows-1252 bytes (U+0093 for “).
                text = re.sub("[-]", lambda m: bytes([ord(m.group(0))]).decode("cp1252", "ignore"), text)
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
        # a hanging indent: same page, a few points right of where the entry starts
        hanging = pg == cur[0] and 3 < bb[0] - cur[1][0] < 30
        if hanging or open_quotes(joined) > 0 or joined.endswith((",", "-", "–", "/", "&", " and")) or t.startswith((QUOTES_OPEN, '"', "(")) \
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
        if len(title) > 260:  # an opening quote with no close: the "title" swallowed the prose after it
            title = None
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

FIRST_NAMES = {l.strip() for l in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "first_names.txt"), encoding="utf-8")
               if l.strip() and not l.startswith("#")}
INST_WORD = re.compile(r"\b(University|College|Institute|School|Academy|Universidad|Université)\b", re.I)

INLINE_ROLE = re.compile(r"\s*(?<![a-z])((?:Co-)?Chairs?|Speakers?|Respondents?|Presenters?|Panelists?|Facilitators?)\s*:\s*")
AND_END = re.compile(r"(,?\s*(and|&))+$")

def split_merged(name, aff, title):
    """Split an entry that holds two or more presenters, where the program set them on one line:
    "A, Univ X, City, B, Univ Y" or "A, Univ X, City B, Univ Y". A second name is two to four words
    starting with a common first name, ending a comma segment, with an institution right after it."""
    out, role = [], None
    while aff:
        # a role label the line break failed to separate: "..., Fredericksburg, VA Speakers: Tabetha Adkins, ..."
        lab = INLINE_ROLE.search(aff)
        if lab:
            head, rest = aff[:lab.start()].strip(" ,"), aff[lab.end():]
            q = parse_entry(rest)
            if q and plausible_name(q[0]):
                people = split_merged(name, head or None, None)
                tail = split_merged(q[0], q[1], title)
                return [(n, a, t, r) for n, a, t, r in people] + [(n, a, t, r or lab.group(1)) for n, a, t, r in tail]
        segs = [s.strip() for s in aff.split(",")]
        cut = None
        for i in range(1, len(segs) - 1):
            words = segs[i].split()
            for k in (4, 3, 2):  # longest first: "Mary Jo Reiff", not "Jo Reiff"
                if k > len(words):
                    continue
                cand = " ".join(words[-k:])
                if words[-k] in FIRST_NAMES and plausible_name(cand) and INST_WORD.search(segs[i + 1]):
                    cut = (i, len(words) - k, cand); break
            if cut:
                break
        if not cut:
            break
        i, keep, cand = cut
        first_aff = ", ".join(segs[:i] + ([" ".join(segs[i].split()[:keep])] if keep else []))
        out.append((name, AND_END.sub("", first_aff).strip() or None, role))
        name, aff = cand, ", ".join(segs[i + 1:])
    out.append((name, aff, role))
    # a repeated person in the same entry is a typesetting echo
    seen, people = set(), []
    for n, a, r in out:
        if (n, a) not in seen:
            seen.add((n, a)); people.append([n, a, None, r])
    people[-1][2] = title
    return [tuple(x) for x in people]

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
                    for name, aff, title, r in split_merged(*p):
                        cur["people"].append(dict(role=r or role, name=name, aff=aff, title=title, page=pg, bbox=bb))
        role_lines = []

    for idx, (pg, bb, t, size) in enumerate(all_lines):
        m = CODE.match(t)
        if m and len(t) < 200:
            flush_role(); role_size = None
            title = m.group(3).strip()
            cur = dict(code=f"{m.group(1)}.{int(m.group(2))}", title=title, page=pg, people=[],
                       title_open=not title or title_continues(title), title_size=size if title else None)
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
        # (a person entry nearly always has a comma before the affiliation; a label never does)
        if CODE.match(nxt) and not ROLE.match(t) and "," not in t and open_quotes(" ".join(x[2] for x in role_lines)) <= 0:
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
        elif cur["title_open"] and len(cur["title"]) < 300:
            if cur["title_size"] is None:  # the code stood alone; the title follows it
                cur["title"] = join_title(cur["title"], t)
                cur["title_size"] = size
                cur["title_open"] = not (len(t) < 45 or t.endswith((".", "?"))) or title_continues(t)
            elif abs(size - cur["title_size"]) <= 0.3 and not (LOCATION.search(t) and "," in t):
                # a subtitle after "Title:" in the title's own type size (not the room line)
                cur["title"] = join_title(cur["title"], t)
                cur["title_open"] = title_continues(t)
            else:
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
