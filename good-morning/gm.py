#!/usr/bin/env python3
"""good-morning entry point.

  gm.py collect             run every collector at the same time, save the raw
                            JSON in a run directory, print a short digest
                            with candidate rungs (Fire / Unblock / Finish /
                            Focus / FYI), newest first
  gm.py render PLAN.json    print the plan as the terminal report (Markdown);
                            with --format html, write the HTML day sheet and
                            print its path (--open opens it)
  gm.py show                print today's last rendered plan again, with no
                            collection; exits 1 when no plan for today exists
  gm.py save PLAN.json      store the accepted plan for carry-over and move
                            the window (last_run) to the collection start

The digest is a proposal. The agent reads it, checks what needs judgment,
and writes PLAN.json (format: references/plan-schema.md).
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from gm_common import (PENDING_PATH, PLAN_PATH, SKILL_DIR, TODAY_PATH, age, gh_graphql, iso, load_config, parse_ts, write_vault_block,
                       utcnow, window_start, write_config)

PY = sys.executable
JIRA_KEY = re.compile(r"^[A-Z][A-Z0-9]+-\d+$")
PR_URL = re.compile(r"github\.com/([^/]+)/([^/]+)/(?:pull|issues)/(\d+)")


def runs_root():
    return Path(tempfile.gettempdir()) / "good-morning"


def collect(cfg):
    now = utcnow()
    start, label = window_start(cfg, now)
    since = iso(start)
    run_dir = runs_root() / now.strftime("%Y%m%dT%H%M%SZ")
    run_dir.mkdir(parents=True, exist_ok=True)

    prev = json.loads(PLAN_PATH.read_text()) if PLAN_PATH.exists() else None
    carry_keys = [i["id"] for i in (prev or {}).get("items", []) if JIRA_KEY.match(str(i.get("id", "")))]

    gh = [PY, str(SKILL_DIR / "gm_github.py"), "--since", since, "--stale-days", str(cfg["stale_days"])]
    for r in cfg["repos"]:
        gh += ["--repo", r]
    for o in cfg["orgs"]:
        gh += ["--org", o]
    for b in cfg["protected_branches"]:
        gh += ["--branch", b]
    jira = [PY, str(SKILL_DIR / "gm_jira.py"), "--since", since, "--stale-days", str(cfg["stale_days"])]
    for k in carry_keys:
        jira += ["--key", k]
    chat = [PY, str(SKILL_DIR / "gm_chat.py"), "--since", since]
    if cfg.get("rocket_username"):
        chat += ["--me", str(cfg["rocket_username"])]
    if cfg.get("rocket_profile"):
        chat += ["--profile", str(cfg["rocket_profile"])]
    ledger = [PY, str(SKILL_DIR / "gm_ledger.py")]
    for pr in cfg["projects"]:
        ledger += ["--project", str(pr)]

    jobs = {"github": gh, "jira": jira, "chat": chat, "ledger": ledger}

    def go(item):
        name, cmd = item
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=SKILL_DIR, timeout=600)
        (run_dir / f"{name}.json").write_text(res.stdout)
        if res.returncode != 0 or not res.stdout.strip():
            return name, None, (res.stderr.strip().splitlines() or ["no output"])[-1][:300]
        return name, json.loads(res.stdout), None

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(go, jobs.items()))
    data = {n: d for n, d, _ in results}
    failed = {n: e for n, _, e in results if e}

    meta = {"started_at": iso(now), "since": since, "label": label, "run_dir": str(run_dir),
            "failed": failed, "config_exists": cfg["_exists"]}
    (run_dir / "meta.json").write_text(json.dumps(meta, indent=1))
    PENDING_PATH.write_text(json.dumps(meta, indent=1))
    print(digest(cfg, meta, data, prev))


def fmt(items, line, limit=12):
    rows = [line(i) for i in items[:limit]]
    if len(items) > limit:
        rows.append(f"  … {len(items) - limit} more (see the JSON)")
    return rows or ["  (none)"]


def digest(cfg, meta, data, prev):
    gh, jira, chat, led = (data.get(k) or {} for k in ("github", "jira", "chat", "ledger"))
    hours = round((parse_ts(meta["started_at"]) - parse_ts(meta["since"])).total_seconds() / 3600)
    out = [f"WINDOW {meta['since']} → {meta['started_at']} ({hours}h, {meta['label']})",
           f"RUN DIR {meta['run_dir']}  (github.json jira.json chat.json ledger.json)"]
    status = []
    for name, d in (("jira", jira), ("chat", chat), ("github", gh), ("ledger", led)):
        if name in meta["failed"]:
            status.append(f"{name} FAILED: {meta['failed'][name]}")
        elif d.get("errors"):
            status.append(f"{name} partial: {'; '.join(d['errors'])}")
        else:
            status.append(f"{name} ok")
    if gh.get("truncated"):
        status.append(f"github truncated: {', '.join(gh['truncated'])}")
    if chat.get("refreshing"):
        status.append("chat cache refreshing (counts may lag)")
    out.append("SOURCES " + " | ".join(status))

    # carry-over
    if prev:
        today = utcnow().astimezone().strftime("%Y-%m-%d")
        bump = 0 if prev.get("date") == today else 1
        out.append(f"\nCARRY-OVER from plan of {prev.get('date')}")
        keys = jira.get("keys", {})
        pr_state = pr_states([i["id"] for i in prev.get("items", []) if PR_URL.search(str(i.get("id", "")))])
        for i in prev.get("items", []):
            iid = str(i.get("id", ""))
            state = keys.get(iid, {}).get("status") if JIRA_KEY.match(iid) else pr_state.get(iid)
            done = (keys.get(iid, {}).get("done") if JIRA_KEY.match(iid)
                    else state in ("MERGED", "CLOSED") if state else None)
            mark = "DONE" if done else "open" if done is False else "?"
            out.append(f"  [{i.get('role')}] {iid} {i.get('title', '')[:70]} — now {state or 'unknown'} "
                       f"({mark}, day {i.get('days', 1) + (0 if done else bump)})")

    out += good_night_lines()

    fire, unblock, finish, focus, fyi = [], [], [], [], []

    for rh in gh.get("release_health", []):
        for r in rh["run_problems"]:
            if r["conclusion"] in ("failure", "timed_out", "startup_failure"):
                fire.append(f"  CI {r['conclusion']}: {r['workflow']} on {r['ref']} ({r['age']}) {r['url']}")
            else:
                fyi.append(f"  CI {r['status']}: {r['workflow']} on {r['ref']} ({r['age']})")
        drafts = rh["drafts"]
        if drafts:
            finish.append(f"  draft release(s) waiting to publish: {', '.join(drafts)} ({rh['repo']})")
        latest = next((r for r in rh["releases"] if r["latest"]), None)
        if latest:
            fyi.append(f"  latest release {rh['repo'].split('/')[1]} {latest['tag']} ({latest['age']} ago)")
        for p in rh["open_prs_into_release_branches"]:
            line = f"  PR into {p['base']}: #{p['number']} {p['title'][:60]} ({p['age']}) {p['url']}"
            (fyi if p["bot"] else finish).append(line + (" [bot]" if p["bot"] else ""))

    for t in jira.get("queue", []):
        if t["priority_project"]:
            fire.append(f"  {t['key']} [{t['priority']}/{t['status']}] {t['summary'][:70]} ({t['age']}) {t['url']}")
    for m in jira.get("moved_by_others", []):
        who = sorted({c["by"] for c in m["changes"] + m["comments"]})
        what = [f"{c['field']}→{c['to']}" for c in m["changes"] if c["field"] != "description"][:3]
        what += [f"comment: \"{c['text'][:90]}\"" for c in m["comments"][:1]]
        line = (f"  {m['key']} [{m['priority']}/{m['status']}] by {', '.join(who)} ({m['age']}): "
                f"{'; '.join(what) or 'description edit'} {m['url']}")
        if m["priority_project"]:
            fire.append(line)
        elif m["asks_me"]:
            unblock.append(line + "  [mentions me]")
        else:
            fyi.append(line)
    for w in jira.get("watched", []):
        unblock.append(f"  move to {w['move_to']}: {w['key']} [{w['status']}] {w['summary'][:70]} "
                       f"({w['assignee'] or 'unassigned'}, created {w['age']} ago) {w['url']}")
    for n in jira.get("new_to_me", []):
        fyi.append(f"  NEW to me: {n['key']} [{n['priority']}] from {n['reporter']} ({n['age']}) {n['summary'][:60]}")

    for kind, items in (("mention", chat.get("mentions", [])), ("DM", chat.get("dms", [])),
                        ("thread", chat.get("threads", []))):
        for i in items:
            state = ("unanswered" if not i.get("answered") else
                     f"answered, {i['others_after_my_last']} after" if i.get("others_after_my_last") else "answered")
            line = f"  chat {kind} by {i['author']} in {i['room']} ({i['age']}, {state}): \"{i['text'][:110]}\" {i['link']}"
            (unblock if not i.get("answered") or i.get("others_after_my_last") else fyi).append(line)

    for r in gh.get("review_requests", []):
        unblock.append(f"  review requested: {r['repo'].split('/')[1]}#{r['number']} by {r['author']} "
                       f"({r['age']}) {r['title'][:60]} {r['url']}")
    seen = set()
    for n in gh.get("notifications", []):
        if n.get("awaiting_me"):
            seen.add(n["url"])
            lo = n.get("last_other") or {}
            tag = "ASKS" if n.get("asks_me") else "ack?"
            unblock.append(f"  [{tag}] {n['repo'].split('/')[1]}#{n['number']} {lo.get('author')} ({age(lo.get('at'))}): "
                           f"\"{(lo.get('text') or '')[:110]}\" {n['url']}")
    for i in gh.get("issue_activity", []):
        if i["awaiting_me"] and i["url"] not in seen:
            unblock.append(f"  issue #{i['number']} {i['title'][:50]} ({i['age']}) {i['url']}")
        elif i["opened_in_window"]:
            fyi.append(f"  new issue #{i['number']} by {i['author']} {i['title'][:60]} ({i['age']})")

    my = gh.get("my_prs", [])
    into_release = {p["url"] for rh in gh.get("release_health", []) for p in rh["open_prs_into_release_branches"]}
    for p in my:
        if p["stale"] or p["url"] in into_release:
            continue
        if p["awaiting_me"] and p["url"] not in seen:
            unblock.append(f"  feedback on my PR #{p['number']} from {p['last_other']['author']} ({p['age']}) {p['url']}")
        state = "draft" if p["draft"] else p["review"] or "no review"
        checks = p["checks"] or "no checks"
        if p["failing_checks"]:
            checks += f" ({', '.join(p['failing_checks'][:3])})"
        finish.append(f"  my PR {p['repo'].split('/')[1]}#{p['number']} [{checks}, {state}, "
                      f"{p['unresolved_human_threads']}/{p['unresolved_threads']} human/all threads] "
                      f"{p['title'][:55]} ({p['age']}) {p['url']}")
    for t in jira.get("queue", []):
        if t["status"] in ("In Progress", "Changes Requested", "in QA", "In Review", "Waiting Review") \
                and not t["stale"]:
            finish.append(f"  {t['key']} [{t['priority']}/{t['status']}] {t['summary'][:70]} ({t['age']}) {t['url']}")
    focus_rows = [t for t in jira.get("queue", []) if t["status"] in ("Ready for Dev", "To Do")]
    for t in focus_rows[:6]:
        fv = f" fix:{','.join(t['fix_versions'])}" if t["fix_versions"] else ""
        focus.append(f"  {t['key']} [{t['priority']}/{t['status']}{fv}] {t['summary'][:70]} ({t['age']}) {t['url']}")

    for name, label in (("FIRE", fire), ("UNBLOCK", unblock), ("FINISH", finish), ("FOCUS", focus)):
        out.append(f"\n{name} candidates")
        out += fmt(label, lambda x: x)

    stale = [p for p in my if p["stale"]]
    stale_t = [t for t in jira.get("queue", []) if t["stale"] and t["status"] in ("In Progress", "Changes Requested")]
    out.append(f"\nSTALE ({cfg['stale_days']}d+): {len(stale)} my PRs, {len(stale_t)} in-flight tickets")
    if stale:
        out.append("  PRs: " + ", ".join(f"{p['repo'].split('/')[1]}#{p['number']}({p['age']}"
                                          f"{',red' if p['checks'] == 'FAILURE' else ''})" for p in stale))
    for t in stale_t:
        out.append(f"  {t['key']} [{t['status']}] {t['summary'][:60]} ({t['age']})")

    out.append("\nLEDGER")
    for p in led.get("projects", []):
        for c in p["cards"]:
            hint = ("  ← all named PRs closed: verify, maybe close"
                    if c["all_prs_closed"] and c["status"] != "blocked" else "")
            out.append(f"  card [{c['status']}] {c['title'][:70]}{hint}")
        for b in p["blockers"]:
            out.append(f"  BLOCKER ({b['age']}) {b['title'][:60]} | default: {b['default']}")

    out.append("\nFYI")
    out += fmt(fyi, lambda x: x, limit=15)
    rooms = chat.get("channel_rooms", [])
    older = chat.get("older_unread", {})
    out.append(f"  chat channels: {sum(r['count'] for r in rooms)} new in {len(rooms)} rooms; "
               f"{sum(older.values())} older unread left out")
    for r in rooms[:6]:
        s = r["samples"][0]
        out.append(f"    {r['room']}: {r['count']} ({r['age']}) {s['author']}: \"{s['text'][:90]}\"")
    quiet = [n for n in gh.get("notifications", []) if not n.get("awaiting_me")]
    newp = gh.get("new_prs", [])
    out.append(f"  github: {len(quiet)} notifications need nothing; {len(newp)} new PRs "
               f"({sum(p['bot'] for p in newp)} bot) in watched repos")
    for p in [p for p in newp if not p["bot"]][:5]:
        out.append(f"    new PR #{p['number']} by {p['author']} {p['title'][:60]} ({p['age']})")
    return "\n".join(out)


def good_night_lines():
    """The last closing note from good-night. Reads only notes/, never the wellbeing journal."""
    import os
    notes = Path(os.environ.get("GOOD_NIGHT_HOME", os.path.expanduser("~/.local/share/good-night"))) / "notes"
    files = sorted(notes.glob("*.md")) if notes.exists() else []
    if not files:
        return []
    sections, current = {}, None
    for line in files[-1].read_text().splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            sections[current] = []
        elif current and line.strip():
            sections[current].append(line.strip())
    out = [f"\nCLOSING NOTE {files[-1].stem} (good-night)"]
    for name in ("Tomorrow first", "In progress", "Waiting on"):
        items = [l for l in sections.get(name, []) if l.lstrip("-* ").lower() not in ("", "none", "-")]
        if items:
            out.append(f"  {name.lower()}:")
            out += [f"    {l}" for l in items[:6]]
    return out


def pr_states(urls):
    """Current state of each PR URL, in one GraphQL call."""
    parts, keys = [], {}
    for i, u in enumerate(urls):
        m = PR_URL.search(u)
        if not m:
            continue
        keys[f"p{i}"] = u
        parts.append(f'p{i}: repository(owner: "{m[1]}", name: "{m[2]}") {{ issueOrPullRequest(number: {m[3]}) '
                     f'{{ ... on PullRequest {{ state }} ... on Issue {{ state }} }} }}')
    if not parts:
        return {}
    try:
        data = gh_graphql("query { " + " ".join(parts) + " }")
    except Exception:
        return {}
    return {keys[k]: ((v or {}).get("issueOrPullRequest") or {}).get("state") for k, v in data.items()}


def vault_markdown(plan):
    """A compact plan for the vault's daily note: links, no tables."""
    def ln(i, title_key="title"):
        t, u = i.get(title_key) or i.get("what") or i.get("id"), i.get("url")
        return f"[{t}]({u})" if u else str(t)
    out = []
    m = plan.get("main")
    if m:
        out += [f"### Main focus: {ln(m)}"] + ([m["why"]] if m.get("why") else [])
        out += [f"- First step: {m['first_step']}"] * bool(m.get("first_step"))
        out += [f"- Done when: {m['done_when']}"] * bool(m.get("done_when"))
    if plan.get("unblock"):
        out += ["", f"### Unblock (~{plan.get('unblock_minutes', 60)} min)"]
        out += [f"- [ ] {u.get('who', '')} — {ln(u, 'what')}" for u in plan["unblock"]]
    if plan.get("secondary"):
        out += ["", "### Secondary"] + [f"- [ ] {ln(s)}" + (f" — {s['why']}" if s.get("why") else "")
                                        for s in plan["secondary"]]
    if plan.get("not_today"):
        out += ["", "### Not today"] + [f"- {ln(n)} — {n.get('reason', '')}" for n in plan["not_today"]]
    return "\n".join(out)


