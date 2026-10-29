"""Build a review page for the name clusters that build_persons.py could not settle.

Usage: python -I src/review_people.py <db_path> <out.html> ["data/person_decisions*.csv"]
Lists every cluster still marked review ('exact-name;review', or 'near-name-reviewed;review' where a merge created the overlap), largest first, as a year-by-year timeline of
institution, session and paper title. For each, choose "Same person", "Different people"
or "Not sure", then "Download decisions" writes person_decisions.csv in the form
build_persons.py reads: save it in data/ (any name starting person_decisions) and
rebuild. Clusters already decided in those files are left off the page. Choices are also kept in the
browser's local storage. Open the page in an ordinary browser; it needs no server.
"""
import csv, glob, json, os, sqlite3, sys

def main(db_path, out_path, decisions_csv="data/person_decisions*.csv"):
    con = sqlite3.connect(db_path)
    done = set()
    for path in glob.glob(decisions_csv):
        done |= {r["person_id"] for r in csv.DictReader(open(path, encoding="utf-8-sig"))}
    people = con.execute("""SELECT p.id, p.display_name, count(*) n FROM person p JOIN appearance a ON a.person_id = p.id
                            WHERE p.method LIKE '%;review' GROUP BY p.id ORDER BY n DESC, p.display_name""").fetchall()
    clusters = []
    for pid, name, n in people:
        if pid in done:
            continue
        rows = con.execute("""SELECT s.year, s.code, s.title, a.role, a.affiliation_as_printed, a.paper_title, i.name, i.two_year
                              FROM appearance a JOIN session s ON s.id = a.session_id
                              LEFT JOIN institution i ON i.id = a.institution_id
                              WHERE a.person_id = ? ORDER BY s.year, s.code""", (pid,)).fetchall()
        clusters.append({"id": pid, "name": name, "n": n,
                         "rows": [{"y": r[0], "code": r[1], "stitle": r[2], "role": r[3], "aff": r[4],
                                   "paper": r[5], "inst": r[6], "two": r[7]} for r in rows]})
    page = TEMPLATE.replace("__DATA__", json.dumps(clusters, ensure_ascii=False).replace("</", "<\\/"))
    page = page.replace("__N__", str(len(clusters)))
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    open(out_path, "w", encoding="utf-8").write(page)
    print(f"people review: {len(clusters)} clusters ({len(done)} already decided) -> {out_path}")

TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Name cluster review</title>
<style>
:root { --bg:#f6f7f9; --surface:#fff; --fg:#1c2230; --muted:#5a6478; --rule:#d9dee7; --accent:#2b4c8c; --same:#1d6b45; --diff:#a3271a; }
@media (prefers-color-scheme: dark) { :root { --bg:#12151c; --surface:#1a1f29; --fg:#e4e8f0; --muted:#9aa4b8; --rule:#2c3442; --accent:#8fb0f0; --same:#6fd0a0; --diff:#f08a7a; color-scheme: dark; } }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg); font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; padding: 0 16px 4rem; }
header { position: sticky; top: 0; background: var(--bg); border-bottom: 1px solid var(--rule); padding: .8rem 0; z-index: 2; display: flex; flex-wrap: wrap; gap: .6rem 1.2rem; align-items: center; }
h1 { font-size: 1.15rem; margin: 0; }
.prog { color: var(--muted); font-size: .9rem; font-variant-numeric: tabular-nums; }
button { font: inherit; font-size: .9rem; border: 1px solid var(--rule); background: var(--surface); color: var(--fg); border-radius: 4px; padding: .3rem .8rem; cursor: pointer; }
button.primary { background: var(--accent); border-color: var(--accent); color: var(--surface); }
.intro { max-width: 52rem; color: var(--muted); font-size: .92rem; margin: 1rem 0; }
.card { background: var(--surface); border: 1px solid var(--rule); border-left: 4px solid var(--rule); border-radius: 6px; margin: 1rem 0; padding: .8rem 1rem; max-width: 66rem; }
.card[data-d="same"] { border-left-color: var(--same); } .card[data-d="different"] { border-left-color: var(--diff); } .card[data-d="unsure"] { border-left-color: var(--muted); }
h2 { font-size: 1.05rem; margin: 0 0 .1rem; }
.meta { font-family: ui-monospace, Consolas, monospace; font-size: .78rem; color: var(--muted); }
table { border-collapse: collapse; width: 100%; font-size: .86rem; margin: .5rem 0; }
th, td { text-align: left; vertical-align: top; padding: .3rem .4rem; border-bottom: 1px solid var(--rule); }
th { font-size: .72rem; text-transform: uppercase; letter-spacing: .03em; color: var(--muted); font-weight: 600; }
td.y { font-family: ui-monospace, Consolas, monospace; white-space: nowrap; }
.paper { color: var(--muted); font-style: italic; }
.sw { display: inline-block; width: .7rem; height: .7rem; border-radius: 2px; margin-right: .35rem; vertical-align: -1px; }
.tw { font-size: .7rem; border: 1px solid var(--rule); border-radius: 999px; padding: 0 .35rem; margin-left: .3rem; }
.choices { display: flex; flex-wrap: wrap; gap: .4rem 1rem; align-items: center; font-size: .9rem; }
.choices input[type=text] { flex: 1 1 16rem; font: inherit; font-size: .88rem; border: 1px solid var(--rule); border-radius: 4px; background: var(--bg); color: var(--fg); padding: .3rem .4rem; }
label { cursor: pointer; }
.tbl { overflow-x: auto; }
</style></head><body>
<header><h1>Name cluster review</h1><span class="prog" id="prog"></span>
<button class="primary" id="dl">Download decisions</button><button id="clear">Clear my choices</button></header>
<p class="intro">__N__ names in the corpus appear at two institutions in the same year, or go back to an earlier institution, so the build can't tell one person with a career from two people with the same name. Each card lists every appearance, oldest first, with the institution color-coded. Choose <b>Same person</b> or <b>Different people</b> (the build then splits the name into one person per institution), or <b>Not sure</b>. The biggest clusters come first. A wrong institution match is "Same person", with a note. Download decisions writes <code>person_decisions.csv</code>: save it in the corpus folder's <code>data</code> folder (a second download named <code>person_decisions (1).csv</code> is fine) and rebuild. Decided names drop off this page on the next build.</p>
<main id="main"></main>
<script>
const CLUSTERS = __DATA__;
const KEY = "cccc-people-review";
const PALETTE = ["#2f6fc0", "#b5651d", "#1b8a86", "#6a45b8", "#c99a1e", "#a3271a", "#5a6478", "#3d8c40"];
let state = {};
try { state = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) {}
const save = () => { try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {} progress(); };
const esc = s => (s == null ? "" : String(s)).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
function progress() {
  const n = CLUSTERS.filter(c => (state[c.id] || {}).d).length;
  document.getElementById("prog").textContent = `${n} of ${CLUSTERS.length} decided`;
  CLUSTERS.forEach(c => document.getElementById("c-" + c.id).dataset.d = (state[c.id] || {}).d || "");
}
function render() {
  document.getElementById("main").innerHTML = CLUSTERS.map(c => {
    const insts = [...new Set(c.rows.map(r => r.inst || "(no institution)"))];
    const color = i => PALETTE[insts.indexOf(i || "(no institution)") % PALETTE.length];
    const s = state[c.id] || {};
    const opt = (v, label) => `<label><input type="radio" name="d-${esc(c.id)}" value="${v}" ${s.d === v ? "checked" : ""}> ${label}</label>`;
    return `<article class="card" id="c-${esc(c.id)}">
      <h2>${esc(c.name)}</h2><div class="meta">${esc(c.id)} · ${c.n} appearances · ${insts.length} institutions</div>
      <div class="tbl"><table><thead><tr><th>Year</th><th>Institution</th><th>As printed</th><th>Session</th></tr></thead><tbody>
      ${c.rows.map(r => `<tr><td class="y">${r.y}</td><td><span class="sw" style="background:${color(r.inst)}"></span>${esc(r.inst || "(no institution)")}${r.two ? '<span class="tw">two-year</span>' : ""}</td>
        <td>${esc(r.aff)}</td><td>${esc(r.code)} ${esc(r.stitle)}${r.paper ? `<br><span class="paper">“${esc(r.paper)}”</span>` : ""}</td></tr>`).join("")}
      </tbody></table></div>
      <div class="choices" data-id="${esc(c.id)}">${opt("same", "Same person")}${opt("different", "Different people")}${opt("unsure", "Not sure")}
        <input type="text" placeholder="Note (optional)" value="${esc(s.note || "")}"></div>
    </article>`;
  }).join("");
  progress();
}
document.addEventListener("change", e => {
  const box = e.target.closest(".choices"); if (!box || e.target.type !== "radio") return;
  const id = box.dataset.id; state[id] = Object.assign(state[id] || {}, {d: e.target.value}); save();
});
document.addEventListener("input", e => {
  const box = e.target.closest(".choices"); if (!box || e.target.type !== "text") return;
  const id = box.dataset.id; state[id] = Object.assign(state[id] || {}, {note: e.target.value}); save();
});
document.getElementById("clear").addEventListener("click", () => { if (confirm("Clear every choice on this page?")) { state = {}; save(); render(); } });
document.getElementById("dl").addEventListener("click", () => {
  const q = v => `"${String(v == null ? "" : v).replace(/"/g, '""')}"`;
  const lines = ["person_id,decision,note"];
  CLUSTERS.forEach(c => { const s = state[c.id]; if (s && s.d) lines.push([c.id, s.d, s.note || ""].map(q).join(",")); });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([lines.join("\\r\\n") + "\\r\\n"], {type: "text/csv"}));
  a.download = "person_decisions.csv"; a.click();
});
render();
</script></body></html>
"""

if __name__ == "__main__":
    main(*sys.argv[1:4])
