"""Second enrichment pass: convention themes and chairs, folded roles, more IPEDS facts.

Usage: python -I src/enrich_more.py <db_path> <themes.csv> <HD2023.zip[,HD2008.zip]>
  convention.dates/theme/chair   from data/themes.csv (NCTE's past-conventions page)
  appearance.role_group          chair | speaker | respondent | facilitator | other
  institution.control/state/lat/lon/hbcu/tribal   from IPEDS HD, for institutions with a UNITID
"""
import csv, os, re, sqlite3, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python -I leaves it off
from enrich_ipeds import load_hd

def add_col(con, table, col, kind="TEXT"):
    if col not in [r[1] for r in con.execute(f"pragma table_info({table})")]:
        con.execute(f"ALTER TABLE {table} ADD COLUMN {col} {kind}")

def role_group(role):
    r = (role or "").lower()
    if "chair" in r or "moderator" in r:
        return "chair"
    if "respond" in r or "discussant" in r:
        return "respondent"
    if re.search(r"facilitat|leader|organizer", r):
        return "facilitator"
    if re.search(r"speaker|presenter|panelist|author", r):
        return "speaker"
    return "other"

def main(db_path, themes_csv, hd_zips):
    con = sqlite3.connect(db_path)
    for c in ("dates", "theme", "chair", "site"):
        add_col(con, "convention", c)
    n = 0
    for r in csv.DictReader(open(themes_csv, encoding="utf-8")):
        cur = con.execute("UPDATE convention SET dates=?, theme=?, chair=?, site=? WHERE year=?",
                          (r["dates"], r["theme"] or None, r["chair"] or None, r["site"], int(r["year"])))
        n += cur.rowcount
    add_col(con, "appearance", "role_group")
    groups = {}
    for (role,) in con.execute("SELECT DISTINCT role FROM appearance"):
        groups[role] = role_group(role)
    con.executemany("UPDATE appearance SET role_group=? WHERE role IS ?", [(g, r) for r, g in groups.items()])
    for c, k in (("control", "INTEGER"), ("state", "TEXT"), ("lat", "REAL"), ("lon", "REAL"), ("hbcu", "INTEGER"), ("tribal", "INTEGER")):
        add_col(con, "institution", c, k)
    hd, _ = load_hd(hd_zips)
    m = 0
    for iid, unit in con.execute("SELECT id, ipeds_unitid FROM institution WHERE ipeds_unitid IS NOT NULL").fetchall():
        r = hd.get(unit)
        if not r:
            continue
        def num(k):
            try:
                v = float(r.get(k) or "")
                return None if v in (-1.0, -2.0) else v
            except ValueError:
                return None
        con.execute("UPDATE institution SET control=?, state=?, lat=?, lon=?, hbcu=?, tribal=? WHERE id=?",
                    (int(r["CONTROL"] or 0) or None, r["STABBR"] or None, num("LATITUDE"), num("LONGITUD"),
                     1 if r.get("HBCU") == "1" else 0, 1 if r.get("TRIBAL") == "1" else 0, iid))
        m += 1
    con.commit()
    left = con.execute("SELECT count(*) FROM appearance WHERE role_group='other'").fetchone()[0]
    print(f"enrich_more: {n} conventions with dates/themes; roles folded ({len(groups)} spellings, {left} appearances left as other); IPEDS facts on {m} institutions")

if __name__ == "__main__":
    main(*sys.argv[1:4])
