"""Register of the groups that held meetings in CCCC's special-interest slots.

Usage: python -I src/build_groups.py <db_path> [data/group_aliases.csv]
group_aliases.csv (variant,canonical) joins two printed names that are one group, e.g. a misprinted "Council" for "Conference".
The programs schedule special interest groups, caucuses, standing groups and consortia in
their own slots (session codes FSIG, TSIG, WSIG, PSIG; from 2024 also the eShow type
"Special Interest Group/Business Meeting"). The session title is the group's name, with a
suffix that varies by year ("Black Caucus", "Black Caucus Business Meeting"). This strips the
suffixes, joins near-identical names across years, and writes:
  sgroup(id, name, kind, first_year, last_year, years, sessions)
  session.group_id
A slot is not always a standing group: some years put one-off topical discussions there, and
those become single-year entries. kind is read from the words in the titles.
"""
import collections, csv, difflib, os, re, sqlite3, sys, unicodedata

PREFIX = re.compile(r"^(?:ccc?c\s+)?(?:special interest group|sig)\s*(?:on|for|in|:|-)?\s*", re.I)
SUFFIX = re.compile(r"\s*[-:,(]?\s*(?:special interest group|sig|standing group|consortium|business meeting|annual meeting|"
                    r"annual business meeting|open meeting|meeting|business|canceled|cancelled|session)\b[\s)]*$", re.I)
PAREN = re.compile(r"\s*\([^)]*\)")

def clean_title(t):
    s = unicodedata.normalize("NFKC", t)
    s = re.sub(r"^(?:19|20)\d\d\s+", "", s.strip())  # a year typed in front of the name
    s = PAREN.sub("", s) if re.search(r"\((?:[A-Z]{2,}|[^)]*group[^)]*)\)\s*$", s) else s  # a trailing acronym: "(MRSG)"
    s = re.sub(r"\s+", " ", s).strip(" .,:;-")
    for _ in range(3):
        s = SUFFIX.sub("", s).strip(" .,:;-")
    s = PREFIX.sub("", s).strip(" .,:;-")
    s = re.sub(r"^meeting of (?:the )?", "", s, flags=re.I)
    return s

def key(t):
    s = PAREN.sub("", clean_title(t)).lower()
    s = re.sub(r"\b(the|of|and|for|on|in|a|an|at|cccc)\b", " ", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()

def kind_of(titles):
    blob = " | ".join(titles).lower()
    if re.search(r"\bcaucus\b", blob):
        return "caucus"
    if "standing group" in blob:
        return "standing group"
    if "consortium" in blob:
        return "consortium"
    if re.search(r"\bsig\b|special interest", blob):
        return "special interest group"
    return "interest-slot session"

def main(db_path, aliases_csv=None):
    con = sqlite3.connect(db_path)
    cols = [r[1] for r in con.execute("pragma table_info(session)")]
    if "group_id" not in cols:
        con.execute("ALTER TABLE session ADD COLUMN group_id TEXT")
    con.execute("UPDATE session SET group_id = NULL")
    con.execute("DROP TABLE IF EXISTS sgroup")
    con.execute("""CREATE TABLE sgroup (id TEXT PRIMARY KEY, name TEXT, kind TEXT, first_year INTEGER, last_year INTEGER,
                   years INTEGER, sessions INTEGER)""")
    rows = con.execute("""SELECT id, year, code, title, cancelled FROM session WHERE parent_id IS NULL AND title IS NOT NULL AND
                          (code LIKE '%SIG.%' OR session_type LIKE 'Special Interest Group%')""").fetchall()
    alias = {}
    if aliases_csv and os.path.exists(aliases_csv):
        alias = {key(r["variant"]): key(r["canonical"]) for r in csv.DictReader(open(aliases_csv, encoding="utf-8"))}
    keyed = [(sid, y, t, alias.get(key(t), key(t))) for sid, y, c, t, x in rows if key(t)]
    freq = collections.Counter(k for _, _, _, k in keyed)
    reps = []  # cluster representatives, most frequent first
    assign = {}
    for k, _ in freq.most_common():
        match = next((r for r in reps if k == r or difflib.SequenceMatcher(None, k, r).ratio() >= 0.9
                      or (len(k) > 12 and (k in r or r in k) and abs(len(k) - len(r)) <= 12)), None)
        if match is None:
            reps.append(k); match = k
        assign[k] = match
    clusters = collections.defaultdict(list)
    for sid, y, t, k in keyed:
        clusters[assign[k]].append((sid, y, t))
    n, used = 0, set()
    for rep, items in sorted(clusters.items(), key=lambda kv: -len(kv[1])):
        gid = "g" + re.sub(r"\s+", "-", rep)[:60]
        while gid in used:  # long names can truncate to the same id
            gid += "x"
        used.add(gid)
        names = collections.Counter(clean_title(t) for _, _, t in items)
        name = names.most_common(1)[0][0]
        years = sorted({y for _, y, _ in items})
        # a group's kind follows its latest wording (many SIGs became standing groups)
        latest = kind_of([t for _, y, t in items if y == years[-1]])
        kind = latest if latest != "interest-slot session" else kind_of([t for _, _, t in items])
        con.execute("INSERT OR REPLACE INTO sgroup VALUES (?,?,?,?,?,?,?)",
                    (gid, name, kind, years[0], years[-1], len(years), len(items)))
        con.executemany("UPDATE session SET group_id=? WHERE id=?", [(gid, sid) for sid, _, _ in items])
        n += 1
    con.commit()
    multi = con.execute("SELECT count(*) FROM sgroup WHERE years >= 2").fetchone()[0]
    kinds = dict(con.execute("SELECT kind, count(*) FROM sgroup WHERE years >= 2 GROUP BY 1").fetchall())
    print(f"groups: {len(rows)} slot sessions -> {n} names, {multi} in two or more years {kinds}")

if __name__ == "__main__":
    main(*sys.argv[1:3])
