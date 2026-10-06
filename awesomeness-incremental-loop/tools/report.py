#!/usr/bin/env python3
"""Build the awesomeness-loop report from loop data on disk.

Reads the journal (Markdown) and the data root described in
references/schemas.md. Writes <out>/index.html (one static page, inline CSS,
no network) and <out>/report-data.json (the same facts for the agent).

Usage:
  report.py [--root .localdev/awesomeness] [--journal docs/awesomeness-loop.md]
            [--out <root>/report]

Standard library only. Prints a short summary, never the full data.
"""
import argparse
import html
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime

STATUS_COLORS = {
    "missing": "#d9534f", "partial": "#e8963a", "below": "#e8963a",
    "unknown": "#e8963a", "lab-only": "#5b8def", "queued": "#8a6fd1",
    "matches": "#3c9a5f", "exceeds": "#1f7a45", "blocked": "#777777",
}


def read_jsonl(path):
    out = []
    if not os.path.isfile(path):
        return out
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            if isinstance(obj, dict):
                out.append(obj)
    return out


def read_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def md_tables(text):
    """Return {section heading: [row dicts]} for every Markdown table."""
    tables = {}
    heading = ""
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("#"):
            heading = line.lstrip("#").strip()
        if line.strip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            header = [c.strip() for c in line.strip().strip("|").split("|")]
            rows = []
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if any(cells):
                    rows.append(dict(zip(header, cells)))
                i += 1
            tables[heading] = rows
            continue
        i += 1
    return tables


def md_setup(text):
    setup = {}
    m = re.search(r"^## Setup\s*$(.*?)(?=^## )", text, re.M | re.S)
    if m:
        for line in m.group(1).splitlines():
            kv = re.match(r"^- ([^:]+):\s*(.*)$", line.strip())
            if kv:
                setup[kv.group(1).strip()] = kv.group(2).strip()
    return setup


def find_table(tables, prefix):
    for name, rows in tables.items():
        if name.lower().startswith(prefix.lower()):
            return rows
    return []


def load_runs(root):
    runs = []
    runs_dir = os.path.join(root, "runs")
    if not os.path.isdir(runs_dir):
        return runs
    for name in sorted(os.listdir(runs_dir)):
        d = os.path.join(runs_dir, name)
        if not os.path.isdir(d):
            continue
        runs.append({
            "id": name,
            "dir": d,
            "captures": read_jsonl(os.path.join(d, "captures.jsonl")),
            "events": read_jsonl(os.path.join(d, "events.jsonl")),
            "metrics": read_json(os.path.join(d, "metrics.json")) or {},
        })
    return runs


def load_critic(root):
    out = []
    d = os.path.join(root, "critic")
    if os.path.isdir(d):
        for name in sorted(os.listdir(d)):
            if name.endswith(".json"):
                obj = read_json(os.path.join(d, name))
                if isinstance(obj, dict):
                    out.append(obj)
    return out


def sparkline(values, limit=None, w=140, h=28):
    vals = [v for v in values if isinstance(v, (int, float))]
    if not vals:
        return ""
    lo = min(vals + ([limit] if isinstance(limit, (int, float)) else []))
    hi = max(vals + ([limit] if isinstance(limit, (int, float)) else []))
    span = (hi - lo) or 1.0

    def y(v):
        return h - 2 - (v - lo) / span * (h - 4)

    step = (w - 4) / max(len(vals) - 1, 1)
    pts = " ".join(f"{2 + i * step:.1f},{y(v):.1f}" for i, v in enumerate(vals))
    lim = ""
    if isinstance(limit, (int, float)):
        lim = f'<line x1="0" x2="{w}" y1="{y(limit):.1f}" y2="{y(limit):.1f}" class="lim"/>'
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" class="spark">'
            f'{lim}<polyline points="{pts}" fill="none"/></svg>')


