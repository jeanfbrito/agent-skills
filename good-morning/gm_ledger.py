#!/usr/bin/env python3
"""Ledger slice of the good-morning briefing, as JSON on stdout.

Reads `.localdev/workflow/todo.md` and `blockers.md` in each project and
checks the PRs that each open card names.

  cards     open cards with status, attempts, the PRs they name and the
            current state of each PR; `all_prs_closed` when every named PR is
            merged or closed (a hint that the card may be stale; a card can also name an old PR as context)
  blockers  active blockers with their age and their "default if no answer"

  gm_ledger.py --project ~/Github/Rocket.Chat.Electron
"""
import argparse
import json
import re
import subprocess
import sys

from gm_common import age, expand, gh_graphql, iso, parse_ts, utcnow
from datetime import datetime

CARD = re.compile(r"^## \[(?P<status>[^\]]+)\]\s*(?P<title>.+)$")
BLOCKER = re.compile(r"^## (?P<when>\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2})?)\s*[—-]\s*(?P<title>.+)$")
PR_REF = re.compile(r"(?:PR\s*)?#(\d{3,6})\b")
JIRA_REF = re.compile(r"\b([A-Z][A-Z0-9]+-\d+)\b")


def sections(text, header):
    cur = None
    for line in text.splitlines():
        m = header.match(line)
        if m:
            if cur:
                yield cur
            cur = {"m": m, "body": []}
        elif line.startswith("## ") or line.startswith("# "):
            if cur:
                yield cur
            cur = None
        elif cur is not None:
            cur["body"].append(line)
    if cur:
        yield cur


def field(body, name):
    for line in body:
        m = re.match(rf"^- {name}:\s*(.+)$", line.strip())
        if m:
            return m.group(1).strip()
    return None


def repo_of(path):
    url = subprocess.run(["git", "-C", str(path), "remote", "get-url", "origin"],
                         capture_output=True, text=True).stdout.strip()
    m = re.search(r"github\.com[:/]([^/]+)/(.+?)(?:\.git)?$", url)
    return (m.group(1), m.group(2)) if m else None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--project", action="append", default=[])
    a = p.parse_args()
    now = utcnow()
    out = {"generated_at": iso(now), "projects": [], "errors": []}

    for proj in a.project:
        path = expand(proj)
        wf = path / ".localdev" / "workflow"
        entry = {"project": str(path), "cards": [], "blockers": []}
        out["projects"].append(entry)
        if not wf.exists():
            entry["note"] = "no .localdev/workflow"
            continue
        todo = (wf / "todo.md").read_text() if (wf / "todo.md").exists() else ""
        for s in sections(todo, CARD):
            status = s["m"]["status"].strip().lower()
            if status in ("done", "cancelled", "closed"):
                continue
            body = "\n".join(s["body"])
            entry["cards"].append({
                "status": status, "title": s["m"]["title"].strip(),
                "attempts": field(s["body"], "Attempts"), "next": field(s["body"], "Next action")
                or field(s["body"], "Next"), "deps": field(s["body"], "Deps"),
                "prs": sorted({int(n) for n in PR_REF.findall(s["m"]["title"] + "\n" + body)}),
                "jira": sorted(set(JIRA_REF.findall(s["m"]["title"] + "\n" + body))),
            })
        blockers = (wf / "blockers.md").read_text() if (wf / "blockers.md").exists() else ""
        for s in sections(blockers, BLOCKER):
            when = s["m"]["when"]
            try:
                ts = datetime.strptime(when, "%Y-%m-%d %H:%M" if " " in when else "%Y-%m-%d").astimezone()
            except ValueError:
                ts = None
            entry["blockers"].append({"title": s["m"]["title"].strip(), "since": when,
                                      "age": age(ts, now) if ts else "?",
                                      "need": field(s["body"], "What I need"),
                                      "default": field(s["body"], "Default if no answer")})

        repo = repo_of(path)
        numbers = sorted({n for c in entry["cards"] for n in c["prs"]})
        states = {}
        if repo and numbers:
            try:
                q = " ".join(f'p{n}: issueOrPullRequest(number: {n}) {{ ... on PullRequest {{ state mergedAt '
                             f'updatedAt url title }} ... on Issue {{ state updatedAt url title }} }}'
                             for n in numbers)
                data = gh_graphql(f'query {{ repository(owner: "{repo[0]}", name: "{repo[1]}") {{ {q} }} }}')
                states = {int(k[1:]): v for k, v in data["repository"].items() if v}
            except Exception as e:
                out["errors"].append(f"{path.name} PR states: {e}")
        for c in entry["cards"]:
            c["pr_states"] = [{"number": n, **{k: states[n].get(k) for k in ("state", "mergedAt", "url")}}
                              for n in c["prs"] if n in states]
            closed = [s for s in c["pr_states"] if s["state"] in ("MERGED", "CLOSED")]
            c["all_prs_closed"] = bool(c["pr_states"]) and len(closed) == len(c["pr_states"])

    json.dump(out, sys.stdout, indent=1)
    print()


if __name__ == "__main__":
    main()
