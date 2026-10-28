"""Tests for the reader: every page loads, and the ethics rules hold in the data and the pages."""
import csv, json, os, re
import pytest
from conftest import needs_db

pytestmark = needs_db

PAGES = ["/", "/tools", "/conventions", "/areas", "/groups", "/groups?all=1", "/trends?terms=multimodal,antiracis*", "/institutions",
         "/atlas", "/atlas?year=2005", "/anatomy", "/area-types", "/network", "/network?era=2004–2009", "/corpus", "/how-to-read", "/ethics",
         "/about", "/search?q=composition", "/year/2005", "/year/2024"]

@pytest.mark.parametrize("path", PAGES)
def test_page_loads_noindex(client, path):
    r = client.get(path)
    assert r.status_code == 200, path
    assert "noindex" in r.headers.get("X-Robots-Tag", "")
    assert b"Traceback" not in r.data
    assert b'name="robots" content="noindex' in r.data

def test_calls_page_if_built(client, con):
    has = con.execute("SELECT 1 FROM sqlite_master WHERE name = 'call_year'").fetchone()
    assert client.get("/calls").status_code == (200 if has else 404)

def test_robots_disallows_all(client):
    assert b"Disallow: /" in client.get("/robots.txt").data

def test_unknown_pages_are_404(client):
    for p in ("/person/p:nobody-at-all", "/session/nope", "/institution/nope", "/group/nope", "/area/nope", "/year/1850"):
        assert client.get(p).status_code == 404, p

# ---- ethics: person pages -------------------------------------------------------------------

def test_person_pages_need_two_conventions(con):
    n = con.execute("SELECT count(*) FROM person_summary WHERE eligible = 1 AND conventions < 2").fetchone()[0]
    assert n == 0

def test_single_listing_has_no_page(client, con):
    r = con.execute("SELECT person_id FROM person_summary WHERE conventions = 1 LIMIT 1").fetchone()
    assert client.get("/person/" + r["person_id"]).status_code == 404

def test_suppressed_people_have_no_page(client):
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "suppressed_people.csv")
    for row in csv.DictReader(open(path, encoding="utf-8-sig")):
        assert client.get("/person/" + row["person_id"]).status_code == 404

def test_session_page_links_only_eligible_people(client, con):
    sid = con.execute("""SELECT a.session_id FROM appearances a JOIN person_summary p ON p.person_id = a.person_id
                         WHERE p.eligible = 0 AND p.conventions = 1 LIMIT 1""").fetchone()[0]
    html = client.get("/session/" + sid).data.decode()
    for pid in set(re.findall(r'href="/person/([^"]+)"', html)):
        ok = con.execute("SELECT eligible FROM person_summary WHERE person_id = ?", (pid.replace("%3A", ":"),)).fetchone()
        assert ok and ok[0] == 1

# ---- ethics: network thresholds ---------------------------------------------------------------

def test_network_nodes_have_three_listings_and_edges_two_sessions(con):
    import analytics as AN
    for era in AN.ERAS:
        net = AN.network(con, era)
        assert all(e["n"] >= AN.MIN_SHARED for e in net["edges"])
        ids = [n["id"] for n in net["nodes"]]
        rows = con.execute(f"SELECT appearances FROM person_summary WHERE person_id IN ({','.join('?' * len(ids))})", ids).fetchall()
        assert all(r[0] >= AN.MIN_LISTINGS for r in rows)

def test_teams_are_eligible_people_only(con):
    import analytics as AN
    for t in AN.teams(con):
        for pid in (t["a"], t["b"]):
            r = con.execute("SELECT eligible, appearances FROM person_summary WHERE person_id = ?", (pid,)).fetchone()
            assert r["eligible"] == 1 and r["appearances"] >= AN.MIN_LISTINGS

# ---- nothing private in the database -----------------------------------------------------------

def test_no_private_columns(con):
    banned = ("description", "eshow_key", "eshow_person_key", "abstract")
    for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'"):
        cols = [r[1].lower() for r in con.execute(f"PRAGMA table_info('{t}')")]
        assert not [c for c in cols if c in banned], (t, cols)

def test_call_tables_hold_only_derived_columns(con):
    for t in ("call_year", "call_term"):
        if con.execute("SELECT 1 FROM sqlite_master WHERE name = ?", (t,)).fetchone():
            cols = {r[1] for r in con.execute(f"PRAGMA table_info('{t}')")}
            assert not cols & {"text", "body", "content"}, (t, cols)

def test_titles_table_has_no_long_text(con):
    # a longer "title" is an unclosed quote that swallowed program prose
    assert con.execute("SELECT max(length(text)) FROM titles WHERE kind = 'paper'").fetchone()[0] <= 260

def test_export_has_no_private_fields(client):
    rows = json.loads(client.get("/export.json?q=assessment&y0=2010&y1=2010").data.decode())["rows"]
    assert rows and not {"description", "eshow_key", "email"} & set(rows[0])

def test_export_csv_has_bom_and_type(client):
    r = client.get("/export.csv?q=assessment&y0=2010&y1=2010")
    assert r.mimetype == "text/csv" and r.data.startswith(b"\xef\xbb\xbf")

# ---- measures ---------------------------------------------------------------------------------

def test_census_shares_in_range(con):
    for r in con.execute("SELECT * FROM census"):
        if r["us_ipeds"]:
            assert 0 <= r["two_year"] / r["us_ipeds"] <= 0.2
        assert r["people"] > 0 and r["sessions"] > 0

def test_term_regex_uses_word_boundaries(client):
    import app as A
    assert A.term_regex("labor").search("collaboration") is None
    assert A.term_regex("labor").search("emotional labor and care")
    assert A.term_regex("antiracis*").search("antiracist pedagogy")
