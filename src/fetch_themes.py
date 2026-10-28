"""Parse NCTE's "Dates, Sites, and Themes for Past CCCC Conventions" page into data/themes.csv.

Usage: python -I src/fetch_themes.py <saved_page.html> <out.csv>
The page is one run of text: "April 9-12, 2025 Baltimore, MD "Theme" Program Chair: Name". Save it with
curl -sL https://cccc.ncte.org/cccc/review/pastconventions/ first. Dates, sites, themes and chairs are
facts about the conventions; the CSV is committed so the build does not depend on the page.
"""
import csv, html, re, sys

MONTH = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?"
START = re.compile(rf"(?={MONTH} \d{{1,2}}\S{{0,3}}\d{{0,2}},? ?(?:19|20)\d\d)")
ENTRY = re.compile(rf"^(?P<dates>{MONTH} [^,]*?,? ?(?P<year>(?:19|20)\d\d))\s+(?P<rest>.*)$")

def main(src, out):
    raw = open(src, "rb").read()
    try:
        h = raw.decode("utf-8")
    except UnicodeDecodeError:
        h = raw.decode("cp1252", "replace")
    i = h.find('entry-content">')
    body = h[i + 15:] if i >= 0 else h
    body = body[:body.find("</div>")] if "</div>" in body else body
    text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", body)))
    rows = []
    for part in START.split(text):
        m = ENTRY.match(part.strip())
        if not m:
            continue
        rest = m["rest"]
        chair = None
        c = re.search(r"Program Chair[s]?:\s*(.*)$", rest)
        if c:
            chair, rest = c.group(1).strip(), rest[:c.start()].strip()
        theme = None
        t = re.search(r"[“\"](.+)[”\"]\s*$", rest)
        if t:
            theme, rest = t.group(1).strip(), rest[:t.start()].strip()
        rows.append(dict(year=int(m["year"]), dates=m["dates"].replace("\u2013", "-").strip(), site=rest.strip(), theme=theme or "", chair=chair or ""))
    rows.sort(key=lambda r: (r["year"], r["dates"]))
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["year", "dates", "site", "theme", "chair"])
        w.writeheader(); w.writerows(rows)
    print(f"themes: {len(rows)} conventions, {sum(1 for r in rows if r['theme'])} with themes, {sum(1 for r in rows if r['chair'])} with chairs")

if __name__ == "__main__":
    main(*sys.argv[1:3])
