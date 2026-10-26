#!/usr/bin/env python3
"""Jira slice of the good-morning briefing, as JSON on stdout.

Talks to the Jira Cloud REST API. Credentials: ATLASSIAN_EMAIL and
JIRA_API_TOKEN (and optional JIRA_SITE) from the environment, else the token
that the jira skill keeps in the macOS Keychain (`jira/jira-env.sh`).

Sections:
  queue             my unresolved tickets, priority projects first, then by
                    priority and last update
  moved_by_others   tickets I am assignee, reporter or watcher of where SOMEONE
                    ELSE changed a field or commented inside the window;
                    my own edits are left out
  new_to_me         tickets created inside the window and assigned to me by
                    someone else
  watched           unresolved tickets that match the jira skill's
                    `defaults.watch_jql` (e.g. new Desktop tickets filed in
                    CORE that still need a move to DSK)
  keys              status of each --key (carry-over items from the last plan)

  gm_jira.py --since 2026-10-14T09:00:00Z
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from gm_common import age, days_since, iso, parse_ts, short, utcnow

JIRA_DIR = Path(os.path.expanduser("~/Github/agent-skills/jira"))
PRIORITY_RANK = {"Highest": 0, "High": 1, "Medium": 2, "Low": 3, "Lowest": 4}
TRACKED_FIELDS = {"status", "assignee", "priority", "Fix Version", "resolution", "Sprint", "summary",
                  "description", "labels", "Link"}


def jira_env():
    """Load site, email and token the same way the jira skill does."""
    cfg = (JIRA_DIR / "local-config.yml").read_text() if (JIRA_DIR / "local-config.yml").exists() else ""

    def read(key):
        for line in cfg.splitlines():
            if line.strip().startswith(key + ":"):
                return line.split(":", 1)[1].split(" #")[0].strip().strip('"')
        return ""

    email, token = os.environ.get("ATLASSIAN_EMAIL"), os.environ.get("JIRA_API_TOKEN")
    if not (email and token) and (JIRA_DIR / "jira-env.sh").exists():  # macOS Keychain via the jira skill
        env = subprocess.run(["bash", "-c", f"source '{JIRA_DIR}/jira-env.sh' >/dev/null 2>&1; "
                                            'printf "%s\\n%s" "$ATLASSIAN_EMAIL" "$JIRA_API_TOKEN"'],
                             capture_output=True, text=True).stdout.split("\n")
        email, token = (env + ["", ""])[:2]
    site = os.environ.get("JIRA_SITE") or read("site") or "https://rocketchat.atlassian.net"
    prio = [p.strip() for p in read("priority_projects").split(",") if p.strip()]
    jira_env.watch = (read("watch_jql"), read("primary_project"))
    if not email or not token:
        raise RuntimeError(f"no Jira token: set ATLASSIAN_EMAIL and JIRA_API_TOKEN, or run {JIRA_DIR}/setup.sh")
    return site.rstrip("/"), email, token, prio


class Jira:
    def __init__(self, site, email, token):
        self.site = site
        self.auth = "Basic " + base64.b64encode(f"{email}:{token}".encode()).decode()

    def call(self, path, body=None):
        req = urllib.request.Request(
            self.site + path, data=json.dumps(body).encode() if body is not None else None,
            headers={"Authorization": self.auth, "Accept": "application/json",
                     "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Jira {path.split('?')[0]}: HTTP {e.code} {e.read()[:200]!r}")

    def search(self, jql, fields, expand=None, limit=100):
        issues, token = [], None
        while len(issues) < limit:
            body = {"jql": jql, "fields": fields, "maxResults": min(50, limit - len(issues))}
            if expand:
                body["expand"] = expand
            if token:
                body["nextPageToken"] = token
            page = self.call("/rest/api/3/search/jql", body)
            issues += page.get("issues", [])
            token = page.get("nextPageToken")
            if page.get("isLast", True) or not token:
                break
        return issues


def adf_text(node, me_id=None, hits=None):
    """Flatten Atlassian Document Format to text; record mentions of me."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if node.get("type") == "text":
        return node.get("text", "")
    if node.get("type") == "mention":
        if hits is not None and node.get("attrs", {}).get("id") == me_id:
            hits.append(True)
        return node.get("attrs", {}).get("text", "@?")
    sep = "\n" if node.get("type") in ("paragraph", "heading", "listItem") else ""
    return sep.join(adf_text(c, me_id, hits) for c in node.get("content", []))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--since", required=True, help="ISO-8601 UTC window start")
    p.add_argument("--stale-days", type=int, default=7)
    p.add_argument("--key", action="append", default=[], help="also report the status of this key")
    a = p.parse_args()

    now = utcnow()
    since = parse_ts(a.since)
    site, email, token, prio = jira_env()
    j = Jira(site, email, token)
    me = j.call("/rest/api/3/myself")
    me_id = me["accountId"]
    out = {"site": site, "me": me["displayName"], "since": a.since, "generated_at": iso(now),
           "priority_projects": prio, "errors": []}

    def link(key):
        return f"{site}/browse/{key}"

    def section(name, fn):
        try:
            out[name] = fn()
        except Exception as e:
            out[name] = []
            out["errors"].append(f"{name}: {e}")

    def queue():
        issues = j.search("assignee = currentUser() AND resolution = Unresolved AND statusCategory != Done",
                          ["summary", "status", "priority", "updated", "fixVersions", "project", "issuetype"],
                          limit=200)
        rows = []
        for i in issues:
            f = i["fields"]
            rows.append({
                "key": i["key"], "url": link(i["key"]), "summary": f["summary"],
                "status": f["status"]["name"], "status_category": f["status"]["statusCategory"]["key"],
                "priority": (f.get("priority") or {}).get("name", "Unprioritized"),
                "type": f["issuetype"]["name"], "project": f["project"]["key"],
                "fix_versions": [v["name"] for v in f.get("fixVersions") or []],
                "priority_project": f["project"]["key"] in prio,
                "updated": f["updated"], "age": age(f["updated"], now),
                "stale": (days_since(f["updated"], now) or 0) >= a.stale_days,
            })
        rows.sort(key=lambda r: (not r["priority_project"], PRIORITY_RANK.get(r["priority"], 9),
                                 -(parse_ts(r["updated"]).timestamp())))
        return rows

    section("queue", queue)

    def watched():
        jql, target = getattr(jira_env, "watch", ("", ""))
        if not jql:
            return []
        rows = []
        for i in j.search(jql, ["summary", "status", "priority", "assignee", "created", "project"], limit=50):
            f = i["fields"]
            rows.append({"key": i["key"], "url": link(i["key"]), "summary": f["summary"],
                         "status": f["status"]["name"], "priority": (f.get("priority") or {}).get("name"),
                         "assignee": (f.get("assignee") or {}).get("displayName"),
                         "created": f["created"], "age": age(f["created"], now), "move_to": target})
        return rows

    section("watched", watched)

    def moved_and_new():
        local = since.astimezone().strftime("%Y-%m-%d %H:%M")
        jql = (f"(assignee = currentUser() OR reporter = currentUser() OR watcher = currentUser()) "
               f"AND updated >= '{local}' ORDER BY updated DESC")
        issues = j.search(jql, ["summary", "status", "priority", "assignee", "reporter", "created",
                                "updated", "comment", "project"], expand="changelog", limit=60)
        moved, new = [], []
        for i in issues:
            f = i["fields"]
            changes = []
            for h in i.get("changelog", {}).get("histories", []):
                at = parse_ts(h["created"])
                who = h.get("author", {})
                if at < since or who.get("accountId") == me_id:
                    continue
                for it in h["items"]:
                    if it["field"] in TRACKED_FIELDS:
                        changes.append({"by": who.get("displayName"), "at": iso(at), "field": it["field"],
                                        "from": short(it.get("fromString"), 80),
                                        "to": short(it.get("toString"), 120)})
            comments = []
            for c in f.get("comment", {}).get("comments", []):
                at = parse_ts(c["created"])
                if at < since or c["author"].get("accountId") == me_id:
                    continue
                hits = []
                text = adf_text(c.get("body"), me_id, hits)
                comments.append({"by": c["author"]["displayName"], "at": iso(at),
                                 "mentions_me": bool(hits), "text": short(text, 280)})
            assignee = (f.get("assignee") or {}).get("accountId")
            reporter = f.get("reporter") or {}
            base = {"key": i["key"], "url": link(i["key"]), "summary": f["summary"],
                    "status": f["status"]["name"], "priority": (f.get("priority") or {}).get("name"),
                    "assigned_to_me": assignee == me_id, "reporter": reporter.get("displayName"),
                    "priority_project": f["project"]["key"] in prio}
            created = parse_ts(f["created"])
            if created >= since and assignee == me_id and reporter.get("accountId") != me_id:
                new.append({**base, "created": iso(created), "age": age(created, now)})
            if changes or comments:
                latest = max([c["at"] for c in changes + comments])
                moved.append({**base, "changes": sorted(changes, key=lambda c: c["at"], reverse=True),
                              "comments": sorted(comments, key=lambda c: c["at"], reverse=True),
                              "asks_me": any(c["mentions_me"] for c in comments),
                              "updated": latest, "age": age(latest, now)})
        moved.sort(key=lambda m: m["updated"], reverse=True)
        new.sort(key=lambda m: m["created"], reverse=True)
        return {"moved_by_others": moved, "new_to_me": new, "checked": len(issues)}

    try:
        res = moved_and_new()
        out.update(res)
    except Exception as e:
        out.update({"moved_by_others": [], "new_to_me": [], "checked": 0})
        out["errors"].append(f"moved_by_others: {e}")

    if a.key:  # carry-over items from yesterday's plan
        try:
            found = j.search(f"key in ({', '.join(a.key)})", ["status", "resolution", "summary"], limit=50)
            out["keys"] = {i["key"]: {"status": i["fields"]["status"]["name"],
                                      "done": i["fields"]["status"]["statusCategory"]["key"] == "done"}
                           for i in found}
        except Exception as e:
            out["keys"] = {}
            out["errors"].append(f"keys: {e}")

    json.dump(out, sys.stdout, indent=1)
    print()


if __name__ == "__main__":
    main()
