#!/usr/bin/env python3
"""good-night: end-of-day check-in, journal, trends and therapy-session summary.

All personal data lives OUTSIDE this repo, in ~/.local/share/good-night/
(override with GOOD_NIGHT_HOME):
  notes/DATE.md     the closing note of each day (work only)
  journal.jsonl     one check-in entry per day
  config.json       optional: the vault for closing notes
  questions.json    optional extra question set, asked after the shipped sets
  state.json        last session date

  gn.py status                  today's state: entry done?, the morning plan
                                and what happened to it, PRs merged and Jira
                                tickets I moved or updated, my
                                reviews, comments, pushes and local commits today
  gn.py note [NOTE.md] [--date D] [--replace]
                                save the closing note of the day (sections:
                                Done, In progress, Waiting on, Tomorrow first,
                                Notes); without a file, print it. With a
                                vault configured, also writes it into the
                                vault's daily note
  gn.py config [--vault PATH [--daily-folder F] [--section H]] [--no-vault]
                                optional Obsidian (or any Markdown) vault
  gn.py questions               the question sets (workday, wellbeing, extra) as JSON
  gn.py record ENTRY.json [--replace]
                                validate an entry against the questions and
                                append it to the journal
  gn.py trends [--days 14]      Markdown table of recent days, averages, and
                                the change against the days before
  gn.py session [--since DATE] [--mark]
                                summary since the last session; --mark
                                sets today as the last session date
"""
import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
GM_DIR = SKILL_DIR.parent / "good-morning"
HOME = Path(os.environ.get("GOOD_NIGHT_HOME", os.path.expanduser("~/.local/share/good-night")))
JOURNAL = HOME / "journal.jsonl"
PERSONAL_Q = HOME / "questions.json"
STATE = HOME / "state.json"
NOTES = HOME / "notes"
CONFIG = HOME / "config.json"
NOTE_SECTIONS = ("Done", "In progress", "Waiting on", "Tomorrow first", "Notes")
WORK_Q = SKILL_DIR / "questions" / "work.json"
WELLBEING_Q = SKILL_DIR / "questions" / "wellbeing.json"


def today():
    return date.today().isoformat()


def load_json(path, default):
    try:
        return json.loads(Path(path).read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_state(state):
    HOME.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=1))


def journal():
    if not JOURNAL.exists():
        return []
    rows = [json.loads(l) for l in JOURNAL.read_text().splitlines() if l.strip()]
    return sorted(rows, key=lambda r: r["date"])


def question_sets():
    sets = [load_json(WORK_Q, {"id": "work", "questions": []}),
            load_json(WELLBEING_Q, {"id": "wellbeing", "questions": []})]
    personal = load_json(PERSONAL_Q, None)
    if personal:
        sets.append(personal)
    return sets


def all_questions():
    return [(s["id"], q) for s in question_sets() for q in s["questions"]]


# ---------------------------------------------------------------- status

def plan_review():
    """Yesterday-or-today morning plan from good-morning, with current states."""
    plan = load_json(GM_DIR / "last-plan.json", None)
    if not plan:
        return {"plan_date": None, "items": [], "note": "no saved good-morning plan"}
    sys.path.insert(0, str(GM_DIR))
    try:
        from gm import JIRA_KEY, PR_URL, pr_states
        prs = pr_states([i["id"] for i in plan["items"] if PR_URL.search(str(i["id"]))])
        keys = [i["id"] for i in plan["items"] if JIRA_KEY.match(str(i["id"]))]
        jira = {}
        if keys:
            from gm_jira import Jira, jira_env
            site, email, token, _ = jira_env()
            j = Jira(site, email, token)
            for i in j.search(f"key in ({', '.join(keys)})", ["status"], limit=50):
                st = i["fields"]["status"]
                jira[i["key"]] = (st["name"], st["statusCategory"]["key"] == "done")
    except Exception as e:  # the check-in must work without GitHub or Jira
        return {"plan_date": plan.get("date"), "items": plan["items"], "note": f"states unavailable: {e}"}
    items = []
    for i in plan["items"]:
        iid = str(i["id"])
        if iid in jira:
            state, done = jira[iid]
        elif iid in prs:
            state = prs[iid]
            done = state in ("MERGED", "CLOSED")
        else:
            state, done = "unknown", None
        items.append({**i, "state": state, "done": done})
    return {"plan_date": plan.get("date"), "items": items}


