"""Parse captured eShow listing pages (2024-2027) into the corpus database.

Usage: python -I src/parse_eshow.py <capture_dir> <db_path>
Reads the eShow listing WARC from capture_dir, so every row traces to a captured copy.
"""
import glob, os, re, sqlite3, sys
from bs4 import BeautifulSoup
from warcio.archiveiterator import ArchiveIterator

HERE = os.path.dirname(os.path.abspath(__file__))
CONVENTIONS = [
    (2024, "Spokane, WA", "Spokane Convention Center", "held"),
    (2025, "Baltimore, MD", "Baltimore Convention Center", "held"),
    (2026, "Cleveland, OH", "Huntington Convention Center", "held"),
    (2027, "Milwaukee, WI", None, "upcoming"),
]
SUFFIX = re.compile(r"^(Jr\.?|Sr\.?|II|III|IV|PhD|Ph\.D\.|MFA|MA|EdD)$", re.I)
KEY = re.compile(r"getDetails\('([0-9A-F-]{36})'")
PERSON = re.compile(r"getSpeakerDetails\('([0-9A-F-]{36})'\)")

def clean(s):
    return re.sub(r"\s+", " ", (s or "").replace("\xa0", " ")).strip()

def split_name(s):
    """'Name, Affiliation' -> (name, affiliation). Keeps suffixes such as Jr. with the name."""
    parts = [p.strip() for p in s.split(",")]
    i = 1
    while i < len(parts) and SUFFIX.match(parts[i]):
        i += 1
    return ", ".join(parts[:i]), ", ".join(parts[i:]) or None

def speakers(container):
    """Walk role labels and speaker spans in document order, skipping nested child tables."""
    out, role = [], None
    for el in container.find_all(["p", "span"]):
        if el.find_parent("table", id="sess_table") and not container.name == "table":
            continue
        cls = el.get("class") or []
        if el.name == "p" and "session-speaker-name" in cls:
            role = clean(el.get_text()).rstrip(":") or None
        elif el.name == "span" and "session-speaker" in cls:
            out.extend(speaker(el, role))
    return out

def speaker(el, role):
    """One span.session-speaker -> [(role, name, affiliation, eshow person key)].
    2026 on, each speaker carries its own role span (Presenter:, Chair:, Respondent:)."""
    a = el.find("a")
    key = PERSON.search(a.get("onclick", "")) if a else None
    own = el.find("span", class_="session-speaker-role")
    name_el = el.find("span", class_="session-speaker-name")
    text = clean(name_el.get_text()) if name_el else ""
    if not text:
        return []
    name, aff = split_name(text)
    return [((clean(own.get_text()).rstrip(":") if own else role), name, aff, key.group(1) if key else None)]

TYPES = {"Individual 30-Minute Presentation", "Concurrent Panel", "Roundtable Session", "Special Interest Group/Business Meeting",
         "Combined Panel Presentation", "Standing Group-Sponsored Panel", "Engaged Learning Experience", "Poster", "Workshop",
         "Standing Group-Sponsored Workshop", "Committee Meeting", "Event", "Cross-Caucus Event", "Sponsored Workshop", "Session",
         "Open Rooms", "Livestream Session", "Registration/Exhibit Hall Hours", "General/Keynote Session", "Individual"}
LEVELS = {"Two-year", "Four-year", "Graduate level"}

def classify(chips):
    """eShow chips mix session type, (2024) audience level, and topic cluster, in no fixed order."""
    norm = [re.sub(r"^(Special Interest Group/Business Meeting):.*$", r"\1", c) for c in chips]
    types = [c for c in norm if c in TYPES]
    levels = [c for c in norm if c in LEVELS]
    rest = [c for c in norm if c not in TYPES and c not in LEVELS]
    return (types[0] if types else None), (" | ".join(levels) or None), (" | ".join(types[1:] + rest) or None)

