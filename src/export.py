"""Write CSV exports of the public-safe tables (session descriptions and eShow keys left out).

Usage: python -I src/export.py <db_path> <out_dir>
"""
import csv, os, sqlite3, sys

TABLES = {
    "conventions": "select * from convention order by year",
    "sessions": "select id, year, source_document_id, parent_id, code, title, session_type, audience_level, tracks, area, area_group, topic_tags, dates, time_label, room, cancelled from session order by year, code, id",
    "appearances": """select a.id, s.year, a.session_id, a.ord, a.role, a.role_group, a.name_as_printed, a.affiliation_as_printed, a.paper_title,
                      a.person_id, a.institution_id, a.source_document_id, a.page
                      from appearance a join session s on s.id = a.session_id order by s.year, a.session_id, a.ord""",
    "people": "select id, display_name, method from person order by id",
    "source_documents": "select id, year, kind, url, rights from source_document order by year, id",
    "institutions": "select * from institution order by name",
    "affiliation_matches": "select * from affiliation_match order by affiliation_as_printed",
}

def main(db_path, out):
    os.makedirs(out, exist_ok=True)
    con = sqlite3.connect(db_path)
    for name, q in TABLES.items():
        cur = con.execute(q)
        with open(os.path.join(out, name + ".csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([d[0] for d in cur.description])
            n = 0
            for row in cur:
                w.writerow(row); n += 1
        print(f"{name}: {n} rows")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