CONTRIB_Q = """query($from: DateTime!) { viewer { contributionsCollection(from: $from) {
  commitContributionsByRepository(maxRepositories: 30) {
    repository { nameWithOwner } contributions(first: 1) { totalCount } }
  pullRequestContributions(first: 30) { nodes { pullRequest {
    number title url state repository { nameWithOwner } } } }
  pullRequestReviewContributions(first: 50) { nodes { pullRequestReview { state }
    pullRequest { number title url repository { nameWithOwner } } } }
  issueContributions(first: 30) { nodes { issue {
    number title url repository { nameWithOwner } } } } } } }"""


def start_of_day():
    return datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)


def github_today(out):
    from gm_common import gh_graphql, gh_json
    c = gh_graphql(CONTRIB_Q, **{"from": start_of_day().isoformat()})["viewer"]["contributionsCollection"]
    ref = lambda n: {"repo": n["repository"]["nameWithOwner"], "number": n["number"],
                     "title": n["title"], "url": n["url"]}
    out["pushed"] = [{"repo": r["repository"]["nameWithOwner"], "commits": r["contributions"]["totalCount"]}
                     for r in c["commitContributionsByRepository"]]
    out["opened_prs"] = [{**ref(n["pullRequest"]), "state": n["pullRequest"]["state"]}
                         for n in c["pullRequestContributions"]["nodes"]]
    reviews = {}
    for n in c["pullRequestReviewContributions"]["nodes"]:
        r = reviews.setdefault(n["pullRequest"]["url"], {**ref(n["pullRequest"]), "states": []})
        r["states"].append(n["pullRequestReview"]["state"])
    out["reviewed_prs"] = list(reviews.values())
    out["opened_issues"] = [ref(n["issue"]) for n in c["issueContributions"]["nodes"]]
    res = gh_json(["search", "prs", "--author", "@me", "--merged-at", f">={today()}",
                   "--json", "number,title,url,repository", "--limit", "30"])
    out["merged_prs"] = [{"repo": r["repository"]["nameWithOwner"], "number": r["number"],
                          "title": r["title"], "url": r["url"]} for r in res]
    # The search finds threads I ever commented in that anyone updated today: keep only my comments from today.
    seen = {p["url"] for k in ("opened_prs", "reviewed_prs", "merged_prs", "opened_issues") for p in out[k]}
    login = gh_json(["api", "user"])["login"]
    since = start_of_day().astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    res = gh_json(["search", "issues", "--include-prs", "--commenter", "@me", "--updated", f">={today()}",
                   "--json", "number,title,url,repository", "--limit", "30"])
    for r in res:
        if r["url"] in seen:
            continue
        repo = r["repository"]["nameWithOwner"]
        mine = gh_json(["api", f"repos/{repo}/issues/{r['number']}/comments?since={since}&per_page=100",
                        "--jq", f'[.[] | select(.user.login == "{login}")] | length'])
        if mine:
            out["commented"].append({"repo": repo, "number": r["number"], "title": r["title"],
                                     "url": r["url"], "comments": mine})


def jira_today(out):
    from gm_jira import Jira, jira_env
    site, email, token, _ = jira_env()
    j = Jira(site, email, token)
    me = j.call("/rest/api/3/myself")["accountId"]
    moved = {i["key"] for i in j.search("status changed BY currentUser() AFTER startOfDay()", ["status"], limit=50)}
    for i in j.search(f'issuekey in updatedBy("{me}", "{today()}")', ["summary", "status"], limit=50):
        out["jira"].append({"key": i["key"], "status": i["fields"]["status"]["name"], "moved": i["key"] in moved,
                            "summary": i["fields"]["summary"], "url": f"{site}/browse/{i['key']}"})


def local_today(out):
    """Commits on any branch in the good-morning projects, and ledger entries dated today."""
    import subprocess
    from gm_common import expand, load_config
    for proj in load_config().get("projects") or []:
        root = expand(proj)
        if not (root / ".git").exists():
            continue
        email = subprocess.run(["git", "-C", str(root), "config", "user.email"],
                               capture_output=True, text=True).stdout.strip()
        log = subprocess.run(["git", "-C", str(root), "log", "--all", "--no-merges", f"--author={email}",
                              f"--since={start_of_day().isoformat()}", "--format=%h %s"],
                             capture_output=True, text=True).stdout.splitlines()
        if log:
            out["local_commits"].append({"project": root.name, "commits": log})
        done = root / ".localdev" / "workflow" / "done.md"
        if done.exists():
            out["ledger_done"] += [l[3:].strip() for l in done.read_text().splitlines()
                                   if l.startswith(f"## {today()}")]


