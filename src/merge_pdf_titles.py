"""For years with an eShow listing, copy PDF paper titles onto the eShow appearances, then drop the PDF rows.

Usage: python -I src/merge_pdf_titles.py <db_path> <year> [<year> ...]
eShow stays the record of who was listed (it has person keys and a cleaner affiliation field);
the PDF contributes the per-speaker paper title, matched on session code and normalized name.
"""
import re, sqlite3, sys, unicodedata

def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower().replace(".", " ").replace("’", "'")
    return re.sub(r"\s+", " ", s).strip()

def code_norm(c):
    m = re.match(r"^([A-Z]{1,4})[.\-–]0*(\d+)", c or "")
    return f"{m.group(1)}.{int(m.group(2))}" if m else None

def main(db_path, *years):
    con = sqlite3.connect(db_path)
    for y in map(int, years):
        pdf = {}
        for code, name, title, page, bbox, doc in con.execute(
                """select s.code, a.name_as_printed, a.paper_title, a.page, a.bbox, a.source_document_id
                   from appearance a join session s on s.id = a.session_id where s.year=? and s.id like 'pdf:%'""", (y,)):
            pdf[(code_norm(code), norm(name))] = (title, page, bbox, doc)
        n = 0
        for aid, code, name in con.execute(
                """select a.id, s.code, a.name_as_printed from appearance a join session s on s.id = a.session_id
                   where s.year=? and s.id like 'eshow:%'""", (y,)).fetchall():
            hit = pdf.get((code_norm(code), norm(name)))
            if hit:
                con.execute("UPDATE appearance SET paper_title=?, page=?, bbox=? WHERE id=?", (hit[0], hit[1], hit[2], aid))
                n += hit[0] is not None
        con.execute("DELETE FROM appearance WHERE session_id IN (SELECT id FROM session WHERE year=? AND id LIKE 'pdf:%')", (y,))
        con.execute("DELETE FROM session WHERE year=? AND id LIKE 'pdf:%'", (y,))
        con.commit()
        print(f"{y}: paper titles copied to {n} eShow appearances; PDF rows removed")

if __name__ == "__main__":
    main(*sys.argv[1:])
