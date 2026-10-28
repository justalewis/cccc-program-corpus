"""Pilot summary: per-year counts of sessions, listed people, institutions, and two-year share.

Usage: python -I src/stats.py <db_path> <out.json>
Counts people by person id within a year (names joined on an exact match plus reviewed pairs). Counts are of
people LISTED in the program, not registrants or attendees.
"""
import json, sqlite3, sys

Q = {
    "sessions": "select count(*) from session where year=? and parent_id is null and coalesce(session_type,'') not in ('Registration/Exhibit Hall Hours','Open Rooms','Committee Meeting','Event')",
    "child_presentations": "select count(*) from session where year=? and parent_id is not null",
    "appearances": "select count(*) from appearance a join session s on s.id=a.session_id where s.year=? and s.parent_id is null",
    "people": "select count(distinct coalesce(person_id, eshow_person_key, name_as_printed)) from appearance a join session s on s.id=a.session_id where s.year=?",
    "people_with_affiliation": "select count(distinct coalesce(person_id, eshow_person_key, name_as_printed)) from appearance a join session s on s.id=a.session_id where s.year=? and affiliation_as_printed is not null",
    "people_matched": "select count(distinct coalesce(person_id, eshow_person_key, name_as_printed)) from appearance a join session s on s.id=a.session_id where s.year=? and a.institution_id is not null",
    "people_us_ipeds": "select count(distinct coalesce(person_id, eshow_person_key, name_as_printed)) from appearance a join session s on s.id=a.session_id join institution i on i.id=a.institution_id where s.year=? and (i.ipeds_unitid is not null or i.two_year is not null)",
    "people_two_year": "select count(distinct coalesce(person_id, eshow_person_key, name_as_printed)) from appearance a join session s on s.id=a.session_id join institution i on i.id=a.institution_id where s.year=? and i.two_year=1",
    "institutions": "select count(distinct a.institution_id) from appearance a join session s on s.id=a.session_id where s.year=?",
    "two_year_institutions": "select count(distinct a.institution_id) from appearance a join session s on s.id=a.session_id join institution i on i.id=a.institution_id where s.year=? and i.two_year=1",
}

def main(db_path, out):
    sys.stdout.reconfigure(encoding="utf-8")
    con = sqlite3.connect(db_path)
    years = [y for (y,) in con.execute("select distinct year from session order by year")]
    res = {}
    for y in years:
        r = {k: con.execute(q, (y,)).fetchone()[0] for k, q in Q.items()}
        r["two_year_share_of_ipeds_matched"] = round(r["people_two_year"] / r["people_us_ipeds"], 3) if r["people_us_ipeds"] else None
        r["types"] = dict(con.execute("select coalesce(session_type,'(none)'), count(*) from session where year=? and parent_id is null group by 1 order by 2 desc", (y,)).fetchall())
        res[y] = r
        print(y, {k: v for k, v in r.items() if k != "types"})
    top = con.execute("""select i.name, count(distinct coalesce(a.person_id, a.eshow_person_key, a.name_as_printed)) n from appearance a join institution i on i.id=a.institution_id
                         where i.two_year=1 group by i.id order by n desc limit 15""").fetchall()
    unmatched = con.execute("""select affiliation_as_printed, count(*) n from appearance where institution_id is null and affiliation_as_printed is not null
                               group by 1 order by n desc limit 40""").fetchall()
    json.dump({"years": res, "top_two_year": top, "top_unmatched": unmatched}, open(out, "w", encoding="utf-8"), indent=1)
    print("top two-year:", top[:8])
    print("top unmatched:", unmatched[:20])

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
