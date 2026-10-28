"""Find name clusters that are probably one person printed two ways, for review.

Usage: python -I src/near_names.py <db_path> <out.html> ["data/name_merges*.csv"]
build_persons.py joins only identical names. This finds pairs of clusters whose names differ
in one of four ways, and keeps only pairs that share at least one institution:
  middle    a middle name or initial added or dropped  (Carrie Leverenz / Carrie Shively Leverenz)
  nickname  a common short form of the first name      (Jim Brown / James Brown)
  surname   one part of a hyphenated surname           (Kellie Sharp / Kellie Sharp-Hoskins)
  spelling  one letter different in the surname        (Adler-Kasner / Adler-Kassner)
The page groups pairs by kind, each as two timelines side by side. "Same person" decisions,
downloaded as name_merges.csv into data/, are merged by build_persons.py on the next build.
Pairs already decided are left off the page. Pairs with no shared institution are only counted.
"""
import collections, csv, glob, json, os, re, sqlite3, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_persons import norm

NICK = {"bill": "william", "will": "william", "billy": "william", "bob": "robert", "rob": "robert", "bobby": "robert",
        "jim": "james", "jimmy": "james", "mike": "michael", "liz": "elizabeth", "beth": "elizabeth", "betsy": "elizabeth",
        "kate": "katherine", "kathy": "katherine", "katie": "katherine", "kathryn": "katherine", "kathleen": "katherine",
        "catherine": "katherine", "cathy": "katherine", "chris": "christopher", "tom": "thomas", "joe": "joseph",
        "dan": "daniel", "dave": "david", "steve": "stephen", "steven": "stephen", "sam": "samuel", "ben": "benjamin",
        "matt": "matthew", "pat": "patricia", "patty": "patricia", "jen": "jennifer", "jenny": "jennifer", "jenn": "jennifer",
        "sue": "susan", "ed": "edward", "ted": "edward", "rick": "richard", "dick": "richard", "rich": "richard",
        "tony": "anthony", "andy": "andrew", "drew": "andrew", "greg": "gregory", "jeff": "jeffrey", "jeffery": "jeffrey",
        "nick": "nicholas", "peggy": "margaret", "maggie": "margaret", "meg": "margaret", "debbie": "deborah", "deb": "deborah",
        "barb": "barbara", "cindy": "cynthia", "vicki": "victoria", "alex": "alexander", "tim": "timothy", "jon": "jonathan",
        "ron": "ronald", "don": "donald", "doug": "douglas", "larry": "lawrence", "jerry": "gerald", "gerry": "gerald",
        "becky": "rebecca", "sandy": "sandra", "pam": "pamela", "fred": "frederick", "phil": "phillip", "philip": "phillip",
        "jackie": "jacquelyn", "abby": "abigail", "nate": "nathan", "zach": "zachary", "josh": "joshua", "ken": "kenneth",
        "lou": "louis", "mandy": "amanda", "nicky": "nicole", "toni": "antonia", "vince": "vincent"}
SUFFIX = {"jr", "sr", "ii", "iii", "iv", "dr"}

def tokens(name):
    return [w for w in re.sub(r"[^a-z\- ]", " ", norm(name).replace("'", "")).split() if w not in SUFFIX]

def first_last(name):
    t = tokens(name)
    if len(t) < 2 or len(t[0]) < 2:
        return None
    return t[0], t[-1], t[1:-1]

def one_edit(a, b):
    if a == b or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    if len(a) > len(b):
        a, b = b, a
    return any(b[:i] + b[i + 1:] == a for i in range(len(b)))

