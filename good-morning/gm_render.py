"""Draw PLAN.json as the good-morning day sheet (one self-contained HTML file).

Layout: a status strip (date, window, sources), the main-focus card, the
day's order as a track (unblock batch -> main -> secondary), then panels for
the unblock list, secondary work, questions, carry-over and stale work, the
"not today" list, ledger actions and FYI. Each item carries a rung stripe,
a source tag and an age chip.
"""
import html
import json
import tempfile
from datetime import datetime
from pathlib import Path

RUNG_LABEL = {"fire": "Fire", "unblock": "Unblock", "finish": "Finish", "focus": "Focus", "fyi": "FYI"}
SOURCE_LABEL = {"jira": "Jira", "chat": "Chat", "github": "GitHub", "ledger": "Ledger",
                "release": "Release", "calendar": "Calendar"}
STATE_LABEL = {"ok": "ok", "partial": "partial", "failed": "failed", "none": "off"}

CSS = """
/* Day sheet: status strip, focus card, ordered track, then panels in a 2-col grid. */
:root {
  --bg: #f5f6f8; --surface: #ffffff; --sunk: #eef0f4; --ink: #141821; --muted: #5d6573;
  --line: #dde1e8; --accent: #2b50c8; --accent-soft: #e6ecfb;
  --fire: #c62f2f; --fire-soft: #fbe9e9; --unblock: #b26a00; --unblock-soft: #fdf1dc;
  --finish: #0f7c74; --finish-soft: #e0f3f1; --focus: #6a43c2; --focus-soft: #efe9fb;
  --fyi: #6b7280; --fyi-soft: #eef0f3; --ok: #1d7f43; --warn: #b26a00; --bad: #c62f2f;
  --display: "Bricolage Grotesque", "Avenir Next", "Segoe UI", system-ui, sans-serif;
  --body: "IBM Plex Sans", "Segoe UI", system-ui, -apple-system, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, "SF Mono", Menlo, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #0f1218; --surface: #171b23; --sunk: #1d222c; --ink: #e8ebf1; --muted: #9aa3b2;
  --line: #2a303c; --accent: #8aa5ff; --accent-soft: #1f2a4a;
  --fire: #ff7b7b; --fire-soft: #3a1d1f; --unblock: #f2b35a; --unblock-soft: #352816;
  --finish: #4fd1c5; --finish-soft: #13302e; --focus: #b49cff; --focus-soft: #2a2244;
  --fyi: #a0a7b4; --fyi-soft: #232833; --ok: #5ed38d; --warn: #f2b35a; --bad: #ff7b7b;
  color-scheme: dark; } }
:root[data-theme="dark"] {
  --bg: #0f1218; --surface: #171b23; --sunk: #1d222c; --ink: #e8ebf1; --muted: #9aa3b2;
  --line: #2a303c; --accent: #8aa5ff; --accent-soft: #1f2a4a;
  --fire: #ff7b7b; --fire-soft: #3a1d1f; --unblock: #f2b35a; --unblock-soft: #352816;
  --finish: #4fd1c5; --finish-soft: #13302e; --focus: #b49cff; --focus-soft: #2a2244;
  --fyi: #a0a7b4; --fyi-soft: #232833; --ok: #5ed38d; --warn: #f2b35a; --bad: #ff7b7b;
  color-scheme: dark; }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); font: 15px/1.5 var(--body); }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
a:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 3px; }
.wrap { max-width: 1120px; margin: 0 auto; padding-inline: 20px; padding-block: 28px 56px;
  display: grid; gap: 20px; }
.strip { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: 12px 24px; }
.strip h1 { font: 650 clamp(26px, 4vw, 34px)/1.1 var(--display); margin: 0; letter-spacing: -0.01em;
  text-wrap: balance; }
.strip .when { color: var(--muted); font: 13px/1.4 var(--mono); font-variant-numeric: tabular-nums; }
.sources { display: flex; flex-wrap: wrap; gap: 6px; }
.src { display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px; border-radius: 999px;
  background: var(--surface); border: 1px solid var(--line); font: 12px/1.4 var(--mono); }
.src i { width: 7px; height: 7px; border-radius: 50%; background: var(--fyi); }
.src.ok i { background: var(--ok); } .src.partial i { background: var(--warn); }
.src.failed i { background: var(--bad); } .src .note { color: var(--muted); }
.focus-card { background: var(--surface); border: 1px solid var(--line); border-radius: 14px;
  padding: 22px 24px; display: grid; gap: 14px; border-top: 4px solid var(--rung, var(--accent)); }
.eyebrow { font: 600 11px/1 var(--mono); letter-spacing: .08em; text-transform: uppercase; color: var(--muted);
  display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.focus-card h2 { margin: 0; font: 650 clamp(21px, 3vw, 26px)/1.2 var(--display); text-wrap: balance; }
.focus-card .why { margin: 0; color: var(--muted); max-width: 70ch; }
.steps { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; }
.step { background: var(--sunk); border-radius: 10px; padding: 12px 14px; min-width: 0; }
.step b { display: block; font: 600 11px/1.3 var(--mono); letter-spacing: .06em; text-transform: uppercase;
  color: var(--muted); margin-bottom: 4px; }
.links { display: flex; flex-wrap: wrap; gap: 8px; }
.links a { font: 13px/1.4 var(--mono); padding: 2px 8px; border-radius: 6px; background: var(--accent-soft); }
.track { display: flex; flex-wrap: wrap; gap: 8px; align-items: stretch; }
.track .leg { flex: 1 1 180px; min-width: 0; background: var(--surface); border: 1px solid var(--line);
  border-radius: 10px; padding: 10px 12px; display: grid; gap: 2px; border-left: 4px solid var(--rung); }
.track .leg small { font: 11px/1.3 var(--mono); color: var(--muted); text-transform: uppercase; letter-spacing: .06em; }
.track .leg span { font-weight: 600; overflow-wrap: anywhere; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 460px), 1fr)); gap: 20px; }
.panel { background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 16px 18px;
  display: grid; gap: 10px; align-content: start; min-width: 0; }
.panel h3 { margin: 0; font: 600 13px/1.2 var(--mono); letter-spacing: .07em; text-transform: uppercase;
  display: flex; gap: 8px; align-items: center; justify-content: space-between; }
.panel h3 .count { color: var(--muted); font-weight: 400; }
.panel .sub { margin: 0; color: var(--muted); font-size: 13px; }
ul.items { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }
.item { display: grid; grid-template-columns: 4px 1fr; gap: 0 12px; padding: 8px 0; border-top: 1px solid var(--line); }
.item:first-child { border-top: 0; padding-top: 2px; }
.item .bar { border-radius: 4px; background: var(--rung, var(--fyi)); }
.item .body { min-width: 0; display: grid; gap: 3px; }
.item .top { display: flex; flex-wrap: wrap; gap: 6px 8px; align-items: baseline; }
.item .title { font-weight: 600; overflow-wrap: anywhere; }
.item .meta { color: var(--muted); font-size: 13.5px; overflow-wrap: anywhere; }
.item .meta b { color: var(--ink); font-weight: 600; }
.tag, .age, .rung { font: 11.5px/1.5 var(--mono); padding: 0 7px; border-radius: 5px; white-space: nowrap;
  font-variant-numeric: tabular-nums; }
.tag { background: var(--sunk); color: var(--muted); }
.age { background: var(--accent-soft); color: var(--accent); }
.rung { background: var(--rung-soft, var(--fyi-soft)); color: var(--rung, var(--fyi)); font-weight: 600; }
.r-fire { --rung: var(--fire); --rung-soft: var(--fire-soft); }
.r-unblock { --rung: var(--unblock); --rung-soft: var(--unblock-soft); }
.r-finish { --rung: var(--finish); --rung-soft: var(--finish-soft); }
.r-focus { --rung: var(--focus); --rung-soft: var(--focus-soft); }
.r-fyi { --rung: var(--fyi); --rung-soft: var(--fyi-soft); }
.questions { background: var(--unblock-soft); border: 1px solid var(--line); border-radius: 12px; padding: 14px 18px; }
.questions h3 { color: var(--unblock); }
.questions ol { margin: 6px 0 0; padding-left: 20px; display: grid; gap: 4px; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip { font: 12.5px/1.5 var(--mono); padding: 2px 8px; border-radius: 6px; background: var(--sunk); }
.chip.red { background: var(--fire-soft); color: var(--fire); }
.decision { font-weight: 600; }
.days { font: 600 12px/1.5 var(--mono); color: var(--unblock); }
footer { color: var(--muted); font: 12px/1.5 var(--mono); }
@media (prefers-reduced-motion: no-preference) {
  .focus-card, .panel { animation: rise .35s ease-out both; }
  @keyframes rise { from { transform: translateY(4px); } to { transform: none; } }
}
"""

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@600;700'
         '&family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;600&display=swap">')


