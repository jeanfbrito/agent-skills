#!/usr/bin/env python3
"""Read, write and guard the awesomeness-loop state on disk.

The loop writes as it works. Each step of a cycle appends one note to the
trail (.localdev/awesomeness/trail.jsonl) when it happens: the pick, the
prediction, each attempt, each capture or measure, keep or revert, the commit,
the end. Each note also rebuilds the HTML report, so the report is always
current and nobody builds it as a separate job. A run that starts later reads
the trail in `brief` and continues the open cycle from its last note.

Usage:
  state.py [brief] [--project DIR] [--journal PATH] [--root PATH] [--drift-depth 4]
  state.py note KIND [TEXT] [--row ROW] [--file PATH ...] [--metric NAME=VALUE ...]
                [--commit SHA] [--status "partial -> matches"] [--progress "0.31 -> 0.12" | none]
                [--next "next step"]
      KIND: pick predict try see keep revert commit step-back blocked end
  state.py lock    [--project DIR] [--owner NAME] [--stale-min 90]   # prints LOCKED token=<t>
  state.py unlock  --token <t> [--project DIR]                       # only the holder unlocks
  state.py pause   [--project DIR]     # the human brake for every driver
  state.py resume  [--project DIR]

Exit codes: 0 ok. 3 another cycle holds the lock. 4 the loop is paused.
Standard library only.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from report import md_setup, md_tables  # noqa: E402  (one parser for both tools)

WORK = {"missing", "partial", "below", "unknown", "lab-only", ""}
QUEUED = {"queued"}
CLOSED = {"matches", "exceeds"}
PARKED = {"blocked", "held"}
STALL_CYCLES = 3
LOG_ROW_MAX = 300
LOG_ROWS_MAX = 30
JOURNAL_MAX = 40_000
TRAIL = "trail.jsonl"
KINDS = ["pick", "predict", "try", "see", "keep", "revert", "commit", "step-back", "blocked", "end"]
IMAGE = re.compile(r"\.(png|jpe?g|webp|gif)$", re.I)
# A line that asserts or compares: an expectation, an assert, a limit, a miss count.
CHECK_LINE = re.compile(r"expect\(|assert|\.to[A-Z]\w*\(|\bcheck\w*\(|_fail\(|violation|miss|[<>]=?\s*-?\d")


def norm(s):
    return re.sub(r"[`*_]", "", s or "").strip().lower()


def status_of(row):
    return norm(row.get("Status", ""))


def section(text, name):
    m = re.search(rf"^## {re.escape(name)}[^\n]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return m.group(1).strip() if m else ""


def find(tables, prefix):
    for name, rows in tables.items():
        if name.lower().startswith(prefix.lower()):
            return rows
    return None


def row_cell(row):
    """The gap row that a cycle-log row worked on (`Row`, or `Item` in old journals)."""
    return norm(row.get("Row") or row.get("Item") or "")


def stall_counts(log, open_rows):
    """Cycles per open row since its last step-back, and trailing no-progress runs."""
    out = {}
    for name in open_rows:
        n = 0
        no_prog = 0
        trailing = True
        for r in reversed(log):
            if row_cell(r) != name:
                continue
            if norm(r.get("Change", "")).startswith("step-back"):
                break
            n += 1
            prog = norm(r.get("Progress", ""))
            if trailing and prog in ("none", "no progress", "-", "same"):
                no_prog += 1
            else:
                trailing = False
        out[name] = (n, no_prog)
    return out


def sense_paths(project, senses):
    paths = set()
    for r in senses or []:
        for cell in r.values():
            for tok in re.findall(r"[\w./-]+\.(?:gd|ts|tsx|js|mjs|py|sh|rs|go|cs)\b", cell or ""):
                tok = tok.lstrip("./").replace("res://", "")
                if os.path.isfile(os.path.join(project, tok)):
                    paths.add(tok)
    return paths


def sense_drift(project, paths, depth):
    """Commits that removed lines from a sense file and changed other code in the same commit."""
    if not paths:
        return []
    try:
        log = subprocess.run(
            ["git", "-C", project, "log", f"-{depth}", "--numstat", "--format=@%h %s"],
            capture_output=True, text=True, timeout=20).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    hits = []
    commit, files = None, []

    def removed_checks(sha, path):
        try:
            diff = subprocess.run(["git", "-C", project, "show", "-U0", "--format=", sha, "--", path],
                                  capture_output=True, text=True, timeout=20).stdout
        except (OSError, subprocess.SubprocessError):
            return 0
        n = 0
        for line in diff.splitlines():
            if not line.startswith("-") or line.startswith("---"):
                continue
            body = line[1:].strip()
            if not body or body.startswith(("#", "//", "*", "/*")):
                continue
            if CHECK_LINE.search(body):
                n += 1
        return n

    def flush():
        if not commit:
            return
        code = [f for a, d, f in files if f not in paths and not f.endswith(".md")]
        if not code:
            return
        sha = commit.split()[0]
        for a_, d, f in files:
            if f in paths and d not in ("0", "-"):
                n = removed_checks(sha, f)
                if n:
                    hits.append(f"{commit[:60]} removes or changes {n} check line(s) in {f} together with {len(code)} code file(s)")

    for line in log.splitlines():
        if line.startswith("@"):
            flush()
            commit, files = line[1:], []
        elif line.strip():
            parts = line.split("\t")
            if len(parts) == 3:
                files.append(tuple(parts))
    flush()
    return hits


def read_trail(root):
    out = []
    path = os.path.join(root, TRAIL)
    if os.path.isfile(path):
        for line in open(path, encoding="utf-8"):
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if isinstance(e, dict):
                out.append(e)
    return out


def open_cycle(trail):
    """The last cycle that has a pick and no end, as (number, row, notes), or None."""
    cycles = {}
    for e in trail:
        cycles.setdefault(e.get("cycle", 0), []).append(e)
    for n in sorted(cycles, reverse=True):
        notes = cycles[n]
        kinds = {e.get("kind") for e in notes}
        if "pick" in kinds and "end" not in kinds:
            return n, notes[0].get("row", ""), notes
        if "end" in kinds:
            return None
    return None


def trail_counts(trail, open_rows):
    """From the trail: cycles per open row since its last step-back, and trailing no-progress ends."""
    ends = [e for e in trail if e.get("kind") == "end"]
    steps = {(e.get("cycle"), norm(e.get("row", ""))) for e in trail if e.get("kind") == "step-back"}
    out = {}
    for name in open_rows:
        n = no_prog = 0
        trailing = True
        for e in reversed(ends):
            if norm(e.get("row", "")) != name:
                continue
            if (e.get("cycle"), name) in steps:
                break
            n += 1
            if trailing and norm(e.get("progress", "")) in ("none", "no progress", "-", "same", ""):
                no_prog += 1
            else:
                trailing = False
        out[name] = (n, no_prog)
    return out


def short(e):
    bits = [e.get("kind", "?"), (e.get("text") or "")[:110]]
    if e.get("metrics"):
        bits.append(" ".join(f"{k}={v}" for k, v in e["metrics"].items())[:80])
    if e.get("files"):
        bits.append(", ".join(os.path.basename(f) for f in e["files"])[:80])
    for k in ("status", "progress", "commit", "next"):
        if e.get(k):
            bits.append(f"{k}: {e[k]}"[:90])
    return " | ".join(b for b in bits if b)


def brief(a):
    jpath = os.path.join(a.project, a.journal)
    root = os.path.join(a.project, a.root)
    out = []
    if os.path.exists(os.path.join(root, "PAUSE")):
        out.append("PAUSED: the human paused the loop (state.py resume to continue).")
    if not os.path.isfile(jpath):
        out.append(f"SIGNAL NO-JOURNAL: {a.journal} is missing. Run the Start steps in SKILL.md.")
        print("\n".join(out))
        return 0
    text = open(jpath, encoding="utf-8").read()
    tables = md_tables(text)
    setup = md_setup(text)
    gap = find(tables, "Gap matrix") or []
    log = find(tables, "Cycle log") or []
    blocked_tbl = find(tables, "Blocked") or []
    queue = find(tables, "Critic queue") or []
    verdicts = find(tables, "Pending verdicts") or []
    asks = find(tables, "Assumptions") or []
    senses = find(tables, "Senses") or []

    head = " | ".join(f"{k}: {setup[k]}" for k in ("Project", "Reference (current bar)", "Mode", "Branch") if setup.get(k))
    out.append(head[:400] or "(no Setup)")
    trail = read_trail(root)
    oc = open_cycle(trail)
    if oc:
        n, row, notes = oc
        out.append(f"IN PROGRESS: cycle {n} on '{row}' has no end note. Continue it from its last note. "
                   f"Do not pick it again and do not redo a step that has a note.")
        out += ["  " + short(e) for e in notes[-14:]]
    else:
        ends = [e for e in trail if e.get("kind") == "end"]
        if ends:
            last = ends[-1]
            out.append(f"NOW: last cycle {last.get('cycle')} on '{last.get('row', '')}' ended: {short(last)}")
        else:
            now = section(text, "Now")  # journals from before the trail
            if now:
                out.append("NOW:")
                out += ["  " + l for l in now.splitlines()[:25] if l.strip() and not l.startswith("The cycle that")]
    focus = norm(oc[1]) if oc else norm(next((e.get("row", "") for e in reversed(trail) if e.get("kind") == "end"), ""))
    reverts = [e for e in trail if e.get("kind") == "revert" and norm(e.get("row", "")) == focus][-6:]
    if reverts:
        out.append("DO NOT RETRY on this row (reverted before):")
        out += ["  - " + (e.get("text") or "")[:150] for e in reverts]

    by_status = {}
    for r in gap:
        by_status.setdefault(status_of(r), []).append(r)
    work = [r for r in gap if status_of(r) not in CLOSED | PARKED | QUEUED]
    queued = [r for r in gap if status_of(r) in QUEUED]
    parked = [r for r in gap if status_of(r) in PARKED]
    has_done_col = bool(gap) and "Done when" in gap[0]
    names = [norm(r.get("Item", "")) for r in work]
    from_log = stall_counts(log, names)  # journals from before the trail
    from_trail = trail_counts(trail, names)
    counts = {n: from_trail[n] if any(e.get("kind") == "end" and norm(e.get("row", "")) == n for e in trail)
              else from_log[n] for n in names}

    out.append(f"ROWS: {len(gap)} total, {len(work)} open, {len(queued)} queued, "
               f"{sum(len(by_status.get(s, [])) for s in CLOSED)} closed, {len(parked)} parked")
    for r in work[:12]:
        name = norm(r.get("Item", ""))
        n, _ = counts.get(name, (0, 0))
        dw = (r.get("Done when") or "").strip()
        out.append(f"  - {r.get('Item', '')[:70]} | {status_of(r) or 'unknown'} | cycles since step-back: {n}"
                   + (f" | done when: {dw[:90]}" if dw else ""))
    if len(work) > 12:
        out.append(f"  - ... {len(work) - 12} more open rows")
    if not trail:
        for r in log[-3:]:
            cells = " | ".join(v for v in r.values() if v)
            out.append(f"  log: {cells[:170]}")

    sig = []
    stale = [f"{k}: {v}" for k, v in setup.items() if re.search(r"drive\.sh|detach|scheduler", f"{k} {v}", re.I)]
    if stale:
        sig.append(f"STALE-DRIVER: the journal says '{stale[0][:80]}'. The loop runs in the session (SKILL.md, Start step 6). "
                   "Delete that line. Do not start drive.sh.")
    open_verdicts = [v for v in verdicts if (v.get("Verdict") or "").strip() and not (v.get("Applied") or "").strip()]
    open_answers = [v for v in asks if (v.get("Verdict") or "").strip() and not (v.get("Applied") or "").strip()]
    if open_verdicts or open_answers:
        sig.append(f"APPLY: {len(open_verdicts)} verdict(s) and {len(open_answers)} answer(s) are written and not applied. Apply them first.")
    blocked_names = {norm(r.get("Item", "")) for r in blocked_tbl}
    for r in gap:
        if norm(r.get("Item", "")) in blocked_names and status_of(r) not in PARKED:
            sig.append(f"MISMATCH: '{r.get('Item', '')[:60]}' is in the Blocked table but its status is '{status_of(r)}'. Set blocked or held, or remove it from Blocked.")
    for r in work:
        name = norm(r.get("Item", ""))
        n, no_prog = counts.get(name, (0, 0))
        if n >= STALL_CYCLES or no_prog >= 2:
            why = f"{n} cycles since its last step-back" if n >= STALL_CYCLES else f"{no_prog} cycles in a row with no progress"
            sig.append(f"STALL: '{r.get('Item', '')[:60]}' has {why}. This cycle is the step back (SKILL.md).")
    if gap and not has_done_col:
        sig.append("NO-DONE-WHEN: the gap matrix has no 'Done when' column. Add it, and fill it for each open row before you work on the row.")
    elif has_done_col:
        missing = [r.get("Item", "")[:40] for r in work if not (r.get("Done when") or "").strip()]
        if missing:
            sig.append(f"NO-DONE-WHEN: {len(missing)} open row(s) have no 'Done when': {', '.join(missing[:4])}. Write it before you work on the row.")
    if len(queue) >= 5 or (queued and not work):
        sig.append(f"CRITIC-DUE: {max(len(queue), len(queued))} row(s) wait for the critic gate. Run one blind round now.")
    if gap and not work and not queued:
        if parked:
            sig.append(f"EXHAUSTED: no open rows and {len(parked)} parked. Do the exhausted procedure (SKILL.md). Do not stop the loop.")
        else:
            sig.append("BEYOND: every row is closed. Start beyond mode (references/beyond.md).")
    drift = sense_drift(a.project, sense_paths(a.project, senses), a.drift_depth)
    for h in drift[:4]:
        sig.append(f"SENSE-DRIFT: {h}. Read that diff. If a check was loosened or turned to fit the new output, restore it in its own commit (lesson 26).")
    long_rows = [r for r in log if len(" | ".join(r.values())) > LOG_ROW_MAX]
    size = len(text.encode("utf-8"))
    if long_rows or len(log) > LOG_ROWS_MAX or size > JOURNAL_MAX:
        sig.append(f"JOURNAL-LONG: {size} bytes, {len(log)} log rows, {len(long_rows)} over {LOG_ROW_MAX} chars. "
                   f"The history now lives in the trail. Move the cycle log out of the journal and keep the tables short.")
    out.append("SIGNALS:" if sig else "SIGNALS: none")
    out += ["  " + s for s in sig]
    out.append(f"report: {os.path.join(a.root, 'report', 'index.html')}")
    print("\n".join(out))
    return 0


def note(a):
    root = os.path.join(a.project, a.root)
    os.makedirs(root, exist_ok=True)
    if not a.rest or a.rest[0] not in KINDS:
        print(f"note: give a KIND first, one of: {' '.join(KINDS)}")
        return 2
    kind, text = a.rest[0], " ".join(a.rest[1:]).strip()
    trail = read_trail(root)
    oc = open_cycle(trail)
    if kind == "pick":
        if oc:
            print(f"REFUSED: cycle {oc[0]} on '{oc[1]}' is still open. Continue it, or close it with "
                  f"`note end --status abandoned --progress none` and say why.")
            return 2
        if not a.row:
            print("REFUSED: a pick needs --row (the gap-matrix item).")
            return 2
        cycle = max([e.get("cycle", 0) for e in trail] or [0]) + 1
        row = a.row
    else:
        if not oc:
            print("REFUSED: no open cycle. Start one with `note pick --row ROW \"the item\"`.")
            return 2
        cycle, row = oc[0], a.row or oc[1]
    metrics = {}
    for m in a.metric or []:
        k, _, v = m.partition("=")
        try:
            v = float(v)
        except ValueError:
            pass
        metrics[k.strip()] = v
    files = [os.path.abspath(os.path.join(a.project, f)) for f in (a.file or [])]
    entry = {"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "cycle": cycle, "row": row, "kind": kind}
    for k, v in (("text", text), ("files", files), ("metrics", metrics), ("commit", a.commit),
                 ("status", a.status), ("progress", a.progress), ("next", a.next)):
        if v:
            entry[k] = v
    with open(os.path.join(root, TRAIL), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    lock_path = os.path.join(root, "lock")
    if os.path.exists(lock_path):  # each note is a heartbeat for the cycle lock
        try:
            held = json.load(open(lock_path))
            held["started"] = time.time()
            json.dump(held, open(lock_path, "w"))
        except (OSError, ValueError):
            pass
    try:
        import report
        report.build(root, os.path.join(a.project, a.journal), os.path.join(root, "report"))
        where = os.path.join(a.root, "report", "index.html")
    except Exception as exc:  # the note is written; a report failure must not lose it
        where = f"report not rebuilt ({exc.__class__.__name__}: {exc})"
    print(f"noted {kind} in cycle {cycle} ('{row}'). report: {where}")
    return 0


def lock(a):
    root = os.path.join(a.project, a.root)
    os.makedirs(root, exist_ok=True)
    if os.path.exists(os.path.join(root, "PAUSE")):
        print("PAUSED: the human paused the loop. This run does nothing.")
        return 4
    path = os.path.join(root, "lock")
    now = time.time()
    if os.path.exists(path):
        try:
            held = json.load(open(path))
        except (OSError, ValueError):
            held = {}
        age = (now - float(held.get("started", 0))) / 60
        if age < a.stale_min:
            print(f"BUSY: {held.get('owner', '?')} holds the cycle lock for {age:.0f} min. This run does nothing.")
            return 3
    token = os.urandom(4).hex()
    with open(path, "w") as fh:
        json.dump({"owner": a.owner, "token": token, "started": now}, fh)
    print(f"LOCKED token={token} (owner {a.owner}). Unlock with: unlock --token {token}")
    return 0


def unlock(a):
    path = os.path.join(a.project, a.root, "lock")
    if not os.path.exists(path):
        print("UNLOCKED (no lock was held)")
        return 0
    try:
        held = json.load(open(path))
    except (OSError, ValueError):
        held = {}
    if held.get("token") and held.get("token") != a.token:
        print(f"REFUSED: this lock belongs to {held.get('owner', '?')}. Only the run that took it unlocks it "
              f"(--token from its LOCKED line).")
        return 3
    os.remove(path)
    print("UNLOCKED")
    return 0


def pause(a, on):
    root = os.path.join(a.project, a.root)
    os.makedirs(root, exist_ok=True)
    path = os.path.join(root, "PAUSE")
    if on:
        open(path, "w").write(time.strftime("%Y-%m-%d %H:%M\n"))
        print("PAUSED: every driver skips its cycles until state.py resume.")
    elif os.path.exists(path):
        os.remove(path)
        print("RESUMED")
    else:
        print("RESUMED (it was not paused)")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", nargs="?", default="brief", choices=["brief", "note", "lock", "unlock", "pause", "resume"])
    ap.add_argument("rest", nargs="*", help="for note: KIND, then the text")
    ap.add_argument("--row")
    ap.add_argument("--file", action="append")
    ap.add_argument("--metric", action="append")
    ap.add_argument("--commit")
    ap.add_argument("--status")
    ap.add_argument("--progress")
    ap.add_argument("--next")
    ap.add_argument("--project", default=".")
    ap.add_argument("--journal", default="docs/awesomeness-loop.md")
    ap.add_argument("--root", default=".localdev/awesomeness")
    ap.add_argument("--owner", default=os.environ.get("AWESOME_OWNER", f"run-{os.getppid()}"))
    ap.add_argument("--stale-min", type=float, default=90, help="minutes with no note before a lock is stale")
    ap.add_argument("--token", help="for unlock: the token that lock printed")
    ap.add_argument("--drift-depth", type=int, default=4, help="commits to scan for sense drift (the last cycle)")
    a = ap.parse_intermixed_args()
    a.project = os.path.abspath(a.project)
    if a.cmd == "brief":
        return brief(a)
    if a.cmd == "note":
        return note(a)
    if a.cmd == "lock":
        return lock(a)
    if a.cmd == "unlock":
        return unlock(a)
    return pause(a, a.cmd == "pause")


if __name__ == "__main__":
    sys.exit(main())
