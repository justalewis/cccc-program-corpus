"""Score the PDF parser against eShow for years that have both (2024-2026).

Usage: python -I src/score_pdf.py <db_path> <year>
Per shared session code, compares the set of normalized names. Reports precision and recall
over all shared sessions, and how often the affiliation agrees when the name matches.
"""
import re, sqlite3, sys, unicodedata

def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower().replace(".", " ")
    return re.sub(r"\s+", " ", s).strip()

def code_norm(c):
    m = re.match(r"^([A-Z]{1,4})[.\-–]0*(\d+)", c or "")
    return f"{m.group(1)}.{int(m.group(2))}" if m else None

def main(db_path, year):
    sys.stdout.reconfigure(encoding="utf-8")
    con = sqlite3.connect(db_path)
    year = int(year)
    def people(prefix):
        out = {}
        for code, name, aff in con.execute(f"""select s.code, a.name_as_printed, a.affiliation_as_printed from appearance a join session s on s.id=a.session_id
                                              where s.year=? and s.id like '{prefix}%' and s.parent_id is null""", (year,)):
            c = code_norm(code)
            if c:
                out.setdefault(c, {})[norm(name)] = norm(aff)
        return out
    es, pdf = people("eshow:"), people("pdf:")
    shared = set(es) & set(pdf)
    tp = fp = fn = aff_ok = 0
    worst = []
    for c in shared:
        e, p = es[c], pdf[c]
        t = set(e) & set(p)
        tp += len(t); fp += len(set(p) - set(e)); fn += len(set(e) - set(p))
        aff_ok += sum(1 for n in t if e[n] and p[n] and (e[n] in p[n] or p[n] in e[n]))
        if set(p) ^ set(e):
            worst.append((c, sorted(set(p) - set(e))[:3], sorted(set(e) - set(p))[:3]))
    print(f"{year}: eShow sessions with code {len(es)}, PDF sessions {len(pdf)}, shared {len(shared)}")
    print(f"  names: precision {tp / max(1, tp + fp):.3f}, recall {tp / max(1, tp + fn):.3f} (tp {tp}, fp {fp}, fn {fn})")
    print(f"  affiliation agrees for {aff_ok / max(1, tp):.3f} of matched names")
    for w in worst[:12]:
        print("   ", w)

if __name__ == "__main__":
    main(*sys.argv[1:3])
