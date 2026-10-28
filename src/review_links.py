"""Build a review page for the suggested links between convention papers and Pinakes articles.

Usage: python -I src/review_links.py <corpus.db> <suggestions.csv> <out.html> ["data/link_decisions*.csv"]
suggestions.csv comes from link_pinakes.py. The page lists every tier B and C pair, plus a
random 150 of tier A (to measure how often the strongest tier is right), as a paper beside the
article it may have become. Choose "Same work", "Different" or "Not sure" for each, then
"Download decisions" writes link_decisions.csv (session_id, person_id, pinakes_id, tier,
decision, note): save it in data/ (any name starting link_decisions) and run build_links.py.
Pairs already decided in those files are left off. Choices persist in the browser's local
storage. Tier D (a matching title but no matching author) is not offered: it is mostly wrong.
"""
import csv, glob, json, os, random, sqlite3, sys

def main(db_path, suggestions, out_path, decisions_glob="data/link_decisions*.csv"):
    done = set()
    for path in glob.glob(decisions_glob):
        for r in csv.DictReader(open(path, encoding="utf-8-sig")):
            done.add((r["session_id"], r["person_id"], r["pinakes_id"]))
    rows = list(csv.DictReader(open(suggestions, encoding="utf-8")))
    con = sqlite3.connect(db_path)
    sess = {sid: (code, title) for sid, code, title in con.execute("SELECT id, code, title FROM session")}
    random.seed(20261029)
    a = [r for r in rows if r["tier"] == "A"]
    random.shuffle(a)
    pick = [r for r in rows if r["tier"] in ("B", "C")] + a[:150]
    cards = []
    for r in pick:
        key = (r["session_id"], r["person_id"], r["pinakes_id"])
        if key in done:
            continue
        code, title = sess.get(r["session_id"], ("", ""))
        cards.append({"id": "|".join(key), "tier": r["tier"], "year": int(r["convention_year"]), "name": r["name_as_printed"],
                      "paper": r["paper_title"], "code": code, "stitle": title, "sid": r["session_id"], "pid": r["person_id"],
                      "wid": r["pinakes_id"], "atitle": r["article_title"], "aauth": r["article_authors"], "journal": r["journal"],
                      "ayear": int(r["article_year"]), "doi": r["doi"], "jac": float(r["title_overlap"])})
    order = {"B": 0, "C": 1, "A": 2}
    cards.sort(key=lambda c: (order[c["tier"]], c["year"], c["name"]))
    page = TEMPLATE.replace("__DATA__", json.dumps(cards, ensure_ascii=False).replace("</", "<\\/")).replace("__N__", str(len(cards)))
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    open(out_path, "w", encoding="utf-8").write(page)
    n = {t: sum(1 for c in cards if c["tier"] == t) for t in "ABC"}
    print(f"link review: {len(cards)} pairs (B {n['B']}, C {n['C']}, A sample {n['A']}); {len(done)} already decided -> {out_path}")

TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Convention paper to article review</title>
<style>
:root { --bg:#f6f7f9; --surface:#fff; --fg:#1c2230; --muted:#5a6478; --rule:#d9dee7; --accent:#2b4c8c; --same:#1d6b45; --diff:#a3271a; }
@media (prefers-color-scheme: dark) { :root { --bg:#12151c; --surface:#1a1f29; --fg:#e4e8f0; --muted:#9aa4b8; --rule:#2c3442; --accent:#8fb0f0; --same:#6fd0a0; --diff:#f08a7a; color-scheme: dark; } }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg); font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; padding: 0 16px 4rem; }
header { position: sticky; top: 0; background: var(--bg); border-bottom: 1px solid var(--rule); padding: .8rem 0; z-index: 2; display: flex; flex-wrap: wrap; gap: .6rem 1.2rem; align-items: center; }
h1 { font-size: 1.15rem; margin: 0; } .prog { color: var(--muted); font-size: .9rem; font-variant-numeric: tabular-nums; }
button { font: inherit; font-size: .9rem; border: 1px solid var(--rule); background: var(--surface); color: var(--fg); border-radius: 4px; padding: .3rem .8rem; cursor: pointer; }
button.primary { background: var(--accent); border-color: var(--accent); color: var(--surface); }
input[type=text] { font: inherit; font-size: .88rem; border: 1px solid var(--rule); border-radius: 4px; background: var(--bg); color: var(--fg); padding: .3rem .4rem; }
.intro { max-width: 56rem; color: var(--muted); font-size: .92rem; margin: 1rem 0; }
.group { margin: 2rem 0 .4rem; max-width: 64rem; display: flex; flex-wrap: wrap; gap: .4rem 1rem; align-items: baseline; } .group h2 { font-size: 1.05rem; margin: 0; } .group p { flex-basis: 100%; margin: 0; color: var(--muted); font-size: .86rem; }
.card { background: var(--surface); border: 1px solid var(--rule); border-left: 4px solid var(--rule); border-radius: 6px; margin: .7rem 0; padding: .7rem 1rem; max-width: 64rem; }
.card[data-d="match"] { border-left-color: var(--same); } .card[data-d="different"] { border-left-color: var(--diff); } .card[data-d="unsure"] { border-left-color: var(--muted); }
.pair { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; } @media (max-width: 760px) { .pair { grid-template-columns: 1fr; } }
.lab { font-size: .72rem; text-transform: uppercase; letter-spacing: .04em; color: var(--muted); } .ti { font-weight: 600; margin: .1rem 0; } .meta { font-size: .82rem; color: var(--muted); }
.choices { display: flex; flex-wrap: wrap; gap: .4rem 1rem; align-items: center; font-size: .9rem; margin-top: .5rem; } .choices input[type=text] { flex: 1 1 14rem; } label { cursor: pointer; }
a { color: var(--accent); }
</style></head><body>
<header><h1>Convention paper to article review</h1><span class="prog" id="prog"></span>
<button class="primary" id="dl">Download decisions</button><button id="clear">Clear my choices</button></header>
<p class="intro">Each card puts a paper listed in a CCCC program (left) beside a Pinakes article that may be the same work (right), found by matching words in the titles, the presenter's name among the authors, and the years. Choose <b>Same work</b> if the article is the paper (reworked or retitled is fine), <b>Different</b> if it is not, or <b>Not sure</b>. Tier B pairs have a close title; tier C pairs have only a partly overlapping title and need more care; the tier A cards are a random sample of the strongest tier, to measure how often it is right. __N__ pairs. Download decisions writes <code>link_decisions.csv</code>: save it in the corpus folder's <code>data</code> folder.</p>
<main id="main"></main>
<script>
const CARDS = __DATA__;
const KEY = "cccc-link-review";
const GROUPS = [["B", "Tier B: close title and an author match", "Mostly right. Watch for co-authored panels where two presenters match the same article."],
                ["C", "Tier C: partly overlapping title and an author match", "Judge by the topic and the lag. A reworked paper often keeps only a few title words."],
                ["A", "Tier A sample: near-identical title and an author match", "Expected to be right. These measure how often it is."]];
let state = {};
try { state = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) {}
const save = () => { try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {} progress(); };
const esc = s => (s == null ? "" : String(s)).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
function progress() {
  const n = CARDS.filter(c => (state[c.id] || {}).d).length;
  document.getElementById("prog").textContent = `${n} of ${CARDS.length} decided`;
  CARDS.forEach(c => { const el = document.getElementById("c-" + c.id.replace(/[^A-Za-z0-9]/g, "_")); if (!el) return; el.dataset.d = (state[c.id] || {}).d || "";
    el.querySelectorAll("input[type=radio]").forEach(r => r.checked = r.value === (state[c.id] || {}).d); });
}
function card(c) {
  const s = state[c.id] || {}, idn = c.id.replace(/[^A-Za-z0-9]/g, "_");
  const opt = (v, l) => `<label><input type="radio" name="d-${idn}" value="${v}" ${s.d === v ? "checked" : ""}> ${l}</label>`;
  const lag = c.ayear - c.year, lagText = lag === 0 ? "same year" : lag > 0 ? `${lag} year${lag === 1 ? "" : "s"} later` : `${-lag} year before`;
  return `<article class="card" id="c-${idn}"><div class="pair">
    <div><div class="lab">Paper in the ${c.year} program</div><div class="ti">${esc(c.paper)}</div><div class="meta">${esc(c.name)} · ${esc(c.code)} ${esc(c.stitle)}</div></div>
    <div><div class="lab">Pinakes article (${c.ayear}, ${lagText}) · title overlap ${c.jac}</div><div class="ti"><a href="https://pinakes.wacclearinghouse.org/article/${c.wid}" target="_blank" rel="noopener">${esc(c.atitle)}</a></div>
    <div class="meta">${esc(c.aauth)} · ${esc(c.journal)}${c.doi ? ` · <a href="https://doi.org/${esc(c.doi)}" target="_blank" rel="noopener">DOI</a>` : ""}</div></div></div>
    <div class="choices" data-id="${esc(c.id)}">${opt("match", "Same work")}${opt("different", "Different")}${opt("unsure", "Not sure")}<input type="text" placeholder="Note (optional)" value="${esc(s.note || "")}"></div></article>`;
}
function render() {
  document.getElementById("main").innerHTML = GROUPS.map(([t, title, blurb]) => {
    const cs = CARDS.filter(c => c.tier === t); if (!cs.length) return "";
    return `<section><div class="group"><h2>${title} (${cs.length})</h2>${t === "A" ? `<button data-all="A">Mark undecided as same work</button>` : ""}<p>${blurb}</p></div>${cs.map(card).join("")}</section>`;
  }).join("");
  progress();
}
document.addEventListener("change", e => { const b = e.target.closest(".choices"); if (!b || e.target.type !== "radio") return; const id = b.dataset.id; state[id] = Object.assign(state[id] || {}, {d: e.target.value}); save(); });
document.addEventListener("input", e => { const b = e.target.closest(".choices"); if (!b || e.target.type !== "text") return; const id = b.dataset.id; state[id] = Object.assign(state[id] || {}, {note: e.target.value}); save(); });
document.addEventListener("click", e => { const t = e.target.dataset && e.target.dataset.all; if (!t) return;
  CARDS.filter(c => c.tier === t && !(state[c.id] || {}).d).forEach(c => state[c.id] = Object.assign(state[c.id] || {}, {d: "match"})); save(); });
document.getElementById("clear").addEventListener("click", () => { if (confirm("Clear every choice on this page?")) { state = {}; save(); render(); } });
document.getElementById("dl").addEventListener("click", () => {
  const q = v => `"${String(v == null ? "" : v).replace(/"/g, '""')}"`;
  const lines = ["session_id,person_id,pinakes_id,tier,decision,note"];
  CARDS.forEach(c => { const s = state[c.id]; if (s && s.d) lines.push([c.sid, c.pid, c.wid, c.tier, s.d, s.note || ""].map(q).join(",")); });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([lines.join("\\r\\n") + "\\r\\n"], {type: "text/csv"}));
  a.download = "link_decisions.csv"; a.click();
});
render();
</script></body></html>
"""

if __name__ == "__main__":
    main(*sys.argv[1:5])
