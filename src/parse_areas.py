"""Read each session's proposal area from the program PDFs.

Usage: python -I src/parse_areas.py <pdf_dir> <db_path> <crosswalk.csv>
From 2004 through 2026 (except 2018, which tags each session with three hashtags that go in
session.topic_tags) the programs print a session's
proposal area as a short italic line directly above the session code ("Theory",
"12-Writing Pedagogies and Processes"). This reads those lines, matches them to sessions by
(year, code), and stores them in session.area_raw (as printed), session.area (the printed
label without its leading number) and session.area_group (from data/area_crosswalk.csv, which
maps each year's headings onto families so trends can cross renamings).
1999's labels are formats (Panel, Roundtable), not areas, and are skipped.
"""
import csv, collections, difflib, os, re, sqlite3, sys
import pymupdf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python -I leaves it off
from parse_pdf import SOURCES

CODE = re.compile(r"^([A-Z]{1,4})\s?[.\-–]\s?(\d{1,3})\b")
NUMBER = re.compile(r"^\d{1,3}\s*[-–—]\s*")

def lines(path):
    d = pymupdf.open(path)
    for pg in d:
        for b in pg.get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                sp = [s for s in l["spans"] if s["text"].strip()]
                if not sp:
                    continue
                t = "".join(s["text"] for s in l["spans"]).replace("\t", " ")
                t = re.sub(r"\s+", " ", t).strip()
                yield round(sp[0]["size"], 1), sp[0]["font"], t

def italic(font):
    return "italic" in font.lower() and "bold" not in font.lower()

def year_areas(files, pdf_dir):
    """{code: area_raw} for one convention year."""
    cand = []
    for f in files:
        path = os.path.join(pdf_dir, f)
        if not os.path.exists(path):
            continue
        L = list(lines(path))
        for a, b in zip(L, L[1:]):
            m = CODE.match(b[2])
            if m and not CODE.match(a[2]) and italic(a[1]) and 3 < len(a[2]) < 80 and ("," not in a[2] or a[2].startswith("#")):
                cand.append((a[0], a[2], f"{m.group(1)}.{int(m.group(2))}"))
    if not cand:
        return {}
    modal = collections.Counter(c[0] for c in cand).most_common(1)[0][0]  # drops "Featured Session" flags set smaller
    out = {}
    for size, label, code in cand:
        if abs(size - modal) <= 0.3:
            out.setdefault(code, label)
    return out

def norm_code(code):
    m = CODE.match(code or "")
    return f"{m.group(1)}.{int(m.group(2))}" if m else code

def clean_labels(areas):
    """Keep a year's real headings: labels used at least three times, plus near-misses of them
    (a typo like "Information Techologies" folds into "Information Technologies"). Italic lines
    that are book titles or one-off track names stay in area_raw but get no area."""
    clean = {code: NUMBER.sub("", raw).strip() for code, raw in areas.items()}
    n = collections.Counter(clean.values())
    core = [l for l, k in n.items() if k >= 3]
    out = {}
    for code, label in clean.items():
        if label.startswith("#"):  # 2018 prints three hashtags, not an area
            out[code] = None
            continue
        if label in core:
            out[code] = label
            continue
        near = difflib.get_close_matches(label, core, n=1, cutoff=0.88)
        out[code] = near[0] if near else None
    return out

def main(pdf_dir, db_path, crosswalk_csv):
    con = sqlite3.connect(db_path)
    cols = [r[1] for r in con.execute("pragma table_info(session)")]
    for c in ("area_raw", "area", "area_group", "topic_tags"):
        if c not in cols:
            con.execute(f"ALTER TABLE session ADD COLUMN {c} TEXT")
    cross = {}
    if os.path.exists(crosswalk_csv):
        for r in csv.DictReader(open(crosswalk_csv, encoding="utf-8")):
            cross[(int(r["year"]), r["area"])] = r["group"]
    found = unmatched = 0
    for year in sorted(SOURCES):
        if year == 1999:
            continue
        raw_by_code = year_areas(SOURCES[year], pdf_dir)
        area_by_code = clean_labels(raw_by_code)
        sess = collections.defaultdict(list)
        for sid, code in con.execute("SELECT id, code FROM session WHERE year=? AND parent_id IS NULL AND code IS NOT NULL", (year,)):
            sess[norm_code(code)].append(sid)
        n = 0
        for code, raw in raw_by_code.items():
            ids = sess.get(code)
            if not ids:
                unmatched += 1
                continue
            area = area_by_code.get(code)
            for sid in ids:
                con.execute("UPDATE session SET area_raw=?, area=?, area_group=?, topic_tags=? WHERE id=?",
                            (raw, area, cross.get((year, area)) if area else None, raw if raw.startswith("#") else None, sid))
                n += 1
        found += n
        total = sum(len(v) for v in sess.values())
        kept = sum(1 for c in raw_by_code if area_by_code.get(c))
        print(f"{year}: {len(raw_by_code)} labeled codes, {n} sessions tagged of {total}, {kept} with a clean area")
    con.commit()
    clean = con.execute("SELECT count(*) FROM session WHERE area IS NOT NULL").fetchone()[0]
    mapped = con.execute("SELECT count(*) FROM session WHERE area_group IS NOT NULL").fetchone()[0]
    print(f"areas: {found} sessions tagged, {clean} with a clean area, {mapped} mapped to a group; {unmatched} labeled codes found no session")

if __name__ == "__main__":
    main(*sys.argv[1:4])
