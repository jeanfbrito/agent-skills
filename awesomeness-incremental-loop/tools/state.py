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
      KIND: pick predict try see keep revert commit step-back blocked end ack
      pick takes --row, --mode gap|coverage|unblock|beyond|step-back|critic|review,
      and --why "<what a user will notice>" (required for gap, coverage, unblock, beyond)
      ack --drift <sha> "<why the check change is right>" clears a SENSE-DRIFT
  state.py lock    [--project DIR] [--owner NAME] [--stale-min 90]
      # The same agent session takes its own lock back (after a compaction).
      # A lock whose session has ended is taken over. Only another live session gets BUSY (exit 3).
  state.py unlock  --token <t> [--project DIR]    # the holder, or any run of the same agent session
  state.py unlock  --orphan [--project DIR]     # the orchestrator, after its cycle subagent ended
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
KINDS = ["pick", "predict", "try", "see", "keep", "revert", "commit", "step-back", "blocked", "end", "ack"]
MODES = ["gap", "coverage", "unblock", "beyond", "step-back", "critic", "review"]
NEEDS_WHY = ("gap", "coverage", "unblock", "beyond")  # work that changes the product or the matrix
REVIEW_EVERY = 10  # cycles between two sense-check reviews
ROTATION = ["coverage", "unblock", "beyond"]  # the steps of the exhausted procedure, in turn
NO_CODE_CYCLES = 3
AGENT_NAMES = ("grok", "claude", "codex")
# Files that do not change the product: docs, the journal, tests and probes, loop data.
NOT_PRODUCT = re.compile(r"(^|/)(docs|tests?|spec|__tests__|\.localdev)/|\.md$|\.(spec|test)\.[a-z]+$|_test\.[a-z]+$|(^|/)probe", re.I)
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
                    hits.append((sha, commit[len(sha) + 1:][:50], f, n, len(code)))

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


def agent_pid():
    """The pid of the agent process that runs this command (grok, claude, codex), or None.

    A session and its subagents share one agent process, so the same pid means
    the same session. A new CLI process per cycle (drive.sh) gives a new pid.
    """
    pid, chain = os.getppid(), []
    for _ in range(12):
        try:
            out = subprocess.run(["ps", "-o", "ppid=,comm=", "-p", str(pid)],
                                 capture_output=True, text=True, timeout=5).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            break
        try:
            ppid, comm = out.split(None, 1)
            pid_next = int(ppid)
        except ValueError:
            break
        chain.append((pid, os.path.basename(comm.strip()).lower()))
        pid = pid_next
        if pid <= 1:
            break
    for p, name in chain:
        if name in AGENT_NAMES:
            return p
    return None  # unknown agent: the lock falls back to its age check


def pid_alive(pid):
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
        return True
    except PermissionError:  # it exists, and another user owns it
        return True
    except (OSError, ValueError):
        return False


