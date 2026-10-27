"""Merge eShow session-detail captures into the database.

Usage: python -I src/parse_details.py <capture_dir> <db_path>
For each captured getDetails response: stores the session description, and uses the
detail view's separate name and company fields to correct the listing's comma split
(matched on the eShow person key within the session).
"""
import glob, os, re, sqlite3, sys
from urllib.parse import parse_qs
from bs4 import BeautifulSoup
from warcio.archiveiterator import ArchiveIterator

PERSON = re.compile(r"getSpeakerDetails\('([0-9A-F-]{36})'\)")

def clean(s):
    return re.sub(r"\s+", " ", (s or "").replace("\xa0", " ")).strip()

def pairs(capture_dir):
    """Yield (session_key, response_html) from the details WARC(s)."""
    for warc in sorted(glob.glob(os.path.join(capture_dir, "eshow-cccc-details-*.warc.gz"))):
        reqs, resps = {}, {}
        with open(warc, "rb") as f:
            for rec in ArchiveIterator(f):
                if rec.rec_type == "request":
                    body = rec.content_stream().read().decode("utf-8", "replace")
                    key = parse_qs(body).get("session_key", [None])[0]
                    reqs[rec.rec_headers.get_header("WARC-Concurrent-To")] = key
                elif rec.rec_type == "response":
                    resps[rec.rec_headers.get_header("WARC-Record-ID")] = rec.content_stream().read()
        for rid, body in resps.items():
            if reqs.get(rid):
                yield reqs[rid], body.decode("utf-8", "replace")

def main(capture_dir, db_path):
    con = sqlite3.connect(db_path)
    n_desc = n_fix = n = 0
    for key, html in pairs(capture_dir):
        n += 1
        soup = BeautifulSoup(html, "lxml")
        h4 = next((h for h in soup.find_all("h4") if clean(h.get_text()) == "Description"), None)
        desc = None
        if h4 and h4.parent:
            desc = clean(h4.parent.get_text()).removeprefix("Description").strip() or None
        if desc:
            con.execute("UPDATE session SET description=? WHERE eshow_key=?", (desc, key)); n_desc += 1
        for item in soup.select("div.speaker-flex-item"):
            nm = item.find("div", class_="speaker-info-name")
            co = item.find("div", class_="speaker-info-company")
            a = item.find("a", onclick=PERSON)
            if not (nm and a):
                continue
            pk = PERSON.search(a["onclick"]).group(1)
            cur = con.execute("""UPDATE appearance SET name_as_printed=?, affiliation_as_printed=?
                                 WHERE eshow_person_key=? AND session_id=? AND (name_as_printed<>? OR coalesce(affiliation_as_printed,'')<>?)""",
                              (clean(nm.get_text()), clean(co.get_text()) if co else None, pk, "eshow:" + key,
                               clean(nm.get_text()), clean(co.get_text()) if co else ""))
            n_fix += cur.rowcount
    con.commit()
    print(f"detail responses: {n}; descriptions stored: {n_desc}; name/affiliation splits corrected: {n_fix}")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
