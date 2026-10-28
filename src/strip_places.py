"""Match affiliations printed with a city or state ("Old Dominion University, Norfolk, VA").

Usage: python -I src/strip_places.py <db_path> <HD2023.zip[,HD2008.zip]>
Runs after enrich_ipeds.
The 2004-2018 programs print the place after the institution. For each still-unmatched
string, tries shorter and rejoined forms and accepts the first that equals (case, commas
and dash spacing folded) an institution's ROR name, a curated alias or an IPEDS name. University
systems are never targets, and every segment dropped must name the institution's own
ROR city, state or country. Forms that keep the city come first, so "University of North
Carolina, Chapel Hill" becomes "University of North Carolina at Chapel Hill" before it
could fall back to the bare system name. Nothing is looked up online.
"""
import glob, json, os, re, sqlite3, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python -I leaves it off
from enrich_ipeds import fill_ipeds, load_hd

SYSTEM = re.compile(r"\bSystem\b|^(State|City) University of New York$")

def fold(s):
    s = s.lower().replace("–", "-").replace("—", "-").replace("’", "'").replace(",", "").replace(".", "")
    s = re.sub(r"^the ", "", s)
    return re.sub(r"\s+", " ", re.sub(r"\s*-\s*", "-", s)).strip()

STATES = {"AL":"Alabama","AK":"Alaska","AZ":"Arizona","AR":"Arkansas","CA":"California","CO":"Colorado","CT":"Connecticut",
    "DE":"Delaware","DC":"District of Columbia","FL":"Florida","GA":"Georgia","HI":"Hawaii","ID":"Idaho","IL":"Illinois",
    "IN":"Indiana","IA":"Iowa","KS":"Kansas","KY":"Kentucky","LA":"Louisiana","ME":"Maine","MD":"Maryland","MA":"Massachusetts",
    "MI":"Michigan","MN":"Minnesota","MS":"Mississippi","MO":"Missouri","MT":"Montana","NE":"Nebraska","NV":"Nevada",
    "NH":"New Hampshire","NJ":"New Jersey","NM":"New Mexico","NY":"New York","NC":"North Carolina","ND":"North Dakota",
    "OH":"Ohio","OK":"Oklahoma","OR":"Oregon","PA":"Pennsylvania","RI":"Rhode Island","SC":"South Carolina","SD":"South Dakota",
    "TN":"Tennessee","TX":"Texas","UT":"Utah","VT":"Vermont","VA":"Virginia","WA":"Washington","WV":"West Virginia",
    "WI":"Wisconsin","WY":"Wyoming","PR":"Puerto Rico"}
NYC = {"queens", "jamaica", "brooklyn", "bronx", "the bronx", "manhattan", "staten island", "new york city", "new york"}

def locations(data_dir):
    """ROR id -> (city, subdivision name, country name) from the cached ROR responses."""
    loc = {}
    for path in glob.glob(os.path.join(data_dir, "ror*cache.jsonl")):
        for line in open(path, encoding="utf-8"):
            d = json.loads(line)
            for it in d.get("r") or d.get("items") or []:
                org = it.get("org", it)
                g = ((org.get("locations") or [{}])[0]).get("geonames_details", {})
                loc["ror:" + org["id"].rsplit("/", 1)[-1]] = (g.get("name", ""), g.get("country_subdivision_name", ""), g.get("country_name", ""))
    return loc

def is_place(seg, where):
    """True when a dropped segment names the institution's own city, state or country."""
    city, region, country = (fold(x) for x in where)
    f = fold(seg)
    if f.upper() in STATES:
        f = fold(STATES[f.upper()])
    if f in (city, region, country) or (f == "usa" and country == "united states"):
        return True
    return f in NYC and city in NYC

