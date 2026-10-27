"""First-pass person clustering for the eShow years.

Usage: python -I src/build_persons.py <db_path>
Within a year, one eShow person key is one person. Across years, people are joined only on
an exact normalized name (case, periods, extra spaces and accents folded). Clusters whose
appearances name more than one institution are marked method='exact-name;review' because
that is where a career move and a namesake look the same. No fuzzy merging here.
"""
import re, sqlite3, sys, unicodedata

def norm(name):
    s = unicodedata.normalize("NFKD", name)
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower().replace(".", " ")
    return re.sub(r"\s+", " ", s).strip()

def main(db_path):
    con = sqlite3.connect(db_path)
    con.execute("DELETE FROM person")
    rows = con.execute("select a.id, a.name_as_printed, a.institution_id from appearance a").fetchall()
    clusters = {}
    for aid, name, inst in rows:
        clusters.setdefault(norm(name), []).append((aid, name, inst))
    review = 0
    for key, apps in clusters.items():
        pid = "p:" + re.sub(r"[^a-z0-9]+", "-", key).strip("-")
        insts = {i for _, _, i in apps if i}
        method = "exact-name" + (";review" if len(insts) > 1 else "")
        review += len(insts) > 1
        display = max((n for _, n, _ in apps), key=lambda n: sum(1 for _, m, _ in apps if m == n))
        con.execute("INSERT INTO person(id, display_name, method) VALUES (?,?,?)", (pid, display, method))
        con.executemany("UPDATE appearance SET person_id=? WHERE id=?", [(pid, aid) for aid, _, _ in apps])
    con.commit()
    print(f"persons: {len(clusters)}; flagged for review (more than one institution): {review}")
    years = [y for (y,) in con.execute("select distinct year from session order by year")]
    seen = set()
    for y in years:
        ppl = {p for (p,) in con.execute("select distinct a.person_id from appearance a join session s on s.id=a.session_id where s.year=?", (y,))}
        if seen:
            print(f"{y}: {len(ppl)} people; {len(ppl & seen)} listed in an earlier eShow year ({len(ppl & seen) / len(ppl):.0%})")
        seen |= ppl

if __name__ == "__main__":
    main(sys.argv[1])