def done_today():
    """What I did today, from GitHub, Jira and the local projects (best effort per source)."""
    out = {"pushed": [], "opened_prs": [], "merged_prs": [], "reviewed_prs": [], "opened_issues": [],
           "commented": [], "jira": [], "local_commits": [], "ledger_done": [], "errors": []}
    sys.path.insert(0, str(GM_DIR))
    for name, fn in (("github", github_today), ("jira", jira_today), ("local", local_today)):
        try:
            fn(out)
        except Exception as e:  # the check-in must work without any one source
            out["errors"].append(f"{name}: {e}")
    return out


def cmd_status(_):
    rows = journal()
    entry = next((r for r in rows if r["date"] == today()), None)
    review = plan_review()
    work = done_today()
    print(f"DATE {today()} · note {'DONE' if (NOTES / f'{today()}.md').exists() else 'not written yet'} · "
          f"check-in {'DONE' if entry else 'not done yet'} · "
          f"journal {len(rows)} entries · extra questions {'yes' if PERSONAL_Q.exists() else 'no'}")
    print(f"\nMORNING PLAN ({review['plan_date'] or 'none'})" + (f" — {review['note']}" if review.get("note") else ""))
    for i in review["items"]:
        mark = "✓" if i.get("done") else "·" if i.get("done") is False else "?"
        print(f"  {mark} [{i.get('role')}] {i.get('title') or i['id']} — {i.get('state', '?')} (day {i.get('days', 1)})")
    print("\nDONE TODAY")
    pr = lambda p: f"{p['repo'].split('/')[1]}#{p['number']} {p['title'][:65]}"
    lines = [f"  merged {pr(p)}" for p in work["merged_prs"]]
    merged = {p["url"] for p in work["merged_prs"]}
    lines += [f"  opened {pr(p)} ({p['state'].lower()})" for p in work["opened_prs"] if p["url"] not in merged]
    lines += [f"  reviewed {pr(p)} ({', '.join(sorted(set(s.lower() for s in p['states'])))})"
              for p in work["reviewed_prs"]]
    lines += [f"  opened issue {pr(p)}" for p in work["opened_issues"]]
    lines += [f"  commented {pr(p)} ({p['comments']}x)" for p in work["commented"]]
    lines += [f"  pushed {r['commits']} commit(s) to {r['repo']}" for r in work["pushed"]]
    lines += [f"  jira {t['key']} {'moved to' if t['moved'] else 'updated, now'} {t['status']} — {t['summary'][:55]}"
              for t in work["jira"]]
    for c in work["local_commits"]:
        lines.append(f"  local {c['project']}: {len(c['commits'])} commit(s)")
        lines += [f"    {x[:80]}" for x in c["commits"][:8]]
    lines += [f"  ledger {x[:80]}" for x in work["ledger_done"]]
    print("\n".join(lines) if lines else "  (nothing found in GitHub, Jira or the local projects)")
    for e in work["errors"]:
        print(f"  ! {e}")
    if rows:
        last = rows[-1]
        print(f"\nLAST ENTRY {last['date']}")
    print(f"\nJOURNAL {JOURNAL}")


# ---------------------------------------------------------------- record

def validate(answers):
    errors, clean = [], {}
    for set_id, q in all_questions():
        key = q["id"]
        if key not in answers or answers[key] in (None, ""):
            if not q.get("optional"):
                errors.append(f"missing: {key}")
            continue
        v = answers[key]
        t = q["type"]
        if t in ("scale", "number"):
            try:
                v = float(v) if t == "number" else int(v)
            except (TypeError, ValueError):
                errors.append(f"{key}: not a number ({v!r})")
                continue
            if t == "scale" and not q["min"] <= v <= q["max"]:
                errors.append(f"{key}: {v} outside {q['min']}..{q['max']}")
        elif t == "bool":
            if not isinstance(v, bool):
                errors.append(f"{key}: use true or false")
        elif t == "multi":
            if not isinstance(v, list) or any(o not in [x["id"] for x in q["options"]] for o in v):
                errors.append(f"{key}: use a list of option ids {[x['id'] for x in q['options']]}")
        clean[key] = v
    unknown = sorted(set(answers) - {q["id"] for _, q in all_questions()})
    return clean, errors, unknown