def parse_listing(html, year):
    soup = BeautifulSoup(html, "lxml")
    sessions = {}
    for tr in soup.select("table#datatable tr[id^=tr-]"):
        title_span = tr.find("span", class_=re.compile(r"^session-title"))
        if not title_span:
            continue
        a = title_span.find("a")
        m = KEY.search(a.get("onclick", "")) if a else None
        if not m:
            continue
        key = m.group(1)
        date = clean(tr.find("span", class_="show_date_time").get_text()) if tr.find("span", class_="show_date_time") else None
        if key in sessions:
            if date and date not in sessions[key]["dates"]:
                sessions[key]["dates"].append(date)
            continue
        cell = tr.find("td", class_="session-divider-line")
        when = tr.find("span", class_="session-date")
        time_label = clean(when.get_text()).replace(date or "", "").strip() if when else None
        chips = [clean(c.get_text()) for c in cell.select("div.session-track-chip span.session-track-label")
                 if not c.find_parent("table", id="sess_table")]
        def label(cls):
            p = cell.find("p", class_=cls)
            return clean(p.get_text()).split(":", 1)[-1].strip() if p else None
        stype, level, tracks = classify(chips)
        s = dict(key=key, year=year, title=clean(a.get_text()), dates=[date] if date else [], time_label=time_label,
                 session_type=stype, audience_level=level, tracks=tracks,
                 room=label("session-location-label"), room_level=label("session-room_level-label"),
                 code=label("session-session_code2-label"),
                 cancelled=int("session-title-cancelled" in (title_span.get("class") or [])),
                 speakers=speakers(cell), children=[])
        for child in cell.select("table#sess_table span.schedule-session-child"):
            ca = child.find("a")
            cm = KEY.search(ca.get("onclick", "")) if ca else None
            if not cm:
                continue
            # speakers for this child are the session-speaker spans that follow it, up to the next child
            sp = []
            for sib in child.find_all_next(["span"]):
                cls = sib.get("class") or []
                if "schedule-session-child" in cls or not sib.find_parent("table", id="sess_table"):
                    break
                if "session-speaker" in cls:
                    sp.extend(speaker(sib, "Presenter"))
            s["children"].append(dict(key=cm.group(1), title=clean(ca.get_text()), speakers=sp))
        sessions[key] = s
    return sessions

def listings(capture_dir):
    for warc in sorted(glob.glob(os.path.join(capture_dir, "eshow-cccc-2024-2027-*.warc.gz"))):
        with open(warc, "rb") as f:
            for rec in ArchiveIterator(f):
                if rec.rec_type != "response":
                    continue
                url = rec.rec_headers.get_header("WARC-Target-URI")
                m = re.search(r"/cccc/(\d{4})/conference_program_sessions\.cfm$", url)
                if m:
                    yield int(m.group(1)), url, os.path.basename(warc), rec.rec_headers.get_header("WARC-Date"), rec.content_stream().read()

def main(capture_dir, db_path):
    con = sqlite3.connect(db_path)
    con.executescript(open(os.path.join(HERE, "schema.sql"), encoding="utf-8").read())
    for y, city, venue, status in CONVENTIONS:
        con.execute("INSERT OR REPLACE INTO convention(year, city, venue, status) VALUES (?,?,?,?)", (y, city, venue, status))
    import hashlib
    for year, url, warc, when, body in listings(capture_dir):
        doc = f"eshow-listing-{year}"
        con.execute("INSERT OR REPLACE INTO source_document VALUES (?,?,?,?,?,?,?,?)",
                    (doc, year, "eshow-listing", url, warc, hashlib.sha256(body).hexdigest(), when, "NCTE / eShow; private capture"))
        con.execute("DELETE FROM appearance WHERE source_document_id = ?", (doc,))
        con.execute("DELETE FROM session WHERE source_document_id = ?", (doc,))
        sessions = parse_listing(body.decode("utf-8", errors="replace"), year)
        n_app = 0
        for s in sessions.values():
            sid = "eshow:" + s["key"]
            con.execute("INSERT OR REPLACE INTO session(id, year, source_document_id, parent_id, code, title, session_type, audience_level, tracks, dates, time_label, room, room_level, cancelled, eshow_key) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (sid, year, doc, None, s["code"], s["title"], s["session_type"], s["audience_level"], s["tracks"], " | ".join(s["dates"]), s["time_label"], s["room"], s["room_level"], s["cancelled"], s["key"]))
            for i, (role, name, aff, pk) in enumerate(s["speakers"], 1):
                con.execute("INSERT INTO appearance(session_id, ord, role, name_as_printed, affiliation_as_printed, eshow_person_key, source_document_id) VALUES (?,?,?,?,?,?,?)",
                            (sid, i, role, name, aff, pk, doc)); n_app += 1
            for c in s["children"]:
                cid = "eshow:" + c["key"]
                con.execute("INSERT OR REPLACE INTO session(id, year, source_document_id, parent_id, title, session_type, eshow_key) VALUES (?,?,?,?,?,?,?)",
                            (cid, year, doc, sid, c["title"], "Presentation", c["key"]))
                for i, (role, name, aff, pk) in enumerate(c["speakers"], 1):
                    con.execute("INSERT INTO appearance(session_id, ord, role, name_as_printed, affiliation_as_printed, eshow_person_key, source_document_id) VALUES (?,?,?,?,?,?,?)",
                                (cid, i, role, name, aff, pk, doc))
        print(year, "sessions", len(sessions), "children", sum(len(s["children"]) for s in sessions.values()), "appearances (top-level)", n_app)
    con.commit()

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