def build(root, journal, out):
    text = ""
    if journal and os.path.isfile(journal):
        with open(journal, encoding="utf-8") as fh:
            text = fh.read()
    tables = md_tables(text)
    setup = md_setup(text)
    gap_rows = find_table(tables, "Gap matrix")
    verdicts = find_table(tables, "Pending verdicts")
    runs = load_runs(root)
    critic = load_critic(root)

    by_row = defaultdict(lambda: {"captures": [], "metrics": [], "events": [], "critic": []})
    breaks = []
    for run in runs:
        rel = os.path.relpath(run["dir"], out)
        for c in run["captures"]:
            c = dict(c, run=run["id"], path=os.path.join(rel, c.get("file", "")))
            by_row[c.get("row", "")]["captures"].append(c)
        m = run["metrics"]
        if m:
            by_row[m.get("row", "")]["metrics"].append(dict(m, run=run["id"]))
        for e in run["events"]:
            e = dict(e, run=run["id"])
            if e.get("kind") == "invariant":
                breaks.append(e)
            by_row[e.get("row", m.get("row", "") if m else "")]["events"].append(e)
    for rnd in critic:
        for p in rnd.get("pairs", []):
            by_row[p.get("row", "")]["critic"].append(dict(p, round=rnd.get("round", ""), cycle=rnd.get("cycle")))

    data = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "setup": setup,
        "gap_matrix": gap_rows,
        "pending_verdicts": verdicts,
        "runs": [r["id"] for r in runs],
        "invariant_breaks": breaks,
        "rows": by_row,
    }
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "report-data.json"), "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, default=str)

    esc = html.escape
    parts = [f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Awesomeness loop report</title><style>
:root{{--bg:#fafaf8;--fg:#1d1d1b;--mut:#6b6b66;--card:#fff;--line:#e3e3de;--acc:#5b8def}}
@media (prefers-color-scheme:dark){{:root{{--bg:#161615;--fg:#ececea;--mut:#9a9a94;--card:#20201e;--line:#33332f;--acc:#7aa2f7}}}}
body{{margin:0;padding:16px;background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,sans-serif}}
main{{max-width:1200px;margin:auto}} h1{{font-size:20px}} h2{{font-size:16px;margin-top:28px}}
.meta{{color:var(--mut)}} table{{border-collapse:collapse;width:100%;background:var(--card)}}
td,th{{border:1px solid var(--line);padding:4px 6px;text-align:left;vertical-align:top}}
.st{{color:#fff;border-radius:3px;padding:1px 6px;font-size:12px;white-space:nowrap}}
.row{{background:var(--card);border:1px solid var(--line);border-radius:6px;padding:10px;margin:12px 0}}
.thumbs{{display:flex;flex-wrap:wrap;gap:6px}} .thumbs figure{{margin:0;width:200px}}
.thumbs img{{width:200px;height:auto;border:1px solid var(--line)}} figcaption{{font-size:11px;color:var(--mut)}}
.spark polyline{{stroke:var(--acc);stroke-width:1.5}} .spark .lim{{stroke:#d9534f;stroke-dasharray:3 2}}
a{{color:var(--acc)}} .bad{{color:#d9534f}} .ok{{color:#3c9a5f}} .wrap{{overflow-x:auto}}
</style></head><body><main>
<h1>Awesomeness loop report</h1>
<p class="meta">{esc(' · '.join(f'{k}: {v}' for k, v in setup.items() if v) or 'No journal setup found')}<br>
Generated {esc(data['generated'])} · {len(runs)} runs · {len(critic)} critic rounds</p>"""]

    parts.append("<h2>Gap matrix</h2><div class='wrap'><table><tr><th>Item</th><th>Status</th><th>Evidence</th><th>Impact</th><th>Effort</th></tr>")
    for r in gap_rows:
        item = r.get("Item", "")
        st = r.get("Status", "").strip("` ").lower() or "unknown"
        color = STATUS_COLORS.get(st, "#777")
        ev = r.get("Full-project result") or r.get("Lab result") or r.get("Evidence for status", "")
        parts.append(f"<tr><td><a href='#row-{esc(item)}'>{esc(item)}</a></td>"
                     f"<td><span class='st' style='background:{color}'>{esc(st)}</span></td>"
                     f"<td>{esc(ev)}</td><td>{esc(r.get('Impact', ''))}</td><td>{esc(r.get('Effort', ''))}</td></tr>")
    parts.append("</table></div>")

    if breaks:
        parts.append("<h2>Invariant breaks</h2><div class='wrap'><table><tr><th>Run</th><th>Frame</th><th>Rule</th><th>Object</th><th>Value / limit</th></tr>")
        for e in breaks[-200:]:
            parts.append(f"<tr><td>{esc(e['run'])}</td><td>{esc(str(e.get('frame', '')))}</td><td class='bad'>{esc(e.get('name', ''))}</td>"
                         f"<td>{esc(e.get('object', ''))}</td><td>{esc(str(e.get('value', '')))} / {esc(str(e.get('limit', '')))}</td></tr>")
        parts.append("</table></div>")

    if verdicts:
        parts.append("<h2>Pending verdicts</h2><div class='wrap'><table><tr>" + "".join(f"<th>{esc(k)}</th>" for k in verdicts[0]) + "</tr>")
        for v in verdicts:
            parts.append("<tr>" + "".join(f"<td>{esc(x)}</td>" for x in v.values()) + "</tr>")
        parts.append("</table></div>")

    parts.append("<h2>Rows</h2>")
    names = [r.get("Item", "") for r in gap_rows] + sorted(k for k in by_row if k not in {r.get("Item", "") for r in gap_rows})
    for name in names:
        d = by_row.get(name)
        if not d:
            continue
        parts.append(f"<section class='row' id='row-{esc(name)}'><h3>{esc(name or '(no row)')}</h3>")
        series = defaultdict(list)
        limits = {}
        for m in d["metrics"]:
            for k, v in (m.get("metrics") or {}).items():
                if isinstance(v, dict):
                    series[k].append(v.get("p95", v.get("max", v.get("value"))))
                    limits[k] = v.get("limit")
        if series:
            parts.append("<table><tr><th>Metric</th><th>Trend (p95)</th><th>Last</th><th>Limit</th></tr>")
            for k, vals in series.items():
                last = vals[-1]
                lim = limits.get(k)
                cls = "ok" if isinstance(lim, (int, float)) and isinstance(last, (int, float)) and last <= lim else "bad"
                parts.append(f"<tr><td>{esc(k)}</td><td>{sparkline(vals, lim)}</td><td class='{cls}'>{esc(str(last))}</td><td>{esc(str(lim))}</td></tr>")
            parts.append("</table>")
        for p in d["critic"]:
            won = p.get("verdict") in (p.get("ours"), "tie")
            parts.append(f"<p class='{'ok' if won else 'bad'}'>Critic {esc(str(p.get('round', '')))}: "
                         f"{'win/tie' if won else 'loss'} ({esc(str(p.get('margin', '')))}). "
                         f"{esc('; '.join(p.get('deficits', [])))}</p>")
        caps = d["captures"]
        if caps:
            keep = {}
            for c in caps:  # first and last capture per shot
                keep.setdefault((c.get("shot"), "first"), c)
                keep[(c.get("shot"), "last")] = c
            parts.append("<div class='thumbs'>")
            for c in sorted({id(v): v for v in keep.values()}.values(), key=lambda c: (c.get("shot", ""), c["run"], c.get("frame", 0))):
                bad = [k for k, v in (c.get("checks") or {}).items() if isinstance(v, dict) and not v.get("ok", True)]
                cap = f"{c.get('shot', '')} · {c['run']} · f{c.get('frame', '')}"
                if c.get("event"):
                    cap += f" · {c['event']}"
                if bad:
                    cap += " · BREAK: " + ", ".join(bad)
                parts.append(f"<figure><a href='{esc(c['path'])}'><img loading='lazy' src='{esc(c['path'])}' alt='{esc(cap)}'></a>"
                             f"<figcaption class='{'bad' if bad else ''}'>{esc(cap)}</figcaption></figure>")
            parts.append("</div>")
        parts.append("</section>")
    parts.append("</main></body></html>")
    with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(parts))
    return data, runs, critic, breaks


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=".localdev/awesomeness")
    ap.add_argument("--journal", default="docs/awesomeness-loop.md")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    out = a.out or os.path.join(a.root, "report")
    data, runs, critic, breaks = build(a.root, a.journal, out)
    print(f"REPORT OK: {len(data['gap_matrix'])} gap rows, {len(runs)} runs, "
          f"{len(critic)} critic rounds, {len(breaks)} invariant breaks")
    print(f"html: {os.path.join(out, 'index.html')}")
    print(f"data: {os.path.join(out, 'report-data.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
