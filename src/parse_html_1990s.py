"""Parse the 1998 HTML program and the 1999 session-title pages from the Wayback capture.

Usage: python -I src/parse_html_1990s.py <capture_dir> <db_path>
1998: www.ncte.org/cccc/98/program/{aa..nn}.htm and the b/c/d.html variants. Each session
is a table row: the code in the first cell; in the second, the title in bold, the room in
italics, then one <P> per person ("Chair: Name, Affiliation" or "Name, Affiliation,
"Paper title""). Where several files print the same code, the one listing the most people
is kept.
1999: the program PDFs (parse_pdf.py) survive for only 10 of the 14 letter sections. The
session pages www.ncte.org/cccc/99/session{a..n}.htm list every code and title, so the
sessions missing from the PDFs are added here with their titles and no people.
"""
import glob, hashlib, html, os, re, sqlite3, sys
from warcio.archiveiterator import ArchiveIterator
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python -I leaves it off
from parse_pdf import ROLE, parse_entry, plausible_name

CODE_IN = re.compile(r"\b([A-Z]{1,4})\s*\.\s*(\d{1,3})\b")
ENTRY_SPLIT = re.compile(r"<p\b[^>]*>|<br\s*/?>\s*<br\s*/?>", re.I)

def text(fragment):
    t = re.sub(r"<br\s*/?>", " ", fragment, flags=re.I)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", t).strip()

def pages(capture_dir):
    """Yield (url, decoded html, sha256) for the 1998 program and 1999 session pages."""
    want = re.compile(r"/cccc/(98/program/[a-z]+\.html?|99/session[a-n]\.htm)$")
    for warc in glob.glob(os.path.join(capture_dir, "wayback-cccc-*.warc.gz")):
        with open(warc, "rb") as f:
            for rec in ArchiveIterator(f):
                if rec.rec_type != "response" or rec.http_headers.get_statuscode() != "200":
                    continue
                url = rec.rec_headers.get_header("WARC-Target-URI")
                if want.search(url):
                    body = rec.content_stream().read()
                    yield url, body.decode("latin-1"), hashlib.sha256(body).hexdigest()

def parse_1998(page):
    sessions = []
    for row in re.findall(r"<tr\b.*?(?=<tr\b|</table>)", page, flags=re.I | re.S):
        cells = re.findall(r"<td\b[^>]*>(.*?)(?=<td\b|</tr>|$)", row, flags=re.I | re.S)
        if len(cells) < 2:
            continue
        # the first cell can also hold a time and a label ("11:15 a.m. ... HI.12 Special Interest Group")
        m = CODE_IN.search(text(cells[0]))
        if not m:
            continue
        b = re.search(r"<b>(.*?)</b>", cells[1], flags=re.I | re.S)
        title = text(b.group(1)) if b else ""
        # drop the bold title and the italic room line, then split people on <P> or a blank line
        body = re.sub(r"<i>.*?</i>", " ", cells[1][b.end():] if b else cells[1], count=1, flags=re.I | re.S)
        people, role = [], "Speaker"
        for chunk in ENTRY_SPLIT.split(body):
            t = text(chunk)
            if not t:
                continue
            r = ROLE.match(t)
            if r:
                role, t = r.group(1), r.group(2)
            p = parse_entry(t.replace('""', '"'))
            if p and plausible_name(p[0]):
                people.append(dict(role=role, name=p[0], aff=p[1], title=p[2]))
            if r and role.lower().startswith(("chair", "co-chair")):
                role = "Speaker"  # the people after a chair line are speakers unless labeled
        sessions.append(dict(code=f"{m.group(1)}.{int(m.group(2))}", title=title, people=people))
    return sessions

def parse_1999_titles(page):
    out = []
    for line in re.split(r"<td\b[^>]*>|<br\s*/?>|<p\b[^>]*>", page, flags=re.I):
        t = text(line)
        m = re.match(r"^([A-Z]{1,2})\.(\d{1,3})\s+(.+)$", t)
        if m:
            out.append((f"{m.group(1)}.{int(m.group(2))}", m.group(3).strip()))
    return out

def main(capture_dir, db_path):
    sys.stdout.reconfigure(encoding="utf-8")
    con = sqlite3.connect(db_path)
    best, titles99, docs = {}, {}, {}
    for url, page, sha in pages(capture_dir):
        path = url.split("/cccc/")[-1]
        doc_id = "wayback-" + path.replace("/", "-")
        docs[doc_id] = (int("19" + path[:2]), url, sha)
        if path.startswith("98/"):
            for s in parse_1998(page):
                if s["code"] not in best or len(s["people"]) > len(best[s["code"]][0]["people"]):
                    best[s["code"]] = (s, doc_id)
        else:
            for code, title in parse_1999_titles(page):
                titles99.setdefault(code, (title, doc_id))
    for doc_id, (year, url, sha) in docs.items():
        con.execute("INSERT OR REPLACE INTO source_document(id, year, kind, url, sha256, rights) VALUES (?,?,?,?,?,?)",
                    (doc_id, year, "html", url, sha, "NCTE; Wayback Machine replay, private capture"))
    con.execute("DELETE FROM appearance WHERE session_id LIKE 'html:%'")
    con.execute("DELETE FROM session WHERE id LIKE 'html:%'")
    n_p = 0
    for code, (s, doc_id) in sorted(best.items()):
        if not s["people"]:
            continue
        sid = f"html:1998:{code}"
        con.execute("INSERT INTO session(id, year, source_document_id, code, title) VALUES (?,?,?,?,?)",
                    (sid, 1998, doc_id, code, s["title"]))
        for i, p in enumerate(s["people"], 1):
            con.execute("""INSERT INTO appearance(session_id, ord, role, name_as_printed, affiliation_as_printed, paper_title, source_document_id)
                           VALUES (?,?,?,?,?,?,?)""", (sid, i, p["role"], p["name"], p["aff"], p["title"], doc_id))
        n_p += len(s["people"])
    have99 = {c for (c,) in con.execute("SELECT code FROM session WHERE year=1999")}
    added = 0
    for code, (title, doc_id) in sorted(titles99.items()):
        if code not in have99:
            con.execute("INSERT INTO session(id, year, source_document_id, code, title) VALUES (?,?,?,?,?)",
                        (f"html:1999:{code}", 1999, doc_id, code, title))
            added += 1
    con.commit()
    print(f"1998: sessions {sum(1 for s, _ in best.values() if s['people'])}, appearances {n_p}")
    print(f"1999: {len(titles99)} session titles on the HTML pages; {added} sessions added that the surviving PDFs lack (titles only)")

if __name__ == "__main__":
    main(*sys.argv[1:3])
