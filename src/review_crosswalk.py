"""Build a review page for the area crosswalk (which families the yearly headings belong to).

Usage: python -I src/review_crosswalk.py <db_path> <out.html> <crosswalk.csv>
One card per heading name, with the years it appears, how many sessions carry it each year,
and a few session titles to judge by. Choose a family from the menu (or add a new one at the
top). Each card has a "by year" fold for the rare case where one name should map differently
in different years. "Download crosswalk" writes area_crosswalk.csv (year, area, group, sessions)
in the form parse_areas.py reads: save it over data/area_crosswalk.csv and rebuild.
Choices persist in the browser's local storage. The page needs no server.
"""
import collections, csv, json, os, sqlite3, sys

def main(db_path, out_path, crosswalk_csv):
    con = sqlite3.connect(db_path)
    cross = {}
    if os.path.exists(crosswalk_csv):
        cross = {(int(r["year"]), r["area"]): r["group"] for r in csv.DictReader(open(crosswalk_csv, encoding="utf-8"))}
    rows = con.execute("""SELECT year, area, count(*) FROM session WHERE area IS NOT NULL AND parent_id IS NULL
                          GROUP BY year, area ORDER BY area, year""").fetchall()
    names = collections.OrderedDict()
    for y, a, n in rows:
        names.setdefault(a, []).append((y, n))
    cards = []
    for a, yrs in names.items():
        sample = [r[0] for r in con.execute("""SELECT title FROM session WHERE area = ? AND parent_id IS NULL AND title IS NOT NULL
                                               ORDER BY year, code LIMIT 400""", (a,))]
        step = max(1, len(sample) // 4)
        sample = sample[::step][:4]
        cards.append({"name": a, "total": sum(n for _, n in yrs), "years": [{"y": y, "n": n, "g": cross.get((y, a), "")} for y, n in yrs], "sample": sample})
    cards.sort(key=lambda c: -c["total"])
    families = sorted({g for g in cross.values() if g})
    page = TEMPLATE.replace("__DATA__", json.dumps({"cards": cards, "families": families}, ensure_ascii=False).replace("</", "<\\/"))
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    open(out_path, "w", encoding="utf-8").write(page)
    print(f"crosswalk review: {len(cards)} heading names in {len(families)} families -> {out_path}")

TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Area crosswalk review</title>
<style>
:root { --bg:#f6f7f9; --surface:#fff; --fg:#1c2230; --muted:#5a6478; --rule:#d9dee7; --accent:#2b4c8c; --ok:#1d6b45; }
@media (prefers-color-scheme: dark) { :root { --bg:#12151c; --surface:#1a1f29; --fg:#e4e8f0; --muted:#9aa4b8; --rule:#2c3442; --accent:#8fb0f0; --ok:#6fd0a0; color-scheme: dark; } }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg); font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; padding: 0 16px 4rem; }
header { position: sticky; top: 0; background: var(--bg); border-bottom: 1px solid var(--rule); padding: .8rem 0; z-index: 2; display: flex; flex-wrap: wrap; gap: .6rem 1.2rem; align-items: center; }
h1 { font-size: 1.15rem; margin: 0; } .prog { color: var(--muted); font-size: .9rem; }
button, select, input[type=text] { font: inherit; font-size: .9rem; border: 1px solid var(--rule); background: var(--surface); color: var(--fg); border-radius: 4px; padding: .3rem .6rem; }
button { cursor: pointer; } button.primary { background: var(--accent); border-color: var(--accent); color: var(--surface); }
.intro { max-width: 54rem; color: var(--muted); font-size: .92rem; margin: 1rem 0; }
.card { background: var(--surface); border: 1px solid var(--rule); border-left: 4px solid var(--rule); border-radius: 6px; margin: .8rem 0; padding: .7rem 1rem; max-width: 64rem; }
.card.set { border-left-color: var(--ok); } .card.unset { border-left-color: #c0392b; }
h2 { font-size: 1.02rem; margin: 0 0 .15rem; } .meta { font-size: .8rem; color: var(--muted); }
.yrs { font-family: ui-monospace, Consolas, monospace; font-size: .78rem; margin: .3rem 0; }
.yrs span { display: inline-block; margin-right: .6rem; }
ul.s { margin: .3rem 0 .5rem 1rem; padding: 0; color: var(--muted); font-size: .86rem; }
.row { display: flex; flex-wrap: wrap; gap: .4rem .8rem; align-items: center; }
details { margin-top: .4rem; font-size: .85rem; } summary { cursor: pointer; color: var(--muted); }
details .y { display: flex; gap: .6rem; align-items: center; margin: .2rem 0; } details .y b { font-family: ui-monospace, Consolas, monospace; min-width: 4rem; }
</style></head><body>
<header><h1>Area crosswalk review</h1><span class="prog" id="prog"></span>
<button class="primary" id="dl">Download crosswalk</button>
<input type="text" id="newfam" placeholder="New family name" size="26"><button id="addfam">Add family</button><button id="clear">Clear my changes</button></header>
<p class="intro">CCCC renamed its proposal areas many times. Each card is one heading as the program printed it, with the years it appears and a few sessions under it. Choose the <b>family</b> it belongs to, so that trends can follow a topic across renamings. The menu starts with my draft. Choose <b>(none)</b> for a heading that is not a topic area (a convention theme track belongs in its own family). The "by year" fold lets one name belong to different families in different years. Download writes <code>area_crosswalk.csv</code>: save it over <code>data/area_crosswalk.csv</code> and rebuild.</p>
<main id="main"></main>
<script>
const DATA = __DATA__;
const KEY = "cccc-crosswalk-review";
let state = {fams: [], pick: {}};
try { state = Object.assign(state, JSON.parse(localStorage.getItem(KEY) || "{}")); } catch (e) {}
const save = () => { try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {} progress(); };
const esc = s => (s == null ? "" : String(s)).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const families = () => [...new Set([...DATA.families, ...state.fams])].sort();
const draft = (c, y) => (c.years.find(t => t.y === y) || {}).g || "";
// pick key: name|* for the whole name, name|year for a year override
const current = (c, y) => { const p = state.pick; const k = c.name + "|" + y, w = c.name + "|*";
  if (k in p) return p[k]; if (w in p) return p[w]; return draft(c, y); };
const opts = sel => `<option value="">(none)</option>` + families().map(f => `<option ${f === sel ? "selected" : ""}>${esc(f)}</option>`).join("");
function progress() {
  const changed = Object.keys(state.pick).length;
  const unset = DATA.cards.filter(c => c.years.some(t => !current(c, t.y))).length;
  document.getElementById("prog").textContent = `${DATA.cards.length} headings · ${changed} changed from the draft · ${unset} with no family`;
  DATA.cards.forEach(c => { const el = document.getElementById("c-" + CSS.escape(c.name)); if (!el) return;
    el.className = "card " + (c.years.some(t => !current(c, t.y)) ? "unset" : "set"); });
}
function render() {
  document.getElementById("main").innerHTML = DATA.cards.map((c, i) => {
    const whole = current(c, c.years[0].y);
    const same = c.years.every(t => current(c, t.y) === whole);
    return `<article class="card" id="c-${esc(c.name)}" data-i="${i}">
      <h2>${esc(c.name)}</h2><div class="meta">${c.total} sessions in ${c.years.length} years</div>
      <div class="yrs">${c.years.map(t => `<span>${t.y} (${t.n})</span>`).join("")}</div>
      <ul class="s">${c.sample.map(s => `<li>${esc(s)}</li>`).join("")}</ul>
      <div class="row"><label>Family <select data-i="${i}" data-y="*">${same ? opts(whole) : `<option value="__mixed" selected>(different by year)</option>` + opts("")}</select></label></div>
      <details ${same ? "" : "open"}><summary>By year</summary>${c.years.map(t => `<div class="y"><b>${t.y}</b><select data-i="${i}" data-y="${t.y}">${opts(current(c, t.y))}</select></div>`).join("")}</details>
    </article>`; }).join("");
  progress();
}
document.addEventListener("change", e => {
  const s = e.target.closest("select[data-i]"); if (!s) return;
  const c = DATA.cards[+s.dataset.i], y = s.dataset.y;
  if (s.value === "__mixed") return;
  if (y === "*") { c.years.forEach(t => delete state.pick[c.name + "|" + t.y]); state.pick[c.name + "|*"] = s.value; }
  else state.pick[c.name + "|" + y] = s.value;
  save(); render();
});
document.getElementById("addfam").addEventListener("click", () => { const v = document.getElementById("newfam").value.trim();
  if (v && !families().includes(v)) { state.fams.push(v); save(); render(); } document.getElementById("newfam").value = ""; });
document.getElementById("clear").addEventListener("click", () => { if (confirm("Throw away every change on this page?")) { state = {fams: [], pick: {}}; save(); render(); } });
document.getElementById("dl").addEventListener("click", () => {
  const q = v => `"${String(v == null ? "" : v).replace(/"/g, '""')}"`;
  const lines = ["year,area,group,sessions"];
  DATA.cards.forEach(c => c.years.forEach(t => { const g = current(c, t.y); if (g) lines.push([t.y, c.name, g, t.n].map(q).join(",")); }));
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([lines.join("\\r\\n") + "\\r\\n"], {type: "text/csv"}));
  a.download = "area_crosswalk.csv"; a.click();
});
render();
</script></body></html>
"""

if __name__ == "__main__":
    main(*sys.argv[1:4])
