"""Resolve curated affiliation aliases to ROR records and link them.

Usage: python -I src/apply_aliases.py <db_path> <aliases.csv> <cache.jsonl>
For each alias, searches ROR (query=canonical name) and accepts a record only when its
display name or one of its aliases/labels equals the canonical name (case-insensitive,
dash variants folded), in the given country, and in the given city if one is named.
Anything ambiguous or unresolved is printed for a person to fix in the CSV.
"""
import csv, json, os, re, sqlite3, sys, time
import requests

API = "https://api.ror.org/v2/organizations"

def fold(s):
    s = s.lower().replace("–", "-").replace("—", "-").replace("’", "'").replace(",", "")
    return re.sub(r"\s*-\s*", "-", s).strip()

def names(org):
    return {fold(n["value"]) for n in org.get("names", [])}

def display(org):
    return next((n["value"] for n in org["names"] if "ror_display" in n["types"]), org["names"][0]["value"])

def main(db_path, aliases_csv, cache_path):
    sys.stdout.reconfigure(encoding="utf-8")
    con = sqlite3.connect(db_path)
    cache = {}
    if os.path.exists(cache_path):
        for line in open(cache_path, encoding="utf-8"):
            d = json.loads(line); cache[d["q"]] = d["items"]
    out = open(cache_path, "a", encoding="utf-8")
    ok, bad = 0, []
    for row in csv.DictReader(open(aliases_csv, encoding="utf-8")):
        canon = row["canonical"]
        if canon not in cache:
            r = requests.get(API, params={"query": canon}, headers={"User-Agent": "cccc-program-corpus/0.1"}, timeout=60)
            cache[canon] = r.json().get("items", [])[:20]
            out.write(json.dumps({"q": canon, "items": cache[canon]}) + "\n"); out.flush()
            time.sleep(0.3)
        hits = []
        for org in cache[canon]:
            loc = (org.get("locations") or [{}])[0].get("geonames_details", {})
            if fold(canon) in names(org) and (not row["country"] or loc.get("country_code") == row["country"]) \
               and (not row["city"] or loc.get("name") == row["city"]) and org.get("status") == "active":
                hits.append((org, loc))
        if len(hits) != 1:
            bad.append((row["affiliation"], canon, [display(h[0]) + " / " + h[1].get("name", "") for h in hits]))
            continue
        org, loc = hits[0]
        ror = org["id"].rsplit("/", 1)[-1]
        ext = {e["type"]: (e.get("preferred") or (e.get("all") or [None])[0]) for e in org.get("external_ids", [])}
        con.execute("INSERT OR IGNORE INTO institution(id, name, ror_id, wikidata, country, kind) VALUES (?,?,?,?,?,?)",
                    ("ror:" + ror, display(org), ror, ext.get("wikidata"), loc.get("country_code"), ",".join(org.get("types", []))))
        con.execute("UPDATE affiliation_match SET institution_id=?, method='alias' WHERE affiliation_as_printed=?", ("ror:" + ror, row["affiliation"]))
        ok += 1
    con.execute("UPDATE appearance SET institution_id = (SELECT institution_id FROM affiliation_match m WHERE m.affiliation_as_printed = appearance.affiliation_as_printed)")
    con.commit()
    print(f"aliases resolved: {ok}; need attention: {len(bad)}")
    for b in bad:
        print("  ", b)

if __name__ == "__main__":
    main(*sys.argv[1:4])
