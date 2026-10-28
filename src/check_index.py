"""Score the PDF parser against the programs' own Index of Participants.

Usage: python -I src/check_index.py <pdf_dir> <db_path> [out.json]
Six programs (2004, 2005, 2007, 2008, 2010, 2011) end with an index: "Abraham, Matthew: FSIG 14,
G 32, J 07". Each entry is a person and the codes of the sessions they appear in. That is an
independent record of who was listed where, so it measures the parser without eShow. For each
year it compares the set of (person, session code) pairs from the index with the pairs the
parser found, matching a person on first and last word of the name:
  precision  share of the parser's pairs that the index also lists
  recall     share of the index's pairs that the parser found
and says how many missed pairs sit in sessions the parser never found at all.
The index is not a perfect gold standard (it can omit or misprint a code), so the figures
describe agreement, and the sampled misses are worth reading.
"""
import collections, json, os, re, sqlite3, sys, unicodedata
import pymupdf

SOURCES = {
    2004: ("2004__2004completeprogram.pdf", "index of participants"),
    2005: ("2005__2005completeprogram.pdf", "index of participants"),
    2007: ("2007__2007completeprogram.pdf", "index of participants"),
    2008: ("2008__2008programindex.pdf", None),
    2010: ("2010__cccc2010-program.pdf", "index of participants"),
    2011: ("2011__program__entire-prog.pdf", "index of participants"),
}
CODE = re.compile(r"\b([A-Z]{1,4})\s?(\d{1,3})\b")
ENTRY = re.compile(r"^(?P<name>[^:]+?,\s*[^:]+?):\s*(?P<rest>.*)$")

def fold(s):
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()

def words(s):
    return re.findall(r"[a-z]+(?:['\-][a-z]+)*", fold(s))

def key_from_index(name):
    last, first = name.split(",", 1)
    first = re.sub(r"\b(jr|sr|ii|iii|iv)\b\.?", "", first, flags=re.I)
    f, l = words(first), words(last)
    return (f[0], l[-1]) if f and l else None

def key_from_printed(name):
    t = words(re.sub(r"\b(jr|sr|ii|iii|iv)\b\.?", "", name, flags=re.I))
    return (t[0], t[-1]) if len(t) >= 2 else None

def norm_code(letters, num):
    return f"{letters}.{int(num)}"

def index_pairs(path, marker):
    d = pymupdf.open(path)
    start = 0
    if marker:
        start = next(i for i, pg in enumerate(d) if marker in pg.get_text()[:400].lower())
    pairs, cur, buf = set(), None, []
    def flush():
        if cur:
            for m in CODE.finditer(" ".join(buf)):
                if m.group(1) in ("FSIG", "TSIG", "WSIG", "PSIG", "W", "MW", "AW", "SW", "RN", "DP") or len(m.group(1)) == 1:
                    pairs.add((cur, norm_code(m.group(1), m.group(2))))
    for pg in d[start:]:
        for line in pg.get_text().split("\n"):
            line = line.strip()
            m = ENTRY.match(line)
            if m and len(m.group("name")) < 60 and not CODE.fullmatch(m.group("name")):
                flush()
                cur, buf = key_from_index(m.group("name")), [m.group("rest")]
            elif cur is not None and line and not re.fullmatch(r"\d{1,3}|[A-Z]", line) and "CONVENTION" not in line:
                buf.append(line)
        flush_now = None
    flush()
    return pairs

def main(pdf_dir, db_path, out=None):
    con = sqlite3.connect(db_path)
    res = {}
    for year, (fname, marker) in SOURCES.items():
        I = index_pairs(os.path.join(pdf_dir, fname), marker)
        codes_found = {r[0] for r in con.execute("SELECT code FROM session WHERE year=? AND code IS NOT NULL", (year,))}
        codes_found = {re.sub(r"^([A-Z]+)\.0*(\d+)$", r"\1.\2", c) for c in codes_found}
        P = set()
        for name, code in con.execute("""SELECT a.name_as_printed, s.code FROM appearance a JOIN session s ON s.id = a.session_id
                                         WHERE s.year = ? AND s.code IS NOT NULL""", (year,)):
            k = key_from_printed(name)
            if k:
                P.add((k, re.sub(r"^([A-Z]+)\.0*(\d+)$", r"\1.\2", code)))
        # score on codes the index and the parse both use as session codes
        both = I & P
        miss = I - P
        extra = P - I
        no_session = {m for m in miss if m[1] not in codes_found}
        res[year] = {"index_pairs": len(I), "parsed_pairs": len(P), "agree": len(both),
                     "precision": round(len(both) / len(P), 3) if P else None, "recall": round(len(both) / len(I), 3) if I else None,
                     "missed": len(miss), "missed_in_unfound_sessions": len(no_session), "extra": len(extra),
                     "sample_missed": sorted(map(str, list(miss - no_session)[:8])), "sample_extra": sorted(map(str, list(extra)[:8]))}
        print(f"{year}: index {len(I):,} pairs, parsed {len(P):,}; precision {res[year]['precision']}, recall {res[year]['recall']}; "
              f"{len(miss):,} missed ({len(no_session):,} in sessions the parser never found); {len(extra):,} not in the index")
    if out:
        json.dump(res, open(out, "w", encoding="utf-8"), indent=1)
    return res

if __name__ == "__main__":
    main(*sys.argv[1:4])
