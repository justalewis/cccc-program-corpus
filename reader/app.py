"""CCCC Program Reader: a read-only Flask app over reader.db (see build_reader.py).

Run locally:  READER_DB=build/reader.db flask --app reader/app.py run
Every page is noindex. Person pages exist only for people listed at two or more conventions.
"""
import csv, io, json, os, re, sqlite3
from datetime import date
from flask import Flask, Response, abort, g, render_template, request

DB = os.environ.get("READER_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "reader.db"))
SITE_URL = os.environ.get("READER_URL", "https://cccc-program-reader.fly.dev")
REPO_URL = "https://github.com/justalewis/cccc-program-corpus"
DATA_URL = "https://cccc-program-corpus.fly.dev"
MAX_EXPORT = 100_000

# Where the series breaks. Drawn on every year chart and listed on the home page.
BREAKS = [
    {"from": 2000, "to": 2003, "label": "No program in the corpus (2000–2003)", "kind": "gap"},
    {"from": 2020, "to": 2020, "label": "2020: program of a cancelled convention", "kind": "cancelled"},
    {"from": 2021, "to": 2022, "label": "2021–2022: virtual conventions", "kind": "virtual"},
    {"from": 2024, "to": 2024, "label": "2024: source changes from PDF to eShow", "kind": "source"},
    {"from": 2027, "to": 2027, "label": "2027: listing before the convention", "kind": "provisional"},
]

YEAR_NOTES = {
    1998: "The convention's web program, replayed from the Wayback Machine. Sections A and J are cut short in the captured pages.",
    1999: "Ten of fourteen letter sections survive as PDFs. Sections E, F, K and M have session titles only, from the web program's session pages.",
    2008: "Read from NCTE's complete program (321 pages). An earlier build used the day files, which lacked Saturday.",
    2018: "NCTE's 2018 program is laid out differently from the neighboring years, and the parser has less to go on there.",
    2020: "This is the printed program of a convention that was cancelled. It shows what was scheduled, not what happened.",
    2021: "A virtual convention. The program is split across several files, including on-demand sessions.",
    2022: "A virtual convention. The program is split across several files, including on-demand sessions.",
    2024: "Read from NCTE's eShow listing, with paper titles copied from the PDF program.",
    2025: "Read from NCTE's eShow listing, with paper titles copied from the PDF program.",
    2026: "Read from NCTE's eShow listing, with paper titles copied from the PDF program.",
    2027: "A listing taken before the convention. It changes as NCTE adds and cancels sessions, and is re-captured monthly through May 2027.",
}

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

# ---- data access -------------------------------------------------------------------------

def db():
    if "db" not in g:
        g.db = sqlite3.connect(f"file:{DB}?mode=ro&immutable=1", uri=True)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(_):
    d = g.pop("db", None)
    if d:
        d.close()

def q(sql, *args):
    return db().execute(sql, args).fetchall()

def q1(sql, *args):
    return db().execute(sql, args).fetchone()

_TITLES = None
def titles():
    """All session and paper titles in memory: (year, kind, session_id, text, lower)."""
    global _TITLES
    if _TITLES is None:
        con = sqlite3.connect(f"file:{DB}?mode=ro&immutable=1", uri=True)
        _TITLES = [(y, k, s, t, t.lower()) for y, k, s, t in con.execute("SELECT year, kind, session_id, text FROM titles")]
        con.close()
    return _TITLES

def build_date():
    return date.fromtimestamp(os.path.getmtime(DB)).isoformat() if os.path.exists(DB) else ""

def natural(code):
    m = re.match(r"([A-Za-z]+)[.\-]?(\d*)", code or "")
    return (m.group(1), int(m.group(2) or 0)) if m else ("", 0)

def term_regex(term):
    """Word-boundary match; a trailing * lets the word continue (antiracis* finds antiracist)."""
    t = term.strip().lower()
    if not t:
        return None
    star = t.endswith("*")
    t = t.rstrip("*").strip()
    if not t:
        return None
    body = r"\s+".join(re.escape(w) for w in t.split())
    return re.compile(r"(?<!\w)" + body + (r"\w*" if star else r"(?!\w)"))

@app.template_filter("pct")
def pct(v, digits=1):
    return "" if v is None else f"{100 * v:.{digits}f}%"

@app.template_filter("num")
def num(v):
    return "" if v is None else f"{v:,}"

@app.after_request
def headers(r):
    r.headers["X-Robots-Tag"] = "noindex, nofollow"
    return r

@app.context_processor
def inject():
    return {"build_date": build_date(), "repo_url": REPO_URL, "data_url": DATA_URL}

@app.route("/robots.txt")
def robots():
    return Response("User-agent: *\nDisallow: /\n", mimetype="text/plain")

# ---- home: who convenes the field --------------------------------------------------------

def census_rows():
    out = []
    for r in q("SELECT * FROM census ORDER BY year"):
        d = dict(r)
        us, ppl = d["us_ipeds"] or 0, d["people"] or 0
        d["two_year_share"] = d["two_year"] / us if us else None
        d["public_share"] = d["public_n"] / us if us else None
        d["private_share"] = d["private_n"] / us if us else None
        d["forprofit_share"] = d["forprofit_n"] / us if us else None
        d["hbcu_share"] = d["hbcu_n"] / us if us else None
        d["non_us_share"] = d["non_us"] / d["matched"] if d["matched"] else None
        d["unmatched_share"] = 1 - d["matched"] / d["with_affiliation"] if d["with_affiliation"] else None
        d["newcomer_share"] = d["newcomers"] / ppl if ppl and d["year"] > 1998 else None
        d["chair_share"] = d["chairs"] / d["appearances"] if d["appearances"] else None
        out.append(d)
    return out

METRICS = [
    ("people", "People listed", "count"),
    ("sessions", "Sessions", "count"),
    ("newcomer_share", "Share listed for the first time in this corpus", "share"),
    ("two_year_share", "Share at two-year colleges", "share"),
    ("public_share", "Share at public colleges", "share"),
    ("private_share", "Share at private nonprofit colleges", "share"),
    ("forprofit_share", "Share at for-profit colleges", "share"),
    ("hbcu_share", "Share at historically Black colleges", "share"),
    ("non_us_share", "Share at institutions outside the US", "share"),
    ("top10_share", "Share of listings from the ten most-listed institutions", "share"),
    ("top50_share", "Share of listings from the fifty most-listed institutions", "share"),
    ("gini", "Concentration (Gini) of listings across institutions", "index"),
    ("unmatched_share", "Share with an affiliation we could not match", "share"),
]

@app.route("/")
def home():
    rows = census_rows()
    return render_template("home.html", rows=rows, metrics=METRICS, breaks=BREAKS,
                           data=json.dumps({"rows": rows, "metrics": METRICS, "breaks": BREAKS}))

# ---- years and sessions ------------------------------------------------------------------

@app.route("/year/<int:y>")
def year(y):
    c = q1("SELECT * FROM census WHERE year = ?", y)
    if not c:
        abort(404)
    conv = q1("SELECT * FROM conventions WHERE year = ?", y)
    cen = [r for r in census_rows() if r["year"] == y][0]
    sessions = q("""SELECT s.id, s.code, s.title, s.session_type, s.tracks,
                    (SELECT count(*) FROM appearances a WHERE a.session_id = s.id) AS n
                    FROM sessions s WHERE s.year = ? AND s.parent_id IS NULL""", y)
    sessions = sorted(sessions, key=lambda r: (natural(r["code"]), r["id"]))
    top = q("""SELECT i.id, i.name, i.two_year, iy.appearances, iy.people FROM inst_year iy JOIN institutions i ON i.id = iy.institution_id
               WHERE iy.year = ? ORDER BY iy.appearances DESC, i.name LIMIT 25""", y)
    docs = q("SELECT DISTINCT d.id, d.url, d.public_url, d.kind FROM source_documents d JOIN sessions s ON s.source_document_id = d.id WHERE s.year = ?", y)
    roles = q("SELECT role_group, count(*) n FROM appearances WHERE year = ? GROUP BY 1 ORDER BY n DESC", y)
    formats = json.loads(c["formats"] or "{}")
    prev = q1("SELECT max(year) y FROM census WHERE year < ?", y)["y"]
    nxt = q1("SELECT min(year) y FROM census WHERE year > ?", y)["y"]
    return render_template("year.html", y=y, c=cen, conv=conv, sessions=sessions, top=top, docs=docs, roles=roles,
                           formats=sorted(formats.items(), key=lambda t: -t[1]), note=YEAR_NOTES.get(y), prev=prev, next=nxt)

@app.route("/session/<path:sid>")
def session(sid):
    s = q1("SELECT * FROM sessions WHERE id = ?", sid)
    if not s:
        abort(404)
    people = q("""SELECT a.*, i.name AS inst_name, i.two_year, ps.eligible FROM appearances a
                  LEFT JOIN institutions i ON i.id = a.institution_id
                  LEFT JOIN person_summary ps ON ps.person_id = a.person_id
                  WHERE a.session_id = ? ORDER BY a.ord""", sid)
    children = q("SELECT id, code, title FROM sessions WHERE parent_id = ? ORDER BY id", sid)
    parent = q1("SELECT id, title FROM sessions WHERE id = ?", s["parent_id"]) if s["parent_id"] else None
    doc = q1("SELECT * FROM source_documents WHERE id = ?", s["source_document_id"])
    page = next((p["page"] for p in people if p["page"]), None)
    conv = q1("SELECT * FROM conventions WHERE year = ?", s["year"])
    link = None
    if doc and doc["public_url"]:
        link = doc["public_url"] + (f"#page={int(page) + 1}" if page is not None and doc["kind"] == "pdf" else "")
    return render_template("session.html", s=s, people=people, children=children, parent=parent, doc=doc, page=page, conv=conv,
                           link=link, today=date.today().strftime("%B %-d, %Y") if os.name != "nt" else date.today().strftime("%B %d, %Y"))

# ---- people ------------------------------------------------------------------------------

ROLE_COLORS = {"speaker": "#8a4b2a", "chair": "#1c1a17", "respondent": "#4f6f8f", "facilitator": "#6b8f4f", "other": "#999"}

@app.route("/person/<path:pid>")
def person(pid):
    p = q1("SELECT * FROM person_summary WHERE person_id = ?", pid)
    if not p or not p["eligible"]:
        return render_template("hidden_person.html"), 404
    rows = q("""SELECT a.*, s.code, s.title AS stitle, s.session_type, i.name AS inst_name, i.two_year FROM appearances a
                JOIN sessions s ON s.id = a.session_id LEFT JOIN institutions i ON i.id = a.institution_id
                WHERE a.person_id = ? ORDER BY a.year, s.code""", pid)
    sids = tuple({r["session_id"] for r in rows})
    co = []
    if sids:
        co = q(f"""SELECT ps.person_id, ps.display_name, count(DISTINCT a.session_id) AS shared, min(a.year) y0, max(a.year) y1
                   FROM appearances a JOIN person_summary ps ON ps.person_id = a.person_id
                   WHERE a.session_id IN ({','.join('?' * len(sids))}) AND a.person_id != ? AND ps.eligible = 1 AND ps.appearances >= 3
                   GROUP BY ps.person_id HAVING shared >= 2 ORDER BY shared DESC, ps.display_name LIMIT 25""", *sids, pid)
    variants = q("SELECT name_as_printed, count(*) n FROM appearances WHERE person_id = ? GROUP BY 1 ORDER BY n DESC", pid)
    insts = []
    for r in rows:
        if r["inst_name"] and (not insts or insts[-1][0] != r["inst_name"]):
            insts.append((r["inst_name"], r["year"]))
    years = {r["year"] for r in rows}
    return render_template("person.html", p=p, rows=rows, co=co, variants=variants, insts=insts, years=sorted(years),
                           strip=career_strip(rows), colors=ROLE_COLORS)

def career_strip(rows):
    y0, y1 = 1998, 2027
    w = 640
    step = (w - 40) / (y1 - y0)
    by = {}
    for r in rows:
        by.setdefault(r["year"], []).append(r["role_group"] or "other")
    marks = []
    for y, roles in sorted(by.items()):
        x = 20 + (y - y0) * step
        for k, role in enumerate(sorted(set(roles), key=lambda z: ["chair", "respondent", "facilitator", "speaker", "other"].index(z) if z in ("chair", "respondent", "facilitator", "speaker", "other") else 9)):
            marks.append({"x": round(x, 1), "y": 28 + 14 * k, "role": role, "n": roles.count(role), "year": y})
    ticks = [{"x": round(20 + (y - y0) * step, 1), "y": y} for y in range(2000, 2028, 5) if True] + [{"x": 20, "y": 1998}]
    return {"w": w, "marks": marks, "ticks": ticks, "gap": [round(20 + (2000 - y0) * step - step / 2, 1), round(20 + (2003 - y0) * step + step / 2, 1)]}

# ---- institutions ------------------------------------------------------------------------

@app.route("/institutions")
def institutions():
    qs = request.args.get("q", "").strip()
    two = request.args.get("two_year") == "1"
    non_us = request.args.get("non_us") == "1"
    where, args = ["1=1"], []
    if qs:
        where.append("i.name LIKE ?"); args.append(f"%{qs}%")
    if two:
        where.append("i.two_year = 1")
    if non_us:
        where.append("i.country IS NOT NULL AND i.country != 'US'")
    rows = q(f"""SELECT i.id, i.name, i.country, i.state, i.two_year, sum(iy.appearances) AS n, count(DISTINCT iy.year) AS years,
                 min(iy.year) y0, max(iy.year) y1 FROM institutions i JOIN inst_year iy ON iy.institution_id = i.id
                 WHERE {' AND '.join(where)} GROUP BY i.id ORDER BY n DESC LIMIT 200""", *args)
    return render_template("institutions.html", rows=rows, qs=qs, two=two, non_us=non_us)

@app.route("/institution/<path:iid>")
def institution(iid):
    i = q1("SELECT * FROM institutions WHERE id = ?", iid)
    if not i:
        abort(404)
    by_year = q("SELECT year, appearances, people FROM inst_year WHERE institution_id = ? ORDER BY year", iid)
    people = q("""SELECT ps.person_id, ps.display_name, ps.first_year, ps.last_year, count(*) AS n FROM appearances a
                  JOIN person_summary ps ON ps.person_id = a.person_id WHERE a.institution_id = ? AND ps.eligible = 1
                  GROUP BY ps.person_id ORDER BY n DESC, ps.display_name LIMIT 150""", iid)
    total = q1("SELECT count(DISTINCT person_id) n FROM appearances WHERE institution_id = ?", iid)["n"]
    sess = q("""SELECT DISTINCT s.id, s.year, s.code, s.title FROM appearances a JOIN sessions s ON s.id = a.session_id
                WHERE a.institution_id = ? ORDER BY s.year DESC, s.code LIMIT 60""", iid)
    printed = q("SELECT affiliation_as_printed, count(*) n FROM appearances WHERE institution_id = ? GROUP BY 1 ORDER BY n DESC LIMIT 12", iid)
    return render_template("institution.html", i=i, by_year=by_year, people=people, total=total, sess=sess, printed=printed)

# ---- search ------------------------------------------------------------------------------

def fts_query(text):
    toks = re.findall(r"\w+", text)
    return " ".join(f'"{t}"*' for t in toks[:8])

@app.route("/search")
def search():
    text = request.args.get("q", "").strip()
    res = {}
    if text and fts_query(text):
        m = fts_query(text)
        res["sessions"] = q("""SELECT s.id, s.year, s.code, s.title FROM sessions_fts f JOIN sessions s ON s.rowid = f.rowid
                               WHERE sessions_fts MATCH ? ORDER BY rank LIMIT 40""", m)
        res["papers"] = q("""SELECT t.year, t.session_id, t.text FROM papers_fts f JOIN titles t ON t.id = f.rowid
                             WHERE papers_fts MATCH ? ORDER BY rank LIMIT 40""", m)
        res["institutions"] = q("""SELECT i.id, i.name, i.country FROM institutions_fts f JOIN institutions i ON i.rowid = f.rowid
                                   WHERE institutions_fts MATCH ? ORDER BY rank LIMIT 25""", m)
        res["people"] = q("""SELECT ps.person_id, ps.display_name, ps.first_year, ps.last_year, ps.conventions FROM people_fts f
                             JOIN person_summary ps ON ps.person_id = f.person_id WHERE people_fts MATCH ? ORDER BY rank LIMIT 25""",
                          fts_query(text))
    return render_template("search.html", text=text, res=res)

# ---- term trends -------------------------------------------------------------------------

def trend_series(terms, scope):
    years = list(range(1998, 2028))  # every year, so 2000-2003 shows as a break and not a straight line
    rows = [t for t in titles() if scope == "all" or (scope == "sessions" and t[1] == "session") or (scope == "papers" and t[1] == "paper")]
    denom = {y: 0 for y in years}
    for t in rows:
        denom[t[0]] = denom.get(t[0], 0) + 1
    series = []
    for term in terms:
        rx = term_regex(term)
        if not rx:
            continue
        cnt = {y: 0 for y in years}
        for t in rows:
            if rx.search(t[4]):
                cnt[t[0]] += 1
        series.append({"term": term, "counts": cnt, "total": sum(cnt.values())})
    return years, denom, series

@app.route("/trends")
def trends():
    raw = request.args.get("terms", "")
    terms = [t.strip() for t in raw.split(",") if t.strip()][:6]
    scope = request.args.get("scope", "all")
    scope = scope if scope in ("all", "sessions", "papers") else "all"
    years, denom, series = trend_series(terms, scope) if terms else (list(range(1998, 2028)), {}, [])
    return render_template("trends.html", raw=raw, terms=terms, scope=scope, years=years, denom=denom, series=series, breaks=BREAKS,
                           data=json.dumps({"years": years, "denom": denom, "breaks": BREAKS,
                                            "series": [{"term": s["term"], "counts": s["counts"]} for s in series]}))

@app.route("/titles")
def title_list():
    term = request.args.get("term", "")
    y = request.args.get("year", type=int)
    scope = request.args.get("scope", "all")
    rx = term_regex(term)
    if not rx:
        abort(400)
    out = [t for t in titles() if (y is None or t[0] == y) and rx.search(t[4])
           and (scope == "all" or (scope == "sessions" and t[1] == "session") or (scope == "papers" and t[1] == "paper"))]
    out.sort(key=lambda t: (t[0], t[3]))
    sess = {r["id"]: r for r in q(f"SELECT id, code, title FROM sessions WHERE id IN ({','.join('?' * min(len(out), 400))})", *[t[2] for t in out[:400]])} if out else {}
    return render_template("titles.html", term=term, y=y, scope=scope, rows=out[:400], total=len(out), sess=sess)

# ---- corpus builder and export -----------------------------------------------------------

def corpus_rows(args, limit):
    y0, y1 = args.get("y0", type=int), args.get("y1", type=int)
    where, a = ["1=1"], []
    if y0:
        where.append("a.year >= ?"); a.append(y0)
    if y1:
        where.append("a.year <= ?"); a.append(y1)
    if args.get("role") in ("chair", "speaker", "respondent", "facilitator", "other"):
        where.append("a.role_group = ?"); a.append(args["role"])
    if args.get("inst", "").strip():
        where.append("i.name LIKE ?"); a.append(f"%{args['inst'].strip()}%")
    if args.get("two_year") == "1":
        where.append("i.two_year = 1")
    if args.get("non_us") == "1":
        where.append("i.country IS NOT NULL AND i.country != 'US'")
    sql = f"""SELECT a.year, a.session_id, s.code, s.title AS session_title, s.session_type, s.tracks, a.role, a.role_group,
              a.name_as_printed, a.affiliation_as_printed, a.paper_title, a.person_id, a.institution_id, i.name AS institution,
              i.country, i.two_year, d.public_url AS source_url, a.page
              FROM appearances a JOIN sessions s ON s.id = a.session_id LEFT JOIN institutions i ON i.id = a.institution_id
              LEFT JOIN source_documents d ON d.id = a.source_document_id WHERE {' AND '.join(where)} ORDER BY a.year, s.code, a.ord"""
    rx = term_regex(args.get("q", ""))
    out = []
    for r in db().execute(sql, a):
        if rx and not (rx.search((r["session_title"] or "").lower()) or rx.search((r["paper_title"] or "").lower())):
            continue
        out.append(dict(r))
        if len(out) >= limit:
            break
    return out

def corpus_label(args):
    bits = []
    if args.get("q"): bits.append(f'titles containing "{args["q"]}"')
    if args.get("y0") or args.get("y1"): bits.append(f'{args.get("y0") or "1998"}–{args.get("y1") or "2027"}')
    if args.get("role"): bits.append(f'role: {args["role"]}')
    if args.get("inst"): bits.append(f'institution contains "{args["inst"]}"')
    if args.get("two_year") == "1": bits.append("two-year colleges")
    if args.get("non_us") == "1": bits.append("outside the US")
    return "; ".join(bits) or "all listings"

@app.route("/corpus")
def corpus():
    has = any(request.args.get(k) for k in ("q", "y0", "y1", "role", "inst", "two_year", "non_us"))
    rows = corpus_rows(request.args, MAX_EXPORT) if has else []
    sample = rows[:15]
    qs = request.query_string.decode()
    label = corpus_label(request.args)
    cite = f'CCCC Program Reader. Corpus: {label}. {len(rows):,} listings. Built {build_date()}. {SITE_URL}/corpus?{qs}'
    return render_template("corpus.html", has=has, n=len(rows), sample=sample, qs=qs, a=request.args, label=label, cite=cite, capped=len(rows) >= MAX_EXPORT)

@app.route("/export.<fmt>")
def export(fmt):
    if fmt not in ("csv", "json"):
        abort(404)
    rows = corpus_rows(request.args, MAX_EXPORT)
    label = corpus_label(request.args)
    if fmt == "json":
        body = json.dumps({"corpus": {"filters": label, "listings": len(rows), "built": build_date(), "source": SITE_URL,
                                      "note": "People listed in the program, not attendees. See /how-to-read."}, "rows": rows}, ensure_ascii=False)
        return Response(body, mimetype="application/json")
    buf = io.StringIO()
    cols = list(rows[0].keys()) if rows else ["year"]
    w = csv.DictWriter(buf, fieldnames=cols)
    w.writeheader(); w.writerows(rows)
    return Response("﻿" + buf.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=cccc-corpus.csv"})

# ---- plain pages -------------------------------------------------------------------------

@app.route("/how-to-read")
def how():
    return render_template("how.html", breaks=BREAKS, notes=sorted(YEAR_NOTES.items()))

@app.route("/ethics")
def ethics():
    return render_template("ethics.html", contact=os.environ.get("READER_CONTACT"))

@app.route("/about")
def about():
    return render_template("about.html")

@app.errorhandler(404)
def nf(_):
    return render_template("error.html", msg="That page isn't in the reader."), 404

@app.errorhandler(400)
def bad(_):
    return render_template("error.html", msg="That request was missing something."), 400

if __name__ == "__main__":
    app.run(debug=True)
