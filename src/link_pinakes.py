"""Suggest links from CCCC convention papers to later articles in Pinakes.

Usage: python -I src/link_pinakes.py <corpus.db> <pinakes_works.jsonl> <out.csv>
Every link is a suggestion: person, paper title and article are compared, and the best
candidate per paper is scored in tiers. Nothing is confirmed without a human check.
The works file comes from the Pinakes public API (one request a second; see
../wpa-l-archive/tools/pinakes_dump.py): id, doi, title, authors ("A B; C D"), pub_date, journal.

Candidates: articles whose title shares most of its distinctive words with the paper title
(inverted index over words of four or more letters), published from one year before the
convention to eight years after. Evidence:
  title   Jaccard overlap of distinctive title words, and whether the part before a colon matches
  author  the presenting name's last name and first initial appear among the article's authors
  time    publication year against the convention year
Tiers: A = near-identical title and author match; B = close title and author match;
C = author match and a partly overlapping title; D = near-identical title, no author match.
"""
import collections, csv, json, re, sqlite3, sys, unicodedata

STOP = set("""about their there these those which while between through under toward towards study studies case cases writing
students student teaching composition rhetoric college using based approach approaches analysis practice practices
research""".split())

def fold(s):
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()

def words(title):
    return {w for w in re.findall(r"[a-z]{4,}", fold(title)) if w not in STOP}

def lead(title):
    return re.sub(r"[^a-z0-9]+", " ", fold(re.split(r"[:?]", title or "")[0])).strip()

def names(authors):
    """('last', 'f') pairs from 'First Last; First M. Last'."""
    out = set()
    for a in (authors or "").split(";"):
        t = re.findall(r"[a-z\-']+", fold(a))
        t = [x for x in t if len(x) > 0]
        if len(t) >= 2:
            out.add((t[-1], t[0][0]))
    return out

def printed(name):
    t = re.findall(r"[a-z\-']+", fold(re.sub(r"\b(jr|sr|ii|iii|iv)\b\.?", "", name, flags=re.I)))
    return (t[-1], t[0][0]) if len(t) >= 2 else None

def main(db, works_path, out):
    works = []
    for line in open(works_path, encoding="utf-8"):
        w = json.loads(line)
        yr = int((w.get("pub_date") or "0")[:4] or 0)
        w["_words"], w["_lead"], w["_names"], w["_year"] = words(w["title"]), lead(w["title"]), names(w["authors"]), yr
        works.append(w)
    index = collections.defaultdict(list)
    for i, w in enumerate(works):
        for t in w["_words"]:
            index[t].append(i)
    index = {t: v for t, v in index.items() if len(v) <= 1500}
    con = sqlite3.connect(db)
    rows = con.execute("""SELECT a.id, s.year, a.person_id, a.name_as_printed, a.paper_title, s.id
                          FROM appearance a JOIN session s ON s.id = a.session_id
                          WHERE a.paper_title IS NOT NULL AND a.paper_title != '' AND s.year < 2027""").fetchall()
    best = {}
    for aid, year, pid, name, paper, sid in rows:
        pw = words(paper)
        if len(pw) < 2:
            continue
        cand = collections.Counter()
        for t in pw:
            for i in index.get(t, ()):
                cand[i] += 1
        me = printed(name)
        pl = lead(paper)
        for i, hits in cand.most_common(40):
            w = works[i]
            if not (year - 1 <= w["_year"] <= year + 8):
                continue
            union = len(pw | w["_words"])
            jac = len(pw & w["_words"]) / union if union else 0
            same_lead = bool(pl) and len(pl) > 12 and pl == w["_lead"]
            author = bool(me) and me in w["_names"]
            if jac >= 0.8 or same_lead:
                tier = "A" if author else "D"
            elif jac >= 0.55 and author:
                tier = "B"
            elif jac >= 0.35 and author:
                tier = "C"
            else:
                continue
            key = aid
            score = {"A": 4, "B": 3, "C": 2, "D": 1}[tier] + jac
            if key not in best or score > best[key][0]:
                best[key] = (score, tier, round(jac, 2), year, pid, name, paper, sid, w["id"], w["title"], w["authors"], w["journal"], w["_year"], w.get("doi"))
    with open(out, "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["tier", "title_overlap", "convention_year", "person_id", "name_as_printed", "paper_title", "session_id",
                     "pinakes_id", "article_title", "article_authors", "journal", "article_year", "doi"])
        for sc, tier, jac, year, pid, name, paper, sid, wid, wt, wa, wj, wy, doi in sorted(best.values(), key=lambda t: -t[0]):
            wr.writerow([tier, jac, year, pid, name, paper, sid, wid, wt, wa, wj, wy, doi])
    c = collections.Counter(v[1] for v in best.values())
    print(f"papers with a title: {len(rows):,}; suggested links: {len(best):,} {dict(sorted(c.items()))}")
    return best

if __name__ == "__main__":
    main(*sys.argv[1:4])
