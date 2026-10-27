"""Add IPEDS sector, level and Carnegie class to institutions; match leftover affiliations to IPEDS by name.

Usage: python -I src/enrich_ipeds.py <db_path> <HD2023.zip> <wikidata_ror_ipeds.csv>

two_year = 1 when IPEDS ICLEVEL is 2 (two-year) or the 2021 Carnegie Basic class is 1-14
(associate's colleges, special-focus two-year, and baccalaureate/associate's colleges that
mostly grant associate's degrees). That keeps community colleges that now offer a few
bachelor's degrees in the two-year count.
"""
import csv, io, re, sqlite3, sys, zipfile

def norm(s):
    s = s.lower().replace("&", "and")
    s = re.sub(r"^the\s+", "", s)
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def main(db_path, hd_zip, wd_csv):
    con = sqlite3.connect(db_path)
    z = zipfile.ZipFile(hd_zip)
    hd = {}
    by_name = {}
    with z.open(z.namelist()[0]) as f:
        for r in csv.DictReader(io.TextIOWrapper(f, encoding="latin-1")):
            r = {k.replace("ï»¿", "").replace("﻿", "").strip().upper(): v for k, v in r.items()}  # file starts with a BOM
            hd[r["UNITID"]] = r
            by_name.setdefault(norm(r["INSTNM"]), []).append(r["UNITID"])
    ror2ipeds = {}
    for r in csv.DictReader(open(wd_csv, encoding="utf-8")):
        ror2ipeds.setdefault(r["ror"], r["ipeds"])

    def fill(inst_id, unitid):
        r = hd.get(unitid)
        if not r:
            return False
        lvl, basic = int(r["ICLEVEL"] or 0), int(r["C21BASIC"] or 0)
        two = 1 if lvl == 2 or 1 <= basic <= 14 else 0
        con.execute("UPDATE institution SET ipeds_unitid=?, sector=?, iclevel=?, two_year=?, carnegie_basic=? WHERE id=?",
                    (unitid, int(r["SECTOR"] or 0), lvl, two, basic, inst_id))
        return True

    via_ror = 0
    for inst_id, ror in con.execute("select id, ror_id from institution where ror_id is not null").fetchall():
        if ror in ror2ipeds and fill(inst_id, ror2ipeds[ror]):
            via_ror += 1

    # US institutions that Wikidata doesn't map: exact normalized ROR name match to a single IPEDS institution
    for inst_id, name in con.execute("select id, name from institution where country='US' and ipeds_unitid is null").fetchall():
        hits = by_name.get(norm(name.replace("–", " ")), [])
        if len(hits) == 1 and fill(inst_id, hits[0]):
            via_ror += 1

    # Community college systems and districts that IPEDS splits by campus: two-year by definition.
    for name in ("Delaware Technical Community College", "Ivy Tech Community College of Indiana",
                 "San Diego Community College District", "St Louis Community College"):
        con.execute("UPDATE institution SET two_year=1, iclevel=2 WHERE name=? AND ipeds_unitid IS NULL", (name,))

    # leftover affiliation strings: exact normalized name match to a single IPEDS institution
    via_name = 0
    for (aff,) in con.execute("select affiliation_as_printed from affiliation_match where institution_id is null").fetchall():
        hits = by_name.get(norm(aff), [])
        if len(hits) == 1:
            u = hits[0]
            iid = "ipeds:" + u
            con.execute("INSERT OR IGNORE INTO institution(id, name, ipeds_unitid, country, kind) VALUES (?,?,?,?,?)",
                        (iid, hd[u]["INSTNM"], u, "US", "education"))
            fill(iid, u)
            con.execute("UPDATE affiliation_match SET institution_id=?, method='ipeds-exact-name' WHERE affiliation_as_printed=?", (iid, aff))
            via_name += 1
    con.execute("UPDATE appearance SET institution_id = (SELECT institution_id FROM affiliation_match m WHERE m.affiliation_as_printed = appearance.affiliation_as_printed)")
    con.commit()
    print(f"IPEDS via ROR->Wikidata: {via_ror}; leftover strings matched by exact IPEDS name: {via_name}")

if __name__ == "__main__":
    main(*sys.argv[1:4])
