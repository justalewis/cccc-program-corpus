"""Build the public Datasette database from a release package.

Usage: python -I src/deploy_db.py <release_dir> <stats.json> <out.db>
Copies the release SQLite (no session descriptions, no eShow keys), then adds what the
web view needs: full-text search on titles, names and affiliations, indexes on the join
columns, and a year_summary table with the per-year counts and two-year share.
"""
import json, os, shutil, sqlite3, sys

FTS = {
    "sessions": ["title"],
    "appearances": ["name_as_printed", "affiliation_as_printed", "paper_title"],
    "institutions": ["name"],
}
INDEXES = [("appearances", "session_id"), ("appearances", "person_id"), ("appearances", "institution_id"),
           ("appearances", "year"), ("sessions", "year"), ("affiliation_matches", "institution_id")]

def main(release_dir, stats_path, out):
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    if os.path.exists(out):
        os.remove(out)
    shutil.copy(os.path.join(release_dir, "cccc-program-corpus.sqlite"), out)
    con = sqlite3.connect(out)
    for table, cols in FTS.items():
        con.execute(f"CREATE VIRTUAL TABLE {table}_fts USING fts5({', '.join(cols)}, content='{table}')")
        con.execute(f"INSERT INTO {table}_fts(rowid, {', '.join(cols)}) SELECT rowid, {', '.join(cols)} FROM {table}")
    for table, col in INDEXES:
        con.execute(f"CREATE INDEX ix_{table}_{col} ON {table}({col})")
    con.execute("""CREATE TABLE year_summary (year INTEGER PRIMARY KEY, city TEXT, status TEXT, sessions INTEGER,
                   listed_people INTEGER, people_with_affiliation INTEGER, people_matched INTEGER,
                   people_us_ipeds INTEGER, people_two_year INTEGER, two_year_share REAL)""")
    stats = json.load(open(stats_path, encoding="utf-8"))["years"]
    conv = {y: (c, s) for y, c, s in con.execute("SELECT year, city, status FROM conventions")}
    for y, s in sorted(stats.items(), key=lambda t: int(t[0])):
        if not s["sessions"]:
            continue
        share = round(s["people_two_year"] / s["people_us_ipeds"], 4) if s["people_us_ipeds"] else None
        con.execute("INSERT INTO year_summary VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (int(y), *conv.get(int(y), (None, None)), s["sessions"], s["people"], s["people_with_affiliation"],
                     s["people_matched"], s["people_us_ipeds"], s["people_two_year"], share))
    con.commit()
    con.execute("VACUUM")
    con.close()
    print(f"deploy db -> {out} ({os.path.getsize(out) / 1e6:.1f} MB)")

if __name__ == "__main__":
    main(*sys.argv[1:4])