def cache_today(plan_path):
    """Keep a copy of the latest rendered plan, so `show` can print it again."""
    TODAY_PATH.write_text(Path(plan_path).read_text())


def show():
    today = utcnow().astimezone().strftime("%Y-%m-%d")
    plan = json.loads(TODAY_PATH.read_text()) if TODAY_PATH.exists() else {}
    if plan.get("date") != today:
        print(f"no cached plan for {today}; run `gm.py collect`")
        sys.exit(1)
    from datetime import datetime
    from gm_render import render_markdown
    cached = datetime.fromtimestamp(TODAY_PATH.stat().st_mtime).astimezone()
    print(f"_Cached plan from {cached:%H:%M} ({age(iso(cached))} ago). Say \"refresh\" to collect again._\n")
    print(render_markdown(TODAY_PATH))


def save(cfg, plan_path):
    plan = json.loads(Path(plan_path).read_text())
    cache_today(plan_path)
    pending = json.loads(PENDING_PATH.read_text()) if PENDING_PATH.exists() else {}
    prev = json.loads(PLAN_PATH.read_text()) if PLAN_PATH.exists() else {}
    prev_days = {i["id"]: i.get("days", 1) for i in prev.get("items", [])}
    today = utcnow().astimezone().strftime("%Y-%m-%d")
    new_day = prev.get("date") != today
    items = []
    for role, entries in (("main", [plan["main"]] if plan.get("main") else []),
                          ("secondary", plan.get("secondary", [])), ("unblock", plan.get("unblock", []))):
        for e in entries:
            iid = e.get("id") or e.get("url") or e.get("title")
            days = prev_days.get(iid, 0) + 1 if new_day else prev_days.get(iid, 1)
            title = e.get("title") or f"{e.get('who', '')}: {e.get('what', '')}".strip(": ")
            items.append({"id": iid, "title": title, "role": role,
                          "url": e.get("url"), "days": days})
    PLAN_PATH.write_text(json.dumps({"date": today, "items": items, "plan": plan}, indent=1))
    if pending.get("started_at"):
        cfg["last_run"] = pending["started_at"]
    write_config(cfg)
    print(f"saved {len(items)} items to {PLAN_PATH}; last_run = {cfg['last_run']}")
    if cfg.get("vault_path"):
        try:
            path = write_vault_block(cfg["vault_path"], cfg.get("vault_daily_folder"),
                                     cfg.get("vault_section") or "## 🎯 Today's Focus",
                                     today, vault_markdown(plan), "good-morning")
            print(f"vault {path}")
        except OSError as e:  # the plan is saved; the vault copy is a bonus
            print(f"vault copy failed: {e}")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("collect")
    sub.add_parser("show")
    r = sub.add_parser("render")
    r.add_argument("plan")
    r.add_argument("--format", choices=("md", "html"), default="md",
                   help="md (default): terminal report on stdout; html: the day sheet file")
    r.add_argument("--open", action="store_true")
    r.add_argument("--fragment", action="store_true", help="page body only (for an Artifact publish)")
    r.add_argument("--out")
    s = sub.add_parser("save")
    s.add_argument("plan")
    a = p.parse_args()
    cfg = load_config()
    if a.cmd == "collect":
        collect(cfg)
    elif a.cmd == "show":
        show()
    elif a.cmd == "render" and a.format == "md":
        from gm_render import render_markdown
        cache_today(a.plan)
        print(render_markdown(Path(a.plan)))
    elif a.cmd == "render":
        from gm_render import render
        path = render(Path(a.plan), fragment=a.fragment, out=a.out)
        print(path)
        if a.open:
            subprocess.run(["open", str(path)])
    elif a.cmd == "save":
        save(cfg, a.plan)


if __name__ == "__main__":
    main()
