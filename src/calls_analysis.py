"""Compare each year's call for proposals with what the program accepted.

Usage: python -I src/calls_analysis.py <reader.db> <capture_dir>
Reads the private capture (NCTE's call pages and PDFs) and writes two derived tables into
reader.db; the call text itself is never stored or shown:
  call_year(year, kind, source_url, words, echo_this, echo_other)
  call_term(year, rank, term, in_call, title_share_this, title_share_other)
A call's distinctive terms are words of five or more letters that occur at least three times in
that call and in few other calls, after dropping dates, host cities and submission vocabulary.
The echo is the share of that year's session and paper titles that use one of the top terms,
against the share of titles in other years. It is a hint about whether the program took up the
call's language, not a measure of influence: the call and the program share a field's vocabulary.
"""
import collections, glob, math, os, re, sqlite3, sys, unicodedata

ADMIN = set("""january february march april june july august september october november december monday tuesday wednesday thursday friday
saturday sunday proposal proposals proposed submit submitted submission submissions deadline deadlines notification notifications
database convention conventions annual review reviewer reviewers reviewed criteria guidelines guideline information required
registration register travel award awards grant grants questions requests email address virtual hybrid zoom session sessions
panel panels presentation presentations presenter presenters speaker speakers participant participants program programs
format formats chair chairs include includes included including please should must also about their there these those which
would could where other between through during within without before after under around across because while
https http nominee nominees nomination nominations onvention ments invitation invitations cccc ncte time zone accessibility accessible online person people attend attendees attendee workshop workshops roundtable
roundtables poster posters special interest groups group meeting meetings""".split())
CITY = set("""chicago atlanta antonio francisco orleans louisville louis vegas indianapolis tampa houston portland kansas pittsburgh
milwaukee spokane baltimore cleveland washington colorado denver minneapolis boston seattle philadelphia cincinnati
virginia carolina illinois maryland ohio oregon texas florida georgia missouri nevada indiana kentucky pennsylvania""".split())
PDF_NAMES = re.compile(r"callfor|cfp|4c_proposal|proposal_\d+", re.I)

def fold(s):
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()

def words(text):
    return [w for w in re.findall(r"[a-z]{5,}", fold(text)) if w not in ADMIN and w not in CITY]

def load_calls(capture_dir):
    """{year: (kind, source_url, text)}. HTML pages win over PDFs when a year has both."""
    import pymupdf
    from bs4 import BeautifulSoup
    from warcio.archiveiterator import ArchiveIterator
    calls = {}
    for warc in glob.glob(os.path.join(capture_dir, "*.warc.gz")):
        if "eshow" in warc or "wayback" in warc:
            continue
        with open(warc, "rb") as f:
            for rec in ArchiveIterator(f):
                if rec.rec_type != "response" or rec.http_headers.get_statuscode() != "200":
                    continue
                url = rec.rec_headers.get_header("WARC-Target-URI")
                m = re.search(r"call-(\d{4})$", url)
                if m and "cccc.ncte.org" in url:
                    soup = BeautifulSoup(rec.content_stream().read().decode("utf-8", "replace"), "lxml")
                    art = soup.select_one("article") or soup.select_one("main")
                    if art:
                        calls[int(m.group(1))] = ("page", url, " ".join(art.get_text(" ").split()))
                elif url.lower().endswith(".pdf") and "/convention/" in url and PDF_NAMES.search(url.rsplit("/", 1)[-1]):
                    y = re.search(r"/convention/(\d{4})/", url)
                    if y and int(y.group(1)) not in calls:
                        try:
                            doc = pymupdf.open(stream=rec.content_stream().read(), filetype="pdf")
                            calls[int(y.group(1))] = ("pdf", url, " ".join(" ".join(p.get_text() for p in doc).split()))
                        except Exception:
                            pass
    return calls

def build(db_path, capture_dir):
    calls = load_calls(capture_dir)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    con.execute("DROP TABLE IF EXISTS call_year")
    con.execute("DROP TABLE IF EXISTS call_term")
    con.execute("CREATE TABLE call_year (year INTEGER PRIMARY KEY, kind TEXT, source_url TEXT, words INTEGER, echo_this REAL, echo_other REAL)")
    con.execute("CREATE TABLE call_term (year INTEGER, rank INTEGER, term TEXT, in_call INTEGER, title_share_this REAL, title_share_other REAL)")
    if not calls:
        con.commit(); print("calls: none found"); return
    per = {y: collections.Counter(words(t)) for y, (_, _, t) in calls.items()}
    n_calls = len(per)
    present = collections.Counter(w for c in per.values() for w in c)
    titles = [(r["year"], fold(r["text"])) for r in con.execute("SELECT year, text FROM titles")]
    by_year = collections.defaultdict(list)
    for y, t in titles:
        by_year[y].append(t)
    all_titles = len(titles)
    title_df = collections.Counter()
    for _, t in titles:
        for w in set(re.findall(r"[a-z]{5,}", t)):
            title_df[w] += 1
    for y in sorted(calls):
        kind, url, _ = calls[y]
        cand = []
        for w, c in per[y].items():
            if c >= 3 and present[w] <= max(3, n_calls // 4) and title_df[w] / all_titles < 0.04:
                cand.append((c * math.log(n_calls / present[w]), w, c))
        cand.sort(reverse=True)
        top = cand[:12]
        mine = by_year.get(y, [])
        other_n = all_titles - len(mine)
        rows, hit_this, hit_other = [], 0, 0
        if top and mine:
            rx = re.compile(r"(?<![a-z])(?:" + "|".join(re.escape(w) for _, w, _ in top) + ")")
            hit_this = sum(1 for t in mine if rx.search(t))
            hit_other = sum(1 for yy, t in titles if yy != y and rx.search(t))
            for rank, (_, w, c) in enumerate(top, 1):
                rw = re.compile(r"(?<![a-z])" + re.escape(w))
                a = sum(1 for t in mine if rw.search(t))
                b = sum(1 for yy, t in titles if yy != y and rw.search(t))
                rows.append((y, rank, w, c, a / len(mine), b / other_n))
        con.execute("INSERT INTO call_year VALUES (?,?,?,?,?,?)",
                    (y, kind, url, sum(per[y].values()), hit_this / len(mine) if mine else None, hit_other / other_n if other_n and mine else None))
        con.executemany("INSERT INTO call_term VALUES (?,?,?,?,?,?)", rows)
    con.commit()
    print(f"calls: {len(calls)} years ({sorted(calls)})")

if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