def candidates(aff):
    if "," not in aff and re.search(r"\s?[-–]\s?", aff):     # "University of North Carolina-Greensboro"
        aff = re.sub(r"\s?[-–]\s?(?=[^-–]*$)", ", ", aff)
    parts = [p.strip() for p in aff.split(",") if p.strip()]
    out = []
    for k in range(len(parts) - 1, 0, -1):          # keep k segments
        head, place = parts[:k], parts[k:]
        if k == 1 and place:
            city = place[0]
            out += [(f"{head[0]} {j} {city}".replace("  ", " "), place[1:]) for j in ("at", "", "-")] + [(f"{head[0]} {city} Campus", place[1:])]
        out.append((", ".join(head), place))
    return out

def main(db_path, hd_zip, data_dir="data"):
    sys.stdout.reconfigure(encoding="utf-8")
    con = sqlite3.connect(db_path)
    hd, _ = load_hd(hd_zip)
    where = locations(data_dir)
    for inst, u in con.execute("SELECT id, ipeds_unitid FROM institution WHERE ipeds_unitid IS NOT NULL"):
        if inst not in where and u in hd:
            where[inst] = (hd[u]["CITY"], STATES.get(hd[u]["STABBR"], ""), "United States")
    # Targets are institutions' own ROR names, curated aliases and IPEDS names. ROR's
    # "chosen" matches on bare names are sometimes wrong, so they are not targets here.
    known = {}
    by_unitid = {}
    for inst, name, u in con.execute("SELECT id, name, ipeds_unitid FROM institution ORDER BY id LIKE 'ror:%' DESC"):
        if u:
            by_unitid.setdefault(u, inst)
            inst = by_unitid[u]
        if not SYSTEM.search(name):
            known.setdefault(fold(name), set()).add(inst)
    for aff, inst in con.execute("SELECT affiliation_as_printed, institution_id FROM affiliation_match WHERE method='alias'"):
        known.setdefault(fold(aff), set()).add(inst)
    for u, r in hd.items():
        if not SYSTEM.search(r["INSTNM"]) and u not in by_unitid:
            known.setdefault(fold(r["INSTNM"]), set()).add("ipeds:" + u)
            where["ipeds:" + u] = (r["CITY"], STATES.get(r["STABBR"], ""), "United States")
    todo = [a for (a,) in con.execute("SELECT affiliation_as_printed FROM affiliation_match WHERE institution_id IS NULL AND (affiliation_as_printed LIKE '%,%' OR affiliation_as_printed LIKE '%-%' OR affiliation_as_printed LIKE '%–%')")]
    hit = new = 0
    for aff in todo:
        for c, dropped in candidates(aff):
            # Several institutions can share a name (Marian University, Union College); keep
            # the one whose city, state or country the dropped segments name.
            fits = [i for i in known.get(fold(c), ())
                    if all(is_place(seg, where.get(i, ("", "", ""))) for seg in dropped)]
            if len(fits) != 1 or (not dropped and len(known[fold(c)]) > 1):
                continue
            inst = fits[0]
            if inst.startswith("ipeds:") and not con.execute("SELECT 1 FROM institution WHERE id=?", (inst,)).fetchone():
                u = inst[6:]
                con.execute("INSERT INTO institution(id, name, ipeds_unitid, country, kind) VALUES (?,?,?,?,?)",
                            (inst, hd[u]["INSTNM"], u, "US", "education"))
                fill_ipeds(con, hd, inst, u)
                new += 1
            con.execute("UPDATE affiliation_match SET institution_id=?, method='place-stripped' WHERE affiliation_as_printed=?", (inst, aff))
            hit += 1
            break
    con.execute("UPDATE appearance SET institution_id = (SELECT institution_id FROM affiliation_match m WHERE m.affiliation_as_printed = appearance.affiliation_as_printed)")
    con.commit()
    print(f"place-stripped matches: {hit} of {len(todo)} unmatched strings with a comma or dash ({new} institutions added from IPEDS)")

if __name__ == "__main__":
    main(*sys.argv[1:4])
