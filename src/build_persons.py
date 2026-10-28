"""Person clustering across all parsed years.

Usage: python -I src/build_persons.py <db_path> ["data/person_decisions*.csv"] ["data/name_merges*.csv"]
People are joined only on an exact normalized name (case, periods, extra spaces and accents
folded). No fuzzy merging. A cluster whose appearances name one institution, or none, is
method 'exact-name'. One that names several is sorted by its year-by-year pattern:
  'exact-name;moves'   one institution per year and never back to an earlier one, which
                       reads as one person changing jobs (A 2004-09, B 2012-19, C 2023);
  'exact-name;review'  two institutions in the same year, or a return to an earlier one,
                       where a namesake and a career are hard to tell apart.
University systems (University of California System, City University of New York) are
left out of the pattern, since programs print a campus one year and the system the next.
Each person_decisions*.csv file (person_id, decision, note) records a reviewer's calls:
'same' keeps it whole ('exact-name;reviewed-same'); 'different' splits it into one person
per institution ('exact-name;reviewed-split'), with institution-less appearances left on
the original id; anything else leaves it as it was.
Each name_merges*.csv file (a, b, decision, note), from the near-name page, joins two clusters
marked 'same' before any of the above; the result is method 'near-name-reviewed[;...]'.
"""
import csv, glob, hashlib, re, sqlite3, sys, unicodedata

def norm(name):
    s = unicodedata.normalize("NFKD", name)
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower().replace(".", " ")
    return re.sub(r"\s+", " ", s).strip()

def slug(name):
    """Cluster key: the folded name with punctuation dropped, so O'Brien and OBrien join."""
    key = norm(name)
    return re.sub(r"[^a-z0-9]+", "-", key).strip("-") or "h" + hashlib.sha1(key.encode()).hexdigest()[:10]

SYSTEM = re.compile(r"\bSystem\b|^(State|City) University of New York$")

def pattern(apps):
    """'single', 'moves' or 'review' for a cluster's (year, institution) pairs."""
    by_year = {}
    for y, inst in apps:
        if inst:
            by_year.setdefault(y, set()).add(inst)
    insts = set().union(*by_year.values()) if by_year else set()
    if len(insts) <= 1:
        return "single"
    if any(len(s) > 1 for s in by_year.values()):
        return "review"
    seq = [next(iter(by_year[y])) for y in sorted(by_year)]
    left = set()
    for prev, cur in zip(seq, seq[1:]):
        if cur != prev:
            left.add(prev)
            if cur in left:
                return "review"
    return "moves"

def apply_merges(clusters, merges_csv):
    """Join clusters a reviewer marked as one person on the near-name page (name_merges*.csv:
    a, b, decision). Returns the keys that absorbed another cluster. The merged cluster keeps
    the key of whichever part has more appearances."""
    parent = {}
    def find(k):
        while parent.get(k, k) != k:
            k = parent[k]
        return k
    for path in sorted(glob.glob(merges_csv)) if merges_csv else []:
        for r in csv.DictReader(open(path, encoding="utf-8-sig")):
            a, b = r["a"].removeprefix("p:"), r["b"].removeprefix("p:")
            if r["decision"].strip().lower() != "same" or "~" in a + b or a not in clusters or b not in clusters:
                continue  # split ids and names no longer in the corpus are skipped
            ra, rb = find(a), find(b)
            if ra != rb:
                if len(clusters[ra]) < len(clusters[rb]):
                    ra, rb = rb, ra
                parent[rb] = ra
                clusters[ra].extend(clusters.pop(rb))
    return {find(k) for k in parent}

def main(db_path, decisions_csv=None, merges_csv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    con = sqlite3.connect(db_path)
    con.execute("DELETE FROM person")
    decisions = {}
    for path in sorted(glob.glob(decisions_csv)) if decisions_csv else []:  # later files win
        decisions.update({r["person_id"]: r["decision"].strip().lower() for r in csv.DictReader(open(path, encoding="utf-8-sig"))})
    rows = con.execute("""select a.id, a.name_as_printed, a.institution_id, s.year, i.name
                          from appearance a join session s on s.id = a.session_id
                          left join institution i on i.id = a.institution_id""").fetchall()
    clusters, system = {}, set()
    for aid, name, inst, year, inst_name in rows:
        clusters.setdefault(slug(name), []).append((aid, name, inst, year))
        if inst_name and SYSTEM.search(inst_name):
            system.add(inst)
    merged = apply_merges(clusters, merges_csv)
    counts = {"single": 0, "moves": 0, "review": 0, "reviewed-same": 0, "reviewed-split": 0}

    def add(pid, apps, method):
        if pid.split("~")[0][2:] in merged:
            method = method.replace("exact-name", "near-name-reviewed", 1)
        display = max((n for _, n, _, _ in apps), key=lambda n: sum(1 for _, m, _, _ in apps if m == n))
        con.execute("INSERT INTO person(id, display_name, method) VALUES (?,?,?)", (pid, display, method))
        con.executemany("UPDATE appearance SET person_id=? WHERE id=?", [(pid, aid) for aid, _, _, _ in apps])

    for key, apps in clusters.items():
        pid = "p:" + key
        # a university system next to one of its campuses is not a second employer
        kind = pattern([(y, None if i in system else i) for _, _, i, y in apps])
        decision = decisions.get(pid) if kind != "single" else None
        if decision == "different":
            groups = {}
            for a in apps:
                groups.setdefault(a[2], []).append(a)
            for inst, part in groups.items():
                add(pid if inst is None else f"{pid}~{inst.split(':', 1)[-1]}", part, "exact-name;reviewed-split")
            counts["reviewed-split"] += 1
        elif decision == "same":
            add(pid, apps, "exact-name;reviewed-same")
            counts["reviewed-same"] += 1
        else:
            add(pid, apps, "exact-name" if kind == "single" else "exact-name;" + kind)
            counts[kind] += 1
    con.commit()
    print(f"near-name merges applied: {len(merged)} clusters absorbed others")
    print(f"persons: {len(clusters)} name clusters; one institution: {counts['single']}; "
          f"moves (one institution a year, no returns): {counts['moves']}; review: {counts['review']}; "
          f"reviewed same: {counts['reviewed-same']}; reviewed and split: {counts['reviewed-split']}")
    years = [y for (y,) in con.execute("select distinct year from session order by year")]
    seen = set()
    for y in years:
        ppl = {p for (p,) in con.execute("select distinct a.person_id from appearance a join session s on s.id=a.session_id where s.year=?", (y,))}
        if seen and ppl:
            print(f"{y}: {len(ppl)} people; {len(ppl & seen)} listed in an earlier year ({len(ppl & seen) / len(ppl):.0%})")
        seen |= ppl

if __name__ == "__main__":
    main(*sys.argv[1:4])