def e(x):
    return html.escape(str(x if x is not None else ""))


def link(text, url):
    return f'<a href="{e(url)}" target="_blank" rel="noopener">{e(text)}</a>' if url else e(text)


def chips(item):
    out = []
    if item.get("rung"):
        out.append(f'<span class="rung r-{e(item["rung"])}">{e(RUNG_LABEL.get(item["rung"], item["rung"]))}</span>')
    if item.get("source"):
        out.append(f'<span class="tag">{e(SOURCE_LABEL.get(item["source"], item["source"]))}</span>')
    if item.get("age"):
        out.append(f'<span class="age">{e(item["age"])}</span>')
    return "".join(out)


def item_li(title, url, meta_html, item, rung):
    meta = f'<div class="meta">{meta_html}</div>' if meta_html else ""
    return (f'<li class="item r-{e(item.get("rung") or rung)}"><span class="bar"></span><div class="body">'
            f'<div class="top"><span class="title">{link(title, url)}</span>{chips(item)}</div>'
            f'{meta}</div></li>')


def panel(title, body, count=None, sub=None, cls=""):
    c = f'<span class="count">{e(count)}</span>' if count is not None else ""
    s = f'<p class="sub">{e(sub)}</p>' if sub else ""
    return f'<section class="panel {cls}"><h3>{e(title)}{c}</h3>{s}{body}</section>'