def cmd_record(a):
    entry = load_json(a.entry, None)
    if entry is None:
        sys.exit(f"cannot read {a.entry}")
    answers = entry.get("answers", entry)
    clean, errors, unknown = validate(answers)
    if errors:
        sys.exit("not recorded:\n  " + "\n  ".join(errors))
    day = entry.get("date") or today()
    rows = journal()
    if any(r["date"] == day for r in rows) and not a.replace:
        sys.exit(f"{day} already has an entry; run again with --replace to overwrite it")
    rows = [r for r in rows if r["date"] != day]
    rows.append({"date": day, "recorded_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                 "answers": clean, "context": entry.get("context", {})})
    HOME.mkdir(parents=True, exist_ok=True)
    JOURNAL.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in sorted(rows, key=lambda r: r["date"])))
    os.chmod(JOURNAL, 0o600)
    print(f"recorded {day} ({len(clean)} answers)" + (f"; ignored unknown keys: {unknown}" if unknown else ""))


# ---------------------------------------------------------------- trends

def numeric_questions():
    return [q for _, q in all_questions() if q["type"] in ("scale", "number") and not q.get("hide_in_trends")]


def avg(xs):
    xs = [x for x in xs if isinstance(x, (int, float))]
    return round(sum(xs) / len(xs), 1) if xs else None


def cmd_trends(a):
    rows = journal()
    if not rows:
        print("No entries yet.")
        return
    start = (date.today() - timedelta(days=a.days - 1)).isoformat()
    prev_start = (date.today() - timedelta(days=2 * a.days - 1)).isoformat()
    cur = [r for r in rows if r["date"] >= start]
    prev = [r for r in rows if prev_start <= r["date"] < start]
    qs = numeric_questions()
    head = ["Date"] + [q.get("short", q["id"]) for q in qs] + ["Plan"]
    print(f"### Last {a.days} days ({len(cur)} entries)\n")
    print("| " + " | ".join(head) + " |")
    print("|" + "|".join("---" for _ in head) + "|")
    for r in cur:
        ans, ctx = r["answers"], r.get("context", {})
        plan = f"{ctx['plan_done']}/{ctx['plan_total']}" if ctx.get("plan_total") else ""
        print("| " + " | ".join([datetime.fromisoformat(r["date"]).strftime("%a %d")]
                                 + [str(ans.get(q["id"], "")) for q in qs] + [plan]) + " |")
    print("| **avg** | " + " | ".join(str(avg([r["answers"].get(q["id"]) for r in cur]) or "")
                                      for q in qs) + " | |")
    if prev:
        deltas = []
        for q in qs:
            c, p = avg([r["answers"].get(q["id"]) for r in cur]), avg([r["answers"].get(q["id"]) for r in prev])
            if c is not None and p is not None and c != p:
                deltas.append(f"{q.get('short', q['id'])} {p} → {c}")
        if deltas:
            print(f"\nAgainst the {a.days} days before: " + "; ".join(deltas))


# ---------------------------------------------------------------- session