def kind(n1, n2):
    """How two names differ, or None if they don't look like one person."""
    a, b = first_last(n1), first_last(n2)
    if not a or not b:
        return None
    (f1, l1, m1), (f2, l2, m2) = a, b
    same_first = f1 == f2
    nick_first = not same_first and NICK.get(f1, f1) == NICK.get(f2, f2)
    if not (same_first or nick_first):
        return None
    if l1 == l2:
        if nick_first:
            return "nickname"
        if m1 != m2:
            # a middle name or initial on one side only, or an initial against its full name
            if not m1 or not m2 or (len(m1) == len(m2) and all(x[0] == y[0] for x, y in zip(m1, m2))):
                return "middle"
        return None
    if "-" in l1 + l2:
        p1, p2 = set(l1.split("-")), set(l2.split("-"))
        if (p1 < p2 or p2 < p1) and min(len(p1), len(p2)) == 1:
            return "surname"
    if len(l1) >= 5 and one_edit(l1, l2) and same_first:
        return "spelling"
    return None

def main(db_path, out_path, merges_csv="data/name_merges*.csv"):
    con = sqlite3.connect(db_path)
    done = set()
    for path in glob.glob(merges_csv):
        done |= {tuple(sorted((r["a"], r["b"]))) for r in csv.DictReader(open(path, encoding="utf-8-sig"))}
    names = dict(con.execute("SELECT id, display_name FROM person"))
    insts, years = collections.defaultdict(set), collections.defaultdict(set)
    for pid, inst, y in con.execute("SELECT a.person_id, a.institution_id, s.year FROM appearance a JOIN session s ON s.id = a.session_id"):
        years[pid].add(y)
        if inst:
            insts[pid].add(inst)
    # candidates: same surname (or a surname part, or a near spelling) under the same first-name form
    buckets = collections.defaultdict(set)
    for pid, n in names.items():
        fl = first_last(n)
        if not fl:
            continue
        f, l, _ = fl
        for part in {l, *l.split("-")}:
            if len(part) > 2:
                buckets[(NICK.get(f, f), part)].add(pid)
                buckets[(NICK.get(f, f), part[:4], "~")].add(pid)  # near spellings share a prefix
    pairs, no_shared = {}, set()
    for group in buckets.values():
        group = sorted(group)
        for i, p in enumerate(group):
            for q in group[i + 1:]:
                key = (p, q)
                if key in pairs or key in no_shared or key in done:
                    continue
                k = kind(names[p], names[q])
                if not k:
                    continue
                if not insts[p] & insts[q]:
                    no_shared.add(key)
                    continue
                pairs[key] = k
    inst_names = dict(con.execute("SELECT id, name FROM institution"))

    def timeline(pid):
        return [{"y": r[0], "code": r[1], "stitle": r[2], "role": r[3], "aff": r[4], "paper": r[5], "inst": r[6]}
                for r in con.execute("""SELECT s.year, s.code, s.title, a.role, a.affiliation_as_printed, a.paper_title, i.name
                                        FROM appearance a JOIN session s ON s.id = a.session_id
                                        LEFT JOIN institution i ON i.id = a.institution_id
                                        WHERE a.person_id = ? ORDER BY s.year, s.code""", (pid,))]
    order = {"middle": 0, "nickname": 1, "spelling": 2, "surname": 3}
    cards = []
    for (p, q), k in sorted(pairs.items(), key=lambda t: (order[t[1]], names[t[0][0]])):
        shared = sorted(inst_names.get(i, i) for i in insts[p] & insts[q])
        cards.append({"id": f"{p}|{q}", "a": p, "b": q, "kind": k, "an": names[p], "bn": names[q],
                      "shared": shared, "overlap": sorted(years[p] & years[q]), "ta": timeline(p), "tb": timeline(q)})
    counts = collections.Counter(c["kind"] for c in cards)
    page = TEMPLATE.replace("__DATA__", json.dumps(cards, ensure_ascii=False).replace("</", "<\\/"))
    page = page.replace("__N__", f"{len(cards):,}")
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    open(out_path, "w", encoding="utf-8").write(page)
    print(f"near names: {len(cards)} pairs sharing an institution ({dict(counts)}); "
          f"{len(no_shared)} more with no shared institution left off; {len(done)} already decided -> {out_path}")

TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Near-name review</title>
<style>
:root { --bg:#f6f7f9; --surface:#fff; --fg:#1c2230; --muted:#5a6478; --rule:#d9dee7; --accent:#2b4c8c; --same:#1d6b45; --diff:#a3271a; }
@media (prefers-color-scheme: dark) { :root { --bg:#12151c; --surface:#1a1f29; --fg:#e4e8f0; --muted:#9aa4b8; --rule:#2c3442; --accent:#8fb0f0; --same:#6fd0a0; --diff:#f08a7a; color-scheme: dark; } }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg); font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; padding: 0 16px 4rem; }
header { position: sticky; top: 0; background: var(--bg); border-bottom: 1px solid var(--rule); padding: .8rem 0; z-index: 2; display: flex; flex-wrap: wrap; gap: .6rem 1.2rem; align-items: center; }
h1 { font-size: 1.15rem; margin: 0; }
.prog { color: var(--muted); font-size: .9rem; font-variant-numeric: tabular-nums; }
button, select { font: inherit; font-size: .9rem; border: 1px solid var(--rule); background: var(--surface); color: var(--fg); border-radius: 4px; padding: .3rem .8rem; cursor: pointer; }
button.primary { background: var(--accent); border-color: var(--accent); color: var(--surface); }
.intro { max-width: 52rem; color: var(--muted); font-size: .92rem; margin: 1rem 0; }
.group { display: flex; flex-wrap: wrap; gap: .5rem 1rem; align-items: baseline; margin: 2rem 0 .5rem; max-width: 72rem; }
.group h2 { font-size: 1.05rem; margin: 0; }
.group p { margin: 0; color: var(--muted); font-size: .88rem; flex-basis: 100%; }
.card { background: var(--surface); border: 1px solid var(--rule); border-left: 4px solid var(--rule); border-radius: 6px; margin: .8rem 0; padding: .7rem 1rem; max-width: 72rem; }
.card[data-d="same"] { border-left-color: var(--same); } .card[data-d="different"] { border-left-color: var(--diff); } .card[data-d="unsure"] { border-left-color: var(--muted); }
h3 { font-size: 1rem; margin: 0 0 .1rem; }
.meta { font-size: .8rem; color: var(--muted); }
.pair { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
@media (max-width: 760px) { .pair { grid-template-columns: 1fr; } }
table { border-collapse: collapse; width: 100%; font-size: .84rem; margin: .4rem 0; }
th, td { text-align: left; vertical-align: top; padding: .25rem .35rem; border-bottom: 1px solid var(--rule); }
th { font-size: .72rem; text-transform: uppercase; letter-spacing: .03em; color: var(--muted); font-weight: 600; }
td.y { font-family: ui-monospace, Consolas, monospace; white-space: nowrap; }
.paper { color: var(--muted); font-style: italic; }
.choices { display: flex; flex-wrap: wrap; gap: .4rem 1rem; align-items: center; font-size: .9rem; }
.choices input[type=text] { flex: 1 1 16rem; font: inherit; font-size: .88rem; border: 1px solid var(--rule); border-radius: 4px; background: var(--bg); color: var(--fg); padding: .3rem .4rem; }
label { cursor: pointer; }
.tbl { overflow-x: auto; }
</style></head><body>
<header><h1>Near-name review</h1><span class="prog" id="prog"></span>
<button class="primary" id="dl">Download decisions</button><button id="clear">Clear my choices</button></header>
<p class="intro">The build joins people only when their names match exactly. These __N__ pairs are names that differ by a middle name or initial, a nickname, one part of a hyphenated surname, or one letter, and that share at least one institution. Each card shows both names' appearances side by side. Choose <b>Same person</b> to merge them on the next build, <b>Different people</b> to keep them apart, or <b>Not sure</b>. Each group has a button that marks every undecided pair in it as the same person; individual choices still override it. The surname group needs the most care (Susan Miller and Susan Miller-Cochran are two people). Download decisions writes <code>name_merges.csv</code>: save it in the corpus folder's <code>data</code> folder and rebuild.</p>
<main id="main"></main>
<script>
const CARDS = __DATA__;
const KEY = "cccc-near-names";
const GROUPS = [["middle", "Middle name or initial", "One name has a middle name or initial the other lacks, or an initial where the other has the full name."],
                ["nickname", "Nickname", "A short form of the first name: Jim and James, Kathy and Katherine."],
                ["spelling", "One letter different", "The surnames differ by one letter, usually a typo in one program."],
                ["surname", "Part of a hyphenated surname", "One name has a hyphenated surname and the other has one part of it. A name change is likely, but so is a different person."]];
let state = {};
try { state = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) {}
const save = () => { try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {} progress(); };
const esc = s => (s == null ? "" : String(s)).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
function progress() {
  const n = CARDS.filter(c => (state[c.id] || {}).d).length;
  document.getElementById("prog").textContent = `${n} of ${CARDS.length} decided`;
  CARDS.forEach(c => { const el = document.getElementById("c-" + c.id); el.dataset.d = (state[c.id] || {}).d || "";
    el.querySelectorAll("input[type=radio]").forEach(r => r.checked = r.value === (state[c.id] || {}).d); });
}
const table = rows => `<div class="tbl"><table><thead><tr><th>Year</th><th>As printed</th><th>Session</th></tr></thead><tbody>
  ${rows.map(r => `<tr><td class="y">${r.y}</td><td>${esc(r.aff)}</td><td>${esc(r.code)} ${esc(r.stitle)}${r.paper ? `<br><span class="paper">“${esc(r.paper)}”</span>` : ""}</td></tr>`).join("")}
  </tbody></table></div>`;
function card(c) {
  const s = state[c.id] || {};
  const opt = (v, label) => `<label><input type="radio" name="d-${esc(c.id)}" value="${v}" ${s.d === v ? "checked" : ""}> ${label}</label>`;
  return `<article class="card" id="c-${esc(c.id)}">
    <div class="meta">Shared institution: ${esc(c.shared.join("; "))}${c.overlap.length ? ` · both listed in ${c.overlap.join(", ")}` : ""}</div>
    <div class="pair"><div><h3>${esc(c.an)}</h3>${table(c.ta)}</div><div><h3>${esc(c.bn)}</h3>${table(c.tb)}</div></div>
    <div class="choices" data-id="${esc(c.id)}">${opt("same", "Same person")}${opt("different", "Different people")}${opt("unsure", "Not sure")}
      <input type="text" placeholder="Note (optional)" value="${esc(s.note || "")}"></div>
  </article>`;
}
function render() {
  document.getElementById("main").innerHTML = GROUPS.map(([k, title, blurb]) => {
    const cs = CARDS.filter(c => c.kind === k); if (!cs.length) return "";
    return `<section><div class="group"><h2>${title} (${cs.length})</h2><button data-all="${k}">Mark undecided as same person</button><p>${blurb}</p></div>${cs.map(card).join("")}</section>`;
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
document.addEventListener("click", e => {
  const k = e.target.dataset && e.target.dataset.all; if (!k) return;
  CARDS.filter(c => c.kind === k && !(state[c.id] || {}).d).forEach(c => state[c.id] = Object.assign(state[c.id] || {}, {d: "same"}));
  save();
});
document.getElementById("clear").addEventListener("click", () => { if (confirm("Clear every choice on this page?")) { state = {}; save(); render(); } });
document.getElementById("dl").addEventListener("click", () => {
  const q = v => `"${String(v == null ? "" : v).replace(/"/g, '""')}"`;
  const lines = ["a,b,decision,note"];
  CARDS.forEach(c => { const s = state[c.id]; if (s && s.d) lines.push([c.a, c.b, s.d, s.note || ""].map(q).join(",")); });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([lines.join("\\r\\n") + "\\r\\n"], {type: "text/csv"}));
  a.download = "name_merges.csv"; a.click();
});
render();
</script></body></html>
"""

if __name__ == "__main__":
    main(*sys.argv[1:4])