def render(plan_path, fragment=False, out=None):
    p = json.loads(Path(plan_path).read_text())
    date = p.get("date") or datetime.now().strftime("%Y-%m-%d")
    day = datetime.strptime(date, "%Y-%m-%d").strftime("%A, %B %-d")
    w = p.get("window", {})
    when = f'window {e(w.get("start", "")[:16].replace("T", " "))} → {e(w.get("end", "")[:16].replace("T", " "))} UTC'
    if w.get("hours"):
        when += f' · {e(w["hours"])}h'
    if w.get("label"):
        when += f' · {e(w["label"])}'

    def source_pill(s):
        note = f' <span class="note">· {e(s["note"])}</span>' if s.get("note") else ""
        state = s.get("state", "none")
        return (f'<span class="src {e(state)}"><i></i>{e(s["name"])} '
                f'{e(STATE_LABEL.get(state, state))}{note}</span>')

    srcs = "".join(source_pill(s) for s in p.get("sources", []))

    parts = [f'<header class="strip"><div><h1>Good morning · {e(day)}</h1>'
             f'<div class="when">{when}</div></div><div class="sources">{srcs}</div></header>']

    m = p.get("main") or {}
    if m:
        links = "".join(link(l["label"], l.get("url")) for l in m.get("links", []))
        why = f'<p class="why">{e(m["why"])}</p>' if m.get("why") else ""
        links_html = f'<div class="links">{links}</div>' if links else ""
        parts.append(
            f'<section class="focus-card r-{e(m.get("rung", "focus"))}"><div class="eyebrow">Main focus {chips(m)}</div>'
            f'<h2>{link(m.get("title"), m.get("url"))}</h2>'
            f'{why}'
            f'<div class="steps"><div class="step"><b>First step</b>{e(m.get("first_step"))}</div>'
            f'<div class="step"><b>Done when</b>{e(m.get("done_when"))}</div></div>'
            f'{links_html}</section>')

    legs = []
    unblock = p.get("unblock", [])
    if unblock:
        legs.append(("unblock", f'Unblock batch · ~{p.get("unblock_minutes", 60)} min', f"{len(unblock)} people waiting"))
    if m:
        legs.append((m.get("rung", "focus"), "Main focus", m.get("title")))
    for s in p.get("secondary", []):
        legs.append((s.get("rung", "finish"), "Secondary", s.get("title")))
    if legs:
        parts.append('<nav class="track" aria-label="Order of the day">' + "".join(
            f'<div class="leg r-{e(r)}"><small>{i}. {e(label)}</small><span>{e(text)}</span></div>'
            for i, (r, label, text) in enumerate(legs, 1)) + "</nav>")

    qs = p.get("questions", [])
    if qs:
        parts.append('<section class="questions"><h3 class="eyebrow">Questions for you</h3><ol>'
                     + "".join(f"<li>{e(q)}</li>" for q in qs) + "</ol></section>")

    grid = []
    if unblock:
        lis = "".join(item_li(u.get("who"), u.get("url"), e(u.get("what")), u, "unblock") for u in unblock)
        grid.append(panel("Unblock batch", f'<ul class="items">{lis}</ul>', len(unblock),
                          f'Do these first, about {p.get("unblock_minutes", 60)} minutes in total.'))
    sec = p.get("secondary", [])
    if sec:
        lis = "".join(item_li(s.get("title"), s.get("url"),
                              f'{e(s.get("why"))}{"<br><b>First step:</b> " + e(s["first_step"]) if s.get("first_step") else ""}',
                              s, "finish") for s in sec)
        grid.append(panel("Secondary", f'<ul class="items">{lis}</ul>', len(sec), "At most two, after the main focus."))
    co = p.get("carry_over", [])
    if co:
        lis = "".join(item_li(c.get("title"), c.get("url"),
                              f'<span class="days">day {e(c.get("days"))}</span> · <span class="decision">{e(c.get("decision"))}</span>',
                              c, "unblock" if (c.get("days") or 0) >= 3 else "fyi") for c in co)
        grid.append(panel("Carry-over", f'<ul class="items">{lis}</ul>', len(co), "Planned before and still open."))
    st = p.get("stale") or {}
    if st.get("items") or st.get("summary"):
        ch = "".join(f'<span class="chip{" red" if i.get("red") else ""}">{link(i.get("title"), i.get("url"))} '
                     f'· {e(i.get("age"))}</span>' for i in st.get("items", []))
        decision = f'<p class="decision">{e(st["decision"])}</p>' if st.get("decision") else ""
        grid.append(panel("Stale", f'<div class="chips">{ch}</div>{decision}',
                          len(st.get("items", [])) or None, st.get("summary")))
    nt = p.get("not_today", [])
    if nt:
        lis = "".join(item_li(n.get("title"), n.get("url"), e(n.get("reason")), n, "fyi") for n in nt)
        grid.append(panel("Not today", f'<ul class="items">{lis}</ul>', len(nt)))
    led = p.get("ledger", [])
    if led:
        lis = "".join(item_li(l.get("title"), l.get("url"), e(l.get("action")), {"source": "ledger", **l}, "fyi")
                      for l in led)
        grid.append(panel("Ledger", f'<ul class="items">{lis}</ul>', len(led), "Cards and blockers to update."))
    fyi = p.get("fyi", [])
    if fyi:
        lis = "".join(item_li(f.get("text"), f.get("url"), "", {"source": f.get("source"), "age": f.get("age")}, "fyi")
                      for f in fyi)
        grid.append(panel("FYI", f'<ul class="items">{lis}</ul>', len(fyi)))
    if grid:
        parts.append(f'<div class="grid">{"".join(grid)}</div>')
    parts.append(f'<footer>Generated by the good-morning skill · {e(datetime.now().strftime("%Y-%m-%d %H:%M"))} · '
                 f'read-only: nothing was sent, moved or marked as read.</footer>')

    body = f'<title>Day Sheet {e(date)}</title>{FONTS}<style>{CSS}</style><main class="wrap">{"".join(parts)}</main>'
    if not fragment:
        body = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
                f'</head><body>{body}</body></html>')
    target = Path(out) if out else Path(tempfile.gettempdir()) / "good-morning" / f"day-sheet-{date}.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body)
    return target


