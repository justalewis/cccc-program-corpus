"""Load suggested and reviewed paper-to-article links into the link table.

Usage: python -I src/build_links.py <corpus.db> <suggestions.csv> ["data/link_decisions*.csv"]
Every tier A, B and C suggestion from link_pinakes.py becomes a row in link:
  target  'pinakes:<id>'      method  'title-author-<tier>'      score  the title overlap
  status  confirmed  a reviewer chose "Same work"
          rejected   a reviewer chose "Different" (kept, so a rebuild does not suggest it again)
          suggested  not reviewed, or "Not sure"
Tier D is not stored. Later decision files win over earlier ones. The summary prints how often
each tier was judged right among the pairs that have been reviewed.
"""
import collections, csv, glob, sqlite3, sys

def main(db_path, suggestions, decisions_glob="data/link_decisions*.csv"):
    con = sqlite3.connect(db_path)
    con.execute("""CREATE TABLE IF NOT EXISTS link (id INTEGER PRIMARY KEY, session_id TEXT, person_id TEXT, target TEXT,
                   method TEXT, score REAL, status TEXT CHECK (status IN ('suggested', 'confirmed', 'rejected')))""")
    con.execute("DELETE FROM link")
    decided = {}
    for path in sorted(glob.glob(decisions_glob)):
        for r in csv.DictReader(open(path, encoding="utf-8-sig")):
            decided[(r["session_id"], r["person_id"], r["pinakes_id"])] = r["decision"].strip().lower()
    stats = collections.defaultdict(collections.Counter)
    n = 0
    for r in csv.DictReader(open(suggestions, encoding="utf-8")):
        if r["tier"] == "D":
            continue
        key = (r["session_id"], r["person_id"], r["pinakes_id"])
        d = decided.get(key)
        status = {"match": "confirmed", "different": "rejected"}.get(d, "suggested")
        if d:
            stats[r["tier"]][d] += 1
        con.execute("INSERT INTO link(session_id, person_id, target, method, score, status) VALUES (?,?,?,?,?,?)",
                    (r["session_id"], r["person_id"], f"pinakes:{r['pinakes_id']}", f"title-author-{r['tier']}", float(r["title_overlap"]), status))
        n += 1
    con.commit()
    by = dict(con.execute("SELECT status, count(*) FROM link GROUP BY 1").fetchall())
    print(f"links: {n} stored {by}")
    for t in "ABC":
        c = stats[t]
        if c:
            judged = c["match"] + c["different"]
            share = f"{100 * c['match'] / judged:.0f}% judged the same work" if judged else "none judged yet"
            print(f"  tier {t}: {sum(c.values())} reviewed ({c['match']} same, {c['different']} different, {c['unsure']} not sure); {share}")

if __name__ == "__main__":
    main(*sys.argv[1:4])