def cmd_session(a):
    state = load_json(STATE, {})
    since = a.since or state.get("last_session") or (date.today() - timedelta(days=7)).isoformat()
    rows = [r for r in journal() if r["date"] > since or (a.since and r["date"] >= since)]
    qs = all_questions()
    print(f"## Since {since}: {len(rows)} entries\n")
    nums = [q for _, q in qs if q["type"] in ("scale", "number")]
    if rows and nums:
        head = ["Date"] + [q.get("short", q["id"]) for q in nums]
        print("| " + " | ".join(head) + " |")
        print("|" + "|".join("---" for _ in head) + "|")
        for r in rows:
            print("| " + " | ".join([r["date"][5:]] + [str(r["answers"].get(q["id"], "")) for q in nums]) + " |")
        print("| **avg** | " + " | ".join(str(avg([r["answers"].get(q["id"]) for r in rows]) or "") for q in nums) + " |\n")
    for _, q in qs:
        if q["type"] == "multi":
            counts = {}
            for r in rows:
                for o in r["answers"].get(q["id"], []):
                    counts[o] = counts.get(o, 0) + 1
            labels = {o["id"]: o["label"] for o in q["options"]}
            if counts:
                print(f"**{q['label']}** " + ", ".join(f"{labels.get(k, k)} ×{v}" for k, v in
                                                     sorted(counts.items(), key=lambda kv: -kv[1])) + "\n")
        if q["type"] == "bool":
            yes = sum(1 for r in rows if r["answers"].get(q["id"]) is True)
            print(f"**{q['label']}** {yes}/{len(rows)}\n")
    for _, q in qs:
        if q["type"] == "text":
            texts = [(r["date"][5:], r["answers"].get(q["id"])) for r in rows if r["answers"].get(q["id"])]
            if texts:
                print(f"**{q['label']}**")
                for d, t in texts:
                    print(f"- {d}: {t}")
                print()
    if a.mark:
        state["last_session"] = today()
        save_state(state)
        print(f"_Marked {today()} as the last session date._")


# ---------------------------------------------------------------- note

def cmd_note(a):
    day = a.date or today()
    path = NOTES / f"{day}.md"
    if not a.file:
        if not path.exists():
            sys.exit(f"no note for {day}")
        print(path.read_text())
        return
    text = Path(a.file).read_text()
    missing = [h for h in NOTE_SECTIONS if f"## {h}" not in text]
    if missing:
        sys.exit("note needs these sections: " + ", ".join(f"## {h}" for h in missing))
    if path.exists() and not a.replace:
        sys.exit(f"{day} already has a note; run again with --replace to overwrite it")
    NOTES.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(0o600)
    print(f"saved {path}")
    vault = load_json(CONFIG, {}).get("vault")
    if vault:
        try:
            print(f"vault {write_to_vault(vault, day, text)}")
        except OSError as e:  # the local note is saved; the vault copy is a bonus
            print(f"vault copy failed: {e}")


def write_to_vault(vault, day, text):
    sys.path.insert(0, str(GM_DIR))
    from gm_common import write_vault_block
    body = "\n".join("#" + l if l.startswith("## ") else l
                     for l in text.splitlines() if not l.startswith("# "))
    return write_vault_block(vault["path"], vault.get("daily_folder", "Daily"),
                             vault.get("section", "## 🌙 Closing note"), day, body, "good-night")


def cmd_config(a):
    cfg = load_json(CONFIG, {})
    if a.no_vault:
        cfg.pop("vault", None)
    elif a.vault:
        cfg["vault"] = {"path": a.vault, "daily_folder": a.daily_folder, "section": a.section}
    if a.no_vault or a.vault:
        HOME.mkdir(parents=True, exist_ok=True)
        CONFIG.write_text(json.dumps(cfg, indent=1, ensure_ascii=False))
    print(json.dumps(cfg, indent=1, ensure_ascii=False) if cfg else "no config: notes stay in " + str(NOTES))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    n = sub.add_parser("note")
    n.add_argument("file", nargs="?")
    n.add_argument("--date")
    n.add_argument("--replace", action="store_true")
    sub.add_parser("questions")
    c = sub.add_parser("config")
    c.add_argument("--vault", help="vault root; the closing note also goes into its daily note")
    c.add_argument("--daily-folder", default="Daily")
    c.add_argument("--section", default="## 🌙 Closing note",
                   help="heading in the daily note; the note goes at the end of that section")
    c.add_argument("--no-vault", action="store_true")
    r = sub.add_parser("record")
    r.add_argument("entry")
    r.add_argument("--replace", action="store_true")
    t = sub.add_parser("trends")
    t.add_argument("--days", type=int, default=14)
    s = sub.add_parser("session")
    s.add_argument("--since")
    s.add_argument("--mark", action="store_true")
    a = p.parse_args()
    if a.cmd == "questions":
        print(json.dumps(question_sets(), indent=1, ensure_ascii=False))
    else:
        {"status": cmd_status, "record": cmd_record, "trends": cmd_trends,
         "session": cmd_session, "note": cmd_note, "config": cmd_config}[a.cmd](a)


if __name__ == "__main__":
    main()