# --- terminal (Markdown) report -------------------------------------------

RUNG_DOT = {"fire": "🔴", "unblock": "🟠", "finish": "🟢", "focus": "🟣", "fyi": "⚪"}
STATE_MARK = {"ok": "✓", "partial": "◐", "failed": "✗", "none": "–"}


def md(x):
    """Escape a value for a Markdown table cell or inline text."""
    return str(x if x is not None else "").replace("|", "\\|").replace("\n", " ").strip()


def mdlink(text, url):
    return f"[{md(text)}]({url})" if url else md(text)


def dot(item, default="fyi"):
    return RUNG_DOT.get(item.get("rung") or default, "⚪")


def table(header, rows):
    if not rows:
        return []
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return out


def render_markdown(plan_path):
    p = json.loads(Path(plan_path).read_text())
    date = p.get("date") or datetime.now().strftime("%Y-%m-%d")
    day = datetime.strptime(date, "%Y-%m-%d").strftime("%A, %b %-d")
    w = p.get("window", {})
    src = " ".join(f"`{s['name']} {STATE_MARK.get(s.get('state'), '?')}`" for s in p.get("sources", []))
    notes = "; ".join(f"{s['name']}: {s['note']}" for s in p.get("sources", []) if s.get("note"))
    out = [f"## ☀️ {day} · {w.get('hours', '?')}h window", src + (f"  \n_{md(notes)}_" if notes else ""), ""]

    m = p.get("main") or {}
    if m:
        rung = RUNG_LABEL.get(m.get("rung", "focus"), "")
        out += [f"### 🎯 Main focus · {dot(m, 'focus')} {rung}",
                f"**{mdlink(m.get('title'), m.get('url'))}**" + (f" — {md(m['why'])}" if m.get("why") else ""), "",
                f"- **First step:** {md(m.get('first_step'))}",
                f"- **Done when:** {md(m.get('done_when'))}"]
        if m.get("links"):
            out.append("- **Links:** " + " · ".join(mdlink(l["label"], l.get("url")) for l in m["links"]))
        out.append("")

    unblock = p.get("unblock", [])
    sec = p.get("secondary", [])
    order = []
    if unblock:
        order.append(["1", f"🟠 Unblock ~{p.get('unblock_minutes', 60)} min",
                      md(", ".join(u.get("who", "") for u in unblock))])
    if m:
        order.append([str(len(order) + 1), f"{dot(m, 'focus')} Main focus", md(m.get("title"))])
    for s in sec:
        order.append([str(len(order) + 1), f"{dot(s, 'finish')} Secondary", md(s.get("title"))])
    if order:
        out += ["### 🗺️ Order of the day"] + table(["#", "Block", "Item"], order) + [""]

    qs = p.get("questions", [])
    if qs:
        out += ["### ❓ Questions for you"] + [f"{i}. {md(q)}" for i, q in enumerate(qs, 1)] + [""]

    if unblock:
        out += [f"### 🟠 Unblock batch · ~{p.get('unblock_minutes', 60)} min"]
        out += table(["Who", "Needs", "Age", "Source"],
                     [[mdlink(u.get("who"), u.get("url")), md(u.get("what")), md(u.get("age", "")),
                       md(SOURCE_LABEL.get(u.get("source"), u.get("source", "")))] for u in unblock]) + [""]
    if sec:
        out += ["### ➡️ Secondary"]
        out += table(["Item", "Why", "First step", "Age"],
                     [[f"{dot(s, 'finish')} {mdlink(s.get('title'), s.get('url'))}", md(s.get("why")),
                       md(s.get("first_step")), md(s.get("age", ""))] for s in sec]) + [""]

    co = p.get("carry_over", [])
    if co:
        out += ["### 🔁 Carry-over"]
        out += table(["Item", "Day", "Decision"],
                     [[mdlink(c.get("title"), c.get("url")),
                       f"**{md(c.get('days'))}**" + (" ⚠️" if (c.get("days") or 0) >= 3 else ""),
                       md(c.get("decision"))] for c in co]) + [""]

    st = p.get("stale") or {}
    if st.get("items") or st.get("summary"):
        out += [f"### 💤 Stale" + (f" · {md(st['summary'])}" if st.get("summary") else "")]
        if st.get("items"):
            out.append(" · ".join(f"{mdlink(i.get('title'), i.get('url'))} `{md(i.get('age'))}`"
                                  + (" 🔴" if i.get("red") else "") for i in st["items"]))
        if st.get("decision"):
            out.append(f"**Decision:** {md(st['decision'])}")
        out.append("")

    nt = p.get("not_today", [])
    if nt:
        out += ["### ⏸️ Not today"]
        out += table(["Item", "Reason"],
                     [[f"{dot(n)} {mdlink(n.get('title'), n.get('url'))}", md(n.get("reason"))] for n in nt]) + [""]

    led = p.get("ledger", [])
    if led:
        out += ["### 🗂️ Ledger"] + [f"- {mdlink(l.get('title'), l.get('url'))} → {md(l.get('action'))}" for l in led] + [""]

    fyi = p.get("fyi", [])
    if fyi:
        out += ["### ℹ️ FYI"]
        out += [f"- `{SOURCE_LABEL.get(f.get('source'), f.get('source', ''))}` {mdlink(f.get('text'), f.get('url'))}"
                + (f" · {md(f['age'])}" if f.get("age") else "") for f in fyi] + [""]

    out.append("_Read-only: nothing was sent, moved or marked as read._")
    return "\n".join(out)
