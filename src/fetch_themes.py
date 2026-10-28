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
    # A range that crosses a month ("March 30-April 1, 1978") is split at the second month, so the
    # first half ends up on the end of the NEXT-LATER entry's chair or theme text. Move it back.
    tail = re.compile(rf"\s+({MONTH} \d{{1,2}}\S{{0,3}})$")
    for i in range(len(rows) - 1, 0, -1):
        for field in ("chair", "theme", "site"):
            m = tail.search(rows[i][field])
            if m:
                rows[i][field] = rows[i][field][:m.start()].strip()
                rows[i - 1]["dates"] = m.group(1).rstrip("-–") + "-" + rows[i - 1]["dates"]
    # A theme whose opening quote was lost stays in the site text: "Atlanta, GA The Uses of Literacy..."
    for r in rows:
        m = re.match(r"^([A-Z][A-Za-z.' ]+, [A-Z]{2})\s+(.+)$", r["site"])
        if m and not r["theme"]:
            r["site"], r["theme"] = m.group(1), m.group(2).strip(" ”\"")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["year", "dates", "site", "theme", "chair"])
        w.writeheader(); w.writerows(rows)
    print(f"themes: {len(rows)} conventions, {sum(1 for r in rows if r['theme'])} with themes, {sum(1 for r in rows if r['chair'])} with chairs")

if __name__ == "__main__":
    main(*sys.argv[1:3])