def commit_files(project, sha):
    try:
        r = subprocess.run(["git", "-C", project, "show", "--name-only", "--format=", sha],
                           capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    files = [l for l in r.stdout.splitlines() if l.strip()]
    return files if r.returncode == 0 and files else None  # None: unknown (bad sha, merge, no git)


def cycles_of(trail):
    """{cycle number: [notes]} in trail order."""
    out = {}
    for e in trail:
        out.setdefault(e.get("cycle", 0), []).append(e)
    return out


def cycle_mode(notes):
    pick = next((e for e in notes if e.get("kind") == "pick"), {})
    if pick.get("mode"):
        return pick["mode"]
    if any(e.get("kind") == "step-back" for e in notes):
        return "step-back"
    if re.search(r"\bcoverage\b", pick.get("text", ""), re.I):  # trails from before --mode
        return "coverage"
    return "gap"


def closes(end):
    after = (end.get("status") or "").split("->")[-1].lower()
    return any(w in after for w in ("matches", "exceeds", "blocked", "held"))


def no_code_run(project, trail, sense):
    """Trailing gap cycles that changed no product file and closed no row."""
    run = []
    cyc = cycles_of(trail)
    for n in sorted(cyc, reverse=True):
        notes = cyc[n]
        end = next((e for e in notes if e.get("kind") == "end"), None)
        if not end:
            continue
        mode = cycle_mode(notes)
        if mode == "step-back":
            break  # a step back answers NO-CODE
        if mode != "gap":
            continue  # coverage, unblock, beyond and critic cycles neither count nor reset
        if closes(end):
            break
        shas = {e["commit"] for e in notes if e.get("commit")}
        product = unknown = False
        for sha in shas:
            files = commit_files(project, sha)
            if files is None:
                unknown = True
            elif any(not NOT_PRODUCT.search(f) and f not in sense for f in files):
                product = True
                break
        if product:
            break
        if unknown:
            continue  # cannot tell: do not count it
        run.append(n)
    return run


def moved(progress):
    p = (progress or "").strip().lower()
    if p in ("", "none", "no progress", "-", "same"):
        return False
    if "->" in p:
        before, after = (x.strip() for x in p.split("->", 1))
        return before != after and after not in ("same", "")
    return True


def next_exhausted_step(trail, has_blocked):
    last = None
    for notes in cycles_of(trail).values():
        m = cycle_mode(notes)
        if m in ROTATION:
            last = (m, notes[0].get("cycle"))
    i = (ROTATION.index(last[0]) + 1) % len(ROTATION) if last else 0
    step = ROTATION[i]
    if step == "unblock" and not has_blocked:
        step = "beyond"
    return step, last


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
    direction = section(text, "Direction")
    lines = [l for l in direction.splitlines() if l.strip() and not l.startswith(("The review", "A review", "Each cycle"))]
    if lines:
        out.append("DIRECTION (from the last sense-check review; it outranks quick wins):")
        out += ["  " + l[:200] for l in lines[:14]]
    else:
        out.append("DIRECTION: none yet. Write the product focus in the journal's Direction section (SKILL.md, Start step 3).")
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

    chores, items = [], []  # chores: small, done first in this cycle. items: decide this cycle's work.
    stale = [f"{k}: {v}" for k, v in setup.items() if re.search(r"drive\.sh|detach|scheduler", f"{k} {v}", re.I)]
    if stale:
        chores.append(("STALE-DRIVER", f"STALE-DRIVER: the journal says '{stale[0][:80]}'. The loop runs in the session "
                       "(SKILL.md, Start step 6). Delete that line. Do not start drive.sh."))
    open_verdicts = [v for v in verdicts if (v.get("Verdict") or "").strip() and not (v.get("Applied") or "").strip()]
    open_answers = [v for v in asks if (v.get("Verdict") or "").strip() and not (v.get("Applied") or "").strip()]
    if open_verdicts or open_answers:
        chores.append(("APPLY", f"APPLY: {len(open_verdicts)} verdict(s) and {len(open_answers)} answer(s) are written and not applied. Apply them."))
    blocked_names = {norm(r.get("Item", "")) for r in blocked_tbl}
    for r in gap:
        if norm(r.get("Item", "")) in blocked_names and status_of(r) not in PARKED:
            chores.append((f"MISMATCH:{norm(r.get('Item', ''))}", f"MISMATCH: '{r.get('Item', '')[:60]}' is in the Blocked table but its status is "
                           f"'{status_of(r)}'. Set blocked or held, or remove it from Blocked."))
    if gap and not has_done_col:
        chores.append(("NO-DONE-WHEN", "NO-DONE-WHEN: the gap matrix has no 'Done when' column. Add it, and fill it for each open row."))
    elif has_done_col:
        missing = [r.get("Item", "")[:40] for r in work if not (r.get("Done when") or "").strip()]
        if missing:
            chores.append(("NO-DONE-WHEN", f"NO-DONE-WHEN: {len(missing)} open row(s) have no 'Done when': {', '.join(missing[:4])}. Write it."))
    for r in queued:
        name = norm(r.get("Item", ""))
        cyc = cycles_of(trail)
        last_end = next((e for e in reversed(trail) if e.get("kind") == "end" and norm(e.get("row", "")) == name
                         and cycle_mode(cyc.get(e.get("cycle"), [])) != "critic"), None)
        if last_end and not moved(last_end.get("progress")):
            chores.append((f"QUEUED-NO-PROGRESS:{name}", f"QUEUED-NO-PROGRESS: '{r.get('Item', '')[:60]}' went to queued in cycle "
                           f"{last_end.get('cycle')} with no measured move ('{last_end.get('progress', 'none')}'). Set it back to "
                           "partial. A row waits for the critic only after its metric moved toward the reference."))
    acked = [str(e["drift"]).strip().lower() for e in trail if e.get("kind") == "ack" and e.get("drift")]
    drift = {}
    for sha, subject, f, n, code in sense_drift(a.project, sense_paths(a.project, senses), a.drift_depth):
        if any(sha.lower().startswith(x) or x.startswith(sha.lower()) for x in acked if len(x) >= 4):
            continue
        d = drift.setdefault(sha, [subject, [], 0, code])
        d[1].append(f)
        d[2] += n
    for sha, (subject, files_, n, code) in list(drift.items())[:4]:
        chores.append((f"SENSE-DRIFT:{sha[:7]}", f"SENSE-DRIFT: {sha[:7]} '{subject}' changes {n} check line(s) in {', '.join(files_)} "
                       f"together with {code} code file(s). Read the diff. If a check was loosened or turned to fit the output, restore "
                       f"it in its own commit. If it is right, record that: note ack --drift {sha[:7]} \"<why it is right>\"."))
    long_rows = [r for r in log if len(" | ".join(r.values())) > LOG_ROW_MAX]
    size = len(text.encode("utf-8"))
    if long_rows or len(log) > LOG_ROWS_MAX or size > JOURNAL_MAX:
        chores.append(("JOURNAL-LONG", f"JOURNAL-LONG: {size} bytes, {len(log)} log rows, {len(long_rows)} over {LOG_ROW_MAX} chars. "
                       f"The history lives in the trail. Move the cycle log out of the journal and keep the tables short."))

    cyc_all = cycles_of(trail)
    since_review = 0
    for n_ in sorted(cyc_all, reverse=True):
        notes_ = cyc_all[n_]
        if cycle_mode(notes_) == "review" and any(e.get("kind") == "end" for e in notes_):
            break
        if any(e.get("kind") == "end" for e in notes_):
            since_review += 1
    if since_review >= REVIEW_EVERY:
        items.append(f"REVIEW-DUE: {since_review} cycles since the last sense-check review. This cycle is the review "
                     "(pick --mode review). Follow references/review-prompt.md.")
    for r in work:
        name = norm(r.get("Item", ""))
        n, no_prog = counts.get(name, (0, 0))
        if n >= STALL_CYCLES or no_prog >= 2:
            why = f"{n} cycles since its last step-back" if n >= STALL_CYCLES else f"{no_prog} cycles in a row with no progress"
            items.append(f"STALL: '{r.get('Item', '')[:60]}' has {why}. This cycle is the step back (pick --mode step-back).")
    run = no_code_run(a.project, trail, sense_paths(a.project, senses))
    if len(run) >= NO_CODE_CYCLES:
        items.append(f"NO-CODE: cycles {', '.join(str(c) for c in sorted(run))} changed no product file and closed no row. This cycle "
                     "changes the product for an open row. If a measure cannot lead to a change, step back on that row.")
    if len(queue) >= 5 or (queued and not work):
        items.append(f"CRITIC-DUE: {max(len(queue), len(queued))} row(s) wait for the critic gate. Run one blind round now (pick --mode critic).")
    if gap and not work and not queued:
        has_blocked = any(status_of(r) == "blocked" for r in gap)
        step, last = next_exhausted_step(trail, has_blocked)
        why = f"the last round, cycle {last[1]}, did {last[0]}" if last else "no round has run yet"
        items.append(f"EXHAUSTED: no open rows ({len(parked)} parked). Next step: {step.upper()} ({why}). "
                     f"Pick with --mode {step}. Each step gets one round, in turn: coverage, unblock, beyond. Do not stop the loop.")

    # A chore that shows up in a second cycle is overdue. Track it by cycle number, not by brief call.
    cur = oc[0] if oc else max([e.get("cycle", 0) for e in trail] or [0]) + 1
    seen_path = os.path.join(root, "signals.json")
    try:
        seen = json.load(open(seen_path))
    except (OSError, ValueError):
        seen = {}
    if not isinstance(seen, dict):
        seen = {}
    fresh = {}
    for key, _ in chores:
        try:
            first, last_c = (int(x) for x in seen.get(key, (cur, cur)))
        except (TypeError, ValueError):
            first, last_c = cur, cur
        fresh[key] = (first if last_c >= cur - 1 else cur, cur)
    try:
        os.makedirs(root, exist_ok=True)
        json.dump(fresh, open(seen_path, "w"))
    except OSError:
        pass
    if chores or items:
        out.append("SIGNALS:")
    else:
        out.append("SIGNALS: none")
    if chores:
        out.append("  DO FIRST (small chores, in this cycle, before the item):")
        for key, msg in chores:
            first = fresh[key][0]
            tag = f"[OVERDUE since cycle {first}] " if first < cur else ""
            out.append(f"    - {tag}{msg}")
    if items:
        out.append("  THIS CYCLE'S ITEM (the first line decides):")
        out += [f"    - {m}" for m in items]
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
        if a.mode and a.mode not in MODES:
            print(f"REFUSED: --mode is one of {', '.join(MODES)}.")
            return 2
        if (a.mode or "gap") in NEEDS_WHY and not (a.why or "").strip():
            print('REFUSED: a pick needs --why: the effect that a user of this project will notice, and how it serves '
                  'the product focus in the journal\'s Direction section. If you cannot write it, pick another row, '
                  'or set this row held with "low value: <reason>".')
            return 2
        cycle = max([e.get("cycle", 0) for e in trail] or [0]) + 1
        row = a.row
    elif kind == "ack":
        if not a.drift or not text:
            print('REFUSED: ack needs --drift <sha> and the reason, for example: note ack --drift 13caac5 "the spec now adds stone"')
            return 2
        cycle = oc[0] if oc else max([e.get("cycle", 0) for e in trail] or [0])
        row = oc[1] if oc else ""
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
    commit = a.commit
    if kind == "end" and not commit:  # the end note carries the cycle's last commit
        commit = next((e.get("commit") for e in reversed(oc[2]) if e.get("commit")), None)
    mode = a.mode if kind == "pick" else None  # without --mode, the pick text decides (cycle_mode)
    for k, v in (("text", text), ("files", files), ("metrics", metrics), ("commit", commit), ("mode", mode),
                 ("why", a.why if kind == "pick" else None),
                 ("drift", a.drift.strip().lower() if kind == "ack" and a.drift else None),
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
    me = agent_pid()
    why = ""
    if os.path.exists(path):
        try:
            held = json.load(open(path))
        except (OSError, ValueError):
            held = {}
        age = (now - float(held.get("started", 0))) / 60
        holder = held.get("agent_pid")
        if me and holder == me:
            # Same agent session: this run after a context compaction, or an earlier cycle of this
            # session that ended without unlocking. The orchestrator runs one cycle at a time.
            why = " (taken back: this agent session already held it. If the brief shows a cycle IN PROGRESS, continue it)"
        elif holder and not pid_alive(holder):
            why = f" (taken over: the session that held it, agent pid {holder}, has ended)"
        elif age < a.stale_min:
            print(f"BUSY: another live agent session (agent pid {holder or '?'}, {held.get('owner', '?')}) holds the cycle "
                  f"lock, renewed {age:.0f} min ago. This run does nothing.")
            return 3
        else:
            why = f" (taken over: the lock had no note for {age:.0f} min)"
    token = os.urandom(4).hex()
    with open(path, "w") as fh:
        json.dump({"owner": a.owner, "token": token, "started": now, "agent_pid": me}, fh)
    print(f"LOCKED token={token} (owner {a.owner}, agent pid {me}){why}. Unlock with: unlock --token {token}")
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
    if a.orphan:
        os.remove(path)
        print(f"UNLOCKED: removed the lock of {held.get('owner', '?')}, a run that has ended.")
        return 0
    me = agent_pid()
    same_session = bool(me) and held.get("agent_pid") == me
    if held.get("token") and held.get("token") != a.token and not same_session:
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
    ap.add_argument("--mode", help=f"for pick: {'|'.join(MODES)} (default gap)")
    ap.add_argument("--why", help="for pick: the effect a user of this project will notice (required for work modes)")
    ap.add_argument("--drift", help="for ack: the commit whose check change you reviewed")
    ap.add_argument("--project", default=".")
    ap.add_argument("--journal", default="docs/awesomeness-loop.md")
    ap.add_argument("--root", default=".localdev/awesomeness")
    ap.add_argument("--owner", default=os.environ.get("AWESOME_OWNER", f"run-{os.getppid()}"))
    ap.add_argument("--stale-min", type=float, default=90, help="minutes with no note before a lock is stale")
    ap.add_argument("--token", help="for unlock: the token that lock printed")
    ap.add_argument("--orphan", action="store_true",
                    help="for unlock: remove a lock whose run has ended (the orchestrator uses it after a cycle subagent ends)")
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
