"""Match printed affiliations to ROR with the ROR v2 affiliation endpoint.

Usage: python -I src/match_ror.py <db_path> <cache.jsonl>
Caches every API answer in cache.jsonl, so reruns only ask about new strings.
Accepts ROR's own 'chosen' result when the record's names share a word with the string
(ROR has "chosen" Hue University of Education for "Purdue University"); otherwise records the top candidate with its score
for review but does not link it. Writes affiliation_match and institution rows.
"""
import json, os, re, sqlite3, sys, time, unicodedata
import requests

API = "https://api.ror.org/v2/organizations"
UA = {"User-Agent": "cccc-program-corpus/0.1"}

def load_cache(path):
    cache = {}
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            d = json.loads(line)
            cache[d["q"]] = d["r"]
    return cache

def name_of(org):
    for n in org.get("names", []):
        if "ror_display" in n.get("types", []):
            return n["value"]
    return org.get("names", [{}])[0].get("value")

GENERIC = set("university college of the and at in state community school institute for de la del du des "
              "technology technical center centre campus city new".split())

def words(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower().replace("’", "").replace("'", "")
    return {w for w in re.findall(r"[a-z]+", s) if w not in GENERIC and len(w) > 2}

def shares_word(aff, org):
    """True when a distinctive word of the printed string starts a word in any of the ROR
    record's names, or the other way round (Penn / Pennsylvania)."""
    mine = words(aff)
    theirs = set().union(*(words(n["value"]) for n in org.get("names", []))) if org.get("names") else set()
    return any(a.startswith(b) or b.startswith(a) for a in mine for b in theirs if min(len(a), len(b)) >= 4) or bool(mine & theirs)

def main(db_path, cache_path):
    sys.stdout.reconfigure(encoding="utf-8")
    con = sqlite3.connect(db_path)
    affs = [a for (a,) in con.execute("select distinct affiliation_as_printed from appearance where affiliation_as_printed is not null")]
    cache = load_cache(cache_path)
    todo = [a for a in affs if a not in cache]
    print(f"{len(affs)} distinct affiliations; {len(todo)} to query")
    with open(cache_path, "a", encoding="utf-8") as out:
        for i, a in enumerate(todo, 1):
            for attempt in range(4):
                try:
                    r = requests.get(API, params={"affiliation": a}, headers=UA, timeout=60)
                    if r.status_code == 429:
                        time.sleep(60); continue
                    r.raise_for_status()
                    items = r.json().get("items", [])[:3]
                    cache[a] = [{"chosen": it.get("chosen"), "score": it.get("score"), "org": it["organization"]} for it in items]
                    out.write(json.dumps({"q": a, "r": cache[a]}) + "\n"); out.flush()
                    break
                except Exception as e:
                    time.sleep(5 * (attempt + 1))
            time.sleep(0.25)
            if i % 200 == 0:
                print(f"  {i}/{len(todo)}", flush=True)
    con.execute("DELETE FROM affiliation_match")
    chosen = refused = 0
    for a in affs:
        res = cache.get(a) or []
        top = res[0] if res else None
        if top and top["chosen"] and not shares_word(a, top["org"]):
            # ROR "chose" a record whose names share no word with the string
            # ("Purdue University" -> Hue University of Education); leave it for an alias.
            con.execute("INSERT INTO affiliation_match VALUES (?,?,?,?)", (a, None, "ror-chosen-refused:" + top["org"]["id"].rsplit("/", 1)[-1], top["score"]))
            refused += 1
        elif top and top["chosen"]:
            org = top["org"]
            ror = org["id"].rsplit("/", 1)[-1]
            ext = {e["type"]: (e.get("preferred") or (e.get("all") or [None])[0]) for e in org.get("external_ids", [])}
            loc = (org.get("locations") or [{}])[0].get("geonames_details", {})
            con.execute("INSERT OR IGNORE INTO institution(id, name, ror_id, wikidata, country, kind) VALUES (?,?,?,?,?,?)",
                        ("ror:" + ror, name_of(org), ror, ext.get("wikidata"), loc.get("country_code"), ",".join(org.get("types", []))))
            con.execute("INSERT INTO affiliation_match VALUES (?,?,?,?)", (a, "ror:" + ror, "ror-affiliation-chosen", top["score"]))
            chosen += 1
        else:
            con.execute("INSERT INTO affiliation_match VALUES (?,?,?,?)", (a, None, "ror-affiliation-top:" + (top["org"]["id"].rsplit("/", 1)[-1] if top else "none"), top["score"] if top else None))
    con.execute("UPDATE appearance SET institution_id = (SELECT institution_id FROM affiliation_match m WHERE m.affiliation_as_printed = appearance.affiliation_as_printed)")
    con.commit()
    print(f"chosen matches: {chosen} of {len(affs)} affiliation strings; refused (no shared word): {refused}")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
