"""Build a review page: a random sample of PDF-parsed sessions beside the program page they came from.

Usage: python -I src/review_sample.py <db_path> <pdf_dir> <out_dir> [per_era] [seed]
Samples per_era sessions (default 10) from each PDF layout era, renders the part of the
program page that holds each session with the parsed people outlined, and writes
out_dir/index.html. Open it in an ordinary browser (it runs from the file, no server):
tick what the parser got right, note what it missed, and use "Download CSV" to save the
review. Ticks are also kept in the browser's local storage. The page images are NCTE's,
so the folder stays private like the capture.
"""
import ast, json, os, random, sqlite3, sys
import pymupdf

ERAS = [(2004, 2010), (2011, 2015), (2016, 2020), (2021, 2023)]
ZOOM = 1.6

def crop_for(page, boxes, code):
    """Full page width, from the printed session code (when it is on this page above the
    first box) or a little above the first box, to a little below the last."""
    top = min(b[1] for b in boxes)
    above = [r.y0 for r in page.search_for(code) if r.y0 < top] if code else []
    y0 = max((max(above) - 8) if above else top - 90, 0)
    y1 = min(max(b[3] for b in boxes) + 30, page.rect.y1)
    return pymupdf.Rect(page.rect.x0, y0, page.rect.x1, y1)

def render(doc_path, page_no, boxes, code, out_path):
    doc = pymupdf.open(doc_path)
    page = doc[page_no - 1]
    clip = crop_for(page, boxes, code)
    for b in boxes:
        page.draw_rect(pymupdf.Rect(b), color=(0.85, 0.2, 0.1), width=1.2)
    page.get_pixmap(matrix=pymupdf.Matrix(ZOOM, ZOOM), clip=clip).save(out_path, jpg_quality=80)

def main(db_path, pdf_dir, out_dir, per_era=10, seed=20261027):
    per_era, seed = int(per_era), int(seed)
    os.makedirs(os.path.join(out_dir, "img"), exist_ok=True)
    con = sqlite3.connect(db_path)
    rng = random.Random(seed)
    cards = []
    for lo, hi in ERAS:
        ids = [r[0] for r in con.execute("""SELECT s.id FROM session s WHERE s.id LIKE 'pdf:%' AND s.year BETWEEN ? AND ?
                                            AND EXISTS (SELECT 1 FROM appearance a WHERE a.session_id = s.id AND a.page IS NOT NULL)
                                            ORDER BY s.id""", (lo, hi))]
        for sid in rng.sample(ids, min(per_era, len(ids))):
            year, code, title, doc_id = con.execute("SELECT year, code, title, source_document_id FROM session WHERE id=?", (sid,)).fetchone()
            rows = con.execute("""SELECT a.id, a.role, a.name_as_printed, a.affiliation_as_printed, a.paper_title, a.page, a.bbox, i.name, i.two_year
                                  FROM appearance a LEFT JOIN institution i ON i.id = a.institution_id
                                  WHERE a.session_id=? ORDER BY a.ord, a.id""", (sid,)).fetchall()
            pdf = os.path.join(pdf_dir, doc_id.split("-", 2)[2])
            imgs = []
            for pg in sorted({int(r[5]) for r in rows if r[5]}):
                boxes = [ast.literal_eval(r[6]) for r in rows if r[5] and int(r[5]) == pg and r[6]]
                name = f"{sid.replace(':', '_').replace('.', '-')}_p{pg}.jpg"
                render(pdf, pg, boxes, code, os.path.join(out_dir, "img", name))
                imgs.append({"src": "img/" + name, "page": pg})
            cards.append({"id": sid, "era": f"{lo}–{hi}", "year": year, "code": code, "title": title,
                          "pdf": os.path.basename(pdf), "imgs": imgs,
                          "rows": [{"aid": r[0], "role": r[1], "name": r[2], "aff": r[3], "paper": r[4],
                                    "inst": r[7], "two": r[8]} for r in rows]})
    page = TEMPLATE.replace("__DATA__", json.dumps(cards, ensure_ascii=False).replace("</", "<\\/"))
    page = page.replace("__SEED__", str(seed)).replace("__N__", str(len(cards)))
    open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8").write(page)
    print(f"review sample: {len(cards)} sessions, {sum(len(c['rows']) for c in cards)} appearances -> {os.path.join(out_dir, 'index.html')}")

TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PDF parse review</title>
<style>
:root { --bg:#f6f7f9; --surface:#fff; --fg:#1c2230; --muted:#5a6478; --rule:#d9dee7; --accent:#2b4c8c; --bad:#a3271a; --badbg:#fbeae7; }
@media (prefers-color-scheme: dark) { :root { --bg:#12151c; --surface:#1a1f29; --fg:#e4e8f0; --muted:#9aa4b8; --rule:#2c3442; --accent:#8fb0f0; --bad:#f08a7a; --badbg:#3a1d19; color-scheme: dark; } }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg); font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; padding: 0 16px 4rem; }
header { position: sticky; top: 0; background: var(--bg); border-bottom: 1px solid var(--rule); padding: .8rem 0; z-index: 2; display: flex; flex-wrap: wrap; gap: .6rem 1.2rem; align-items: center; }
h1 { font-size: 1.15rem; margin: 0; }
.prog { color: var(--muted); font-size: .9rem; font-variant-numeric: tabular-nums; }
button { font: inherit; font-size: .9rem; border: 1px solid var(--rule); background: var(--surface); color: var(--fg); border-radius: 4px; padding: .3rem .8rem; cursor: pointer; }
button.primary { background: var(--accent); border-color: var(--accent); color: var(--surface); }
.intro { max-width: 52rem; color: var(--muted); font-size: .92rem; margin: 1rem 0; }
.card { background: var(--surface); border: 1px solid var(--rule); border-radius: 6px; margin: 1.2rem 0; display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr); }
@media (max-width: 900px) { .card { grid-template-columns: 1fr; } }
.card.done { border-color: var(--accent); }
.imgs { padding: .8rem; border-right: 1px solid var(--rule); overflow: auto; max-height: 80vh; }
.imgs img { width: 100%; height: auto; display: block; margin-bottom: .6rem; border: 1px solid var(--rule); }
.imgs .cap { font-size: .78rem; color: var(--muted); font-family: ui-monospace, Consolas, monospace; }
.parsed { padding: .8rem 1rem; min-width: 0; }
.meta { font-family: ui-monospace, Consolas, monospace; font-size: .8rem; color: var(--muted); }
h2 { font-size: 1.05rem; margin: .2rem 0 .6rem; }
table { border-collapse: collapse; width: 100%; font-size: .86rem; }
th, td { text-align: left; vertical-align: top; padding: .35rem .4rem; border-bottom: 1px solid var(--rule); }
th { font-size: .72rem; text-transform: uppercase; letter-spacing: .03em; color: var(--muted); font-weight: 600; }
td.ck { text-align: center; width: 2.4rem; }
tr.bad td { background: var(--badbg); }
.paper { color: var(--muted); font-style: italic; }
.inst { color: var(--muted); font-size: .8rem; }
.inst.none { color: var(--bad); }
.tw { font-size: .7rem; border: 1px solid var(--rule); border-radius: 999px; padding: 0 .35rem; margin-left: .3rem; font-style: normal; }
.sess { display: flex; flex-wrap: wrap; gap: .4rem 1rem; margin: .8rem 0 .4rem; font-size: .88rem; }
textarea { width: 100%; font: inherit; font-size: .88rem; min-height: 3.2rem; border: 1px solid var(--rule); border-radius: 4px; background: var(--bg); color: var(--fg); padding: .4rem; }
label { cursor: pointer; }
input[type=checkbox] { width: 1.05rem; height: 1.05rem; accent-color: var(--accent); }
</style></head><body>
<header><h1>PDF parse review</h1><span class="prog" id="prog"></span>
<button class="primary" id="dl">Download CSV</button><button id="clear">Clear my ticks</button></header>
<p class="intro">__N__ sessions sampled at random (seed __SEED__) from four layout eras of the PDF programs, 2004–2023. Left: the program page; a red box marks the first line of each entry the parser stored, so a person with no box was missed. Right: what the parser stored. Each row starts with every box ticked; untick anything that is wrong. <b>Name</b>: the name as printed. <b>Aff</b>: the affiliation as printed. <b>Inst</b>: the institution it was matched to (red when none was found, which counts as correct if the affiliation is not a college). Then say whether the session code and title are right, and note anyone the parser missed or any extra row. Ticks are saved in this browser; Download CSV writes them out.</p>
<main id="main"></main>
<script>
const CARDS = __DATA__;
const KEY = "cccc-review-__SEED__";
let state = {};
try { state = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) {}
const save = () => { try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {} progress(); };
const esc = s => (s == null ? "" : String(s)).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const get = (k, d) => (k in state ? state[k] : d);
function progress() {
  const n = CARDS.filter(c => get(c.id + ":done", false)).length;
  document.getElementById("prog").textContent = `${n} of ${CARDS.length} sessions marked reviewed`;
  CARDS.forEach(c => document.getElementById("c-" + c.id).classList.toggle("done", get(c.id + ":done", false)));
}
function render() {
  document.getElementById("main").innerHTML = CARDS.map(c => `
  <article class="card" id="c-${esc(c.id)}">
    <div class="imgs">${c.imgs.map(i => `<div class="cap">${esc(c.pdf)} · page ${i.page}</div><img src="${esc(i.src)}" alt="Program page ${i.page} for session ${esc(c.code)}" loading="lazy">`).join("")}</div>
    <div class="parsed">
      <div class="meta">${esc(c.era)} · ${c.year} · ${esc(c.id)}</div>
      <h2>${esc(c.code)} ${esc(c.title || "(no title)")}</h2>
      <table><thead><tr><th>Role</th><th>Parsed</th><th class="ck">Name</th><th class="ck">Aff</th><th class="ck">Inst</th></tr></thead><tbody>
      ${c.rows.map(r => `<tr data-aid="${r.aid}"><td>${esc(r.role)}</td><td><b>${esc(r.name)}</b><br>${esc(r.aff)}${r.paper ? `<br><span class="paper">“${esc(r.paper)}”</span>` : ""}<br>
        <span class="inst ${r.inst ? "" : "none"}">→ ${r.inst ? esc(r.inst) : "no institution"}${r.two ? '<span class="tw">two-year</span>' : ""}</span></td>
        ${["name", "aff", "inst"].map(f => `<td class="ck"><input type="checkbox" data-k="${c.id}:${r.aid}:${f}" ${get(c.id + ":" + r.aid + ":" + f, true) ? "checked" : ""} aria-label="${f} correct"></td>`).join("")}</tr>`).join("")}
      </tbody></table>
      <div class="sess">
        <label><input type="checkbox" data-k="${c.id}:code" ${get(c.id + ":code", true) ? "checked" : ""}> Code right</label>
        <label><input type="checkbox" data-k="${c.id}:title" ${get(c.id + ":title", true) ? "checked" : ""}> Title complete</label>
        <label><input type="checkbox" data-k="${c.id}:done" ${get(c.id + ":done", false) ? "checked" : ""}> <b>Reviewed</b></label>
      </div>
      <textarea data-k="${c.id}:note" placeholder="Missed people, extra rows, anything else">${esc(get(c.id + ":note", ""))}</textarea>
    </div>
  </article>`).join("");
  document.querySelectorAll("tr[data-aid]").forEach(tr => {
    const mark = () => tr.classList.toggle("bad", [...tr.querySelectorAll("input")].some(i => !i.checked));
    tr.addEventListener("change", mark); mark();
  });
  progress();
}
document.addEventListener("change", e => { const k = e.target.dataset.k; if (!k) return; state[k] = e.target.checked; save(); });
document.addEventListener("input", e => { const k = e.target.dataset.k; if (!k || e.target.type === "checkbox") return; state[k] = e.target.value; save(); });
document.getElementById("clear").addEventListener("click", () => { if (confirm("Clear every tick and note on this page?")) { state = {}; save(); render(); } });
document.getElementById("dl").addEventListener("click", () => {
  const q = v => `"${String(v == null ? "" : v).replace(/"/g, '""')}"`;
  const lines = [["session_id", "era", "year", "code", "reviewed", "code_ok", "title_ok", "appearance_id", "name", "affiliation", "institution", "name_ok", "aff_ok", "inst_ok", "note"].join(",")];
  CARDS.forEach(c => {
    const s = [c.id, c.era, c.year, c.code, get(c.id + ":done", false), get(c.id + ":code", true), get(c.id + ":title", true)];
    c.rows.forEach(r => lines.push([...s, r.aid, r.name, r.aff, r.inst, ...["name", "aff", "inst"].map(f => get(c.id + ":" + r.aid + ":" + f, true)), get(c.id + ":note", "")].map(q).join(",")));
  });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob(["\\ufeff" + lines.join("\\r\\n")], {type: "text/csv"}));
  a.download = "pdf-parse-review-__SEED__.csv"; a.click();
});
render();
</script></body></html>
"""

if __name__ == "__main__":
    main(*sys.argv[1:6])
