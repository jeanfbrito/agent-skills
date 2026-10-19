#!/usr/bin/env python3
"""Snapshot the open pull requests of a GitHub repo as JSON, with merge blockers.

Usage:
  pr-snapshot.py [--repo owner/name] [--since YYYY-MM-DD] [--me LOGIN] [--all] [--save]

--since keeps PRs created on or after the date (default: 30 days ago).
--all ignores --since. --me defaults to the gh-authenticated login.
Prints one JSON object: {"repo", "me", "since", "prs": [...]}.
Each PR carries "mine" and a "blockers" list computed from GitHub state only.
When run inside a clone of the repo, each PR also gets "local_merge": a trial
merge against its base (conflict files, commits behind).

State: local-state.json next to this script (gitignored) keeps, per repo, the
head SHA of every PR seen on the last --save run. Each PR gets "status":
"new" (never seen), "updated" (head moved), or "unchanged". --save writes the
current SHAs and the run date after printing.
"""
import argparse
import os
import datetime as dt
import json
import subprocess
import sys

QUERY = """
query($owner:String!, $name:String!, $cursor:String) {
  repository(owner:$owner, name:$name) {
    defaultBranchRef { name }
    pullRequests(states:OPEN, first:20, after:$cursor, orderBy:{field:CREATED_AT, direction:DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes {
        number title url createdAt updatedAt isDraft
        author { login }
        baseRefName headRefName
        mergeable mergeStateStatus reviewDecision
        additions deletions changedFiles
        labels(first:10) { nodes { name } }
        reviewRequests(first:10) { nodes { requestedReviewer { ... on User { login } ... on Team { slug } } } }
        reviews(last:30) { nodes { author { login } state submittedAt } }
        reviewThreads(first:60) { nodes { isResolved isOutdated comments(first:1) { nodes { author { login } } } } }
        comments(last:5) { nodes { author { login } createdAt } }
        commits(last:1) { nodes { commit { oid committedDate statusCheckRollup {
          state
          contexts(first:60) { nodes {
            ... on CheckRun { name conclusion status }
            ... on StatusContext { context state }
          } }
        } } } }
      }
    }
  }
}
"""

BOTS = ("coderabbitai", "github-actions", "dependabot", "lingohub", "copilot")


def gh(args):
    out = subprocess.run(["gh", *args], capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"gh {' '.join(args[:2])} failed: {out.stderr.strip()}")
    return out.stdout


def fetch(owner, name):
    prs, cursor, default = [], None, None
    while True:
        args = ["api", "graphql", "-f", f"query={QUERY}", "-F", f"owner={owner}", "-F", f"name={name}"]
        if cursor:
            args += ["-F", f"cursor={cursor}"]
        repo = json.loads(gh(args))["data"]["repository"]
        default = repo["defaultBranchRef"]["name"]
        page = repo["pullRequests"]
        prs += page["nodes"]
        if not page["pageInfo"]["hasNextPage"]:
            return default, prs
        cursor = page["pageInfo"]["endCursor"]


def is_bot(login):
    return any(b in (login or "").lower() for b in BOTS)


def checks(rollup):
    if not rollup:
        return {"state": "NONE", "failing": [], "pending": []}
    failing, pending = [], []
    for c in rollup["contexts"]["nodes"]:
        name = c.get("name") or c.get("context")
        if not name:
            continue
        if "status" in c:
            if c["status"] != "COMPLETED":
                pending.append(name)
            elif c["conclusion"] in ("FAILURE", "TIMED_OUT", "CANCELLED", "ACTION_REQUIRED", "STARTUP_FAILURE"):
                failing.append(name)
        elif c.get("state") in ("FAILURE", "ERROR"):
            failing.append(name)
        elif c.get("state") in ("PENDING", "EXPECTED"):
            pending.append(name)
    return {"state": rollup["state"], "failing": sorted(set(failing)), "pending": sorted(set(pending))}


def shape(pr, me, default, local=None):
    author = (pr["author"] or {}).get("login", "ghost")
    head = pr["commits"]["nodes"][0]["commit"] if pr["commits"]["nodes"] else {}
    ck = checks(head.get("statusCheckRollup"))
    threads = [t for t in pr["reviewThreads"]["nodes"] if not t["isResolved"]]
    def thread_author(t):
        n = t["comments"]["nodes"]
        return n[0]["author"]["login"] if n and n[0]["author"] else "ghost"
    human_open = [t for t in threads if not is_bot(thread_author(t))]
    bot_open = [t for t in threads if is_bot(thread_author(t))]
    latest = {}
    for r in pr["reviews"]["nodes"]:
        login = (r["author"] or {}).get("login", "ghost")
        if r["state"] in ("APPROVED", "CHANGES_REQUESTED", "DISMISSED"):
            latest[login] = r["state"]
    approvals = sorted(l for l, s in latest.items() if s == "APPROVED" and l != author)
    changes = sorted(l for l, s in latest.items() if s == "CHANGES_REQUESTED")
    age_days = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(pr["createdAt"].replace("Z", "+00:00"))).days
    last_push = head.get("committedDate")

    blockers = []
    if pr["isDraft"]:
        blockers.append("draft")
    if pr["baseRefName"] != default:
        blockers.append(f"base is {pr['baseRefName'] or '(deleted)'}, not {default}")
    conflict = pr["mergeable"] == "CONFLICTING" or bool(local and local["conflict"])
    if conflict:
        files = (local or {}).get("conflict_files") or []
        blockers.append("merge conflicts" + (f" in {', '.join(files[:6])}" if files else ""))
    elif pr["mergeStateStatus"] == "BEHIND":
        blockers.append(f"behind {pr['baseRefName']}")
    if ck["failing"]:
        blockers.append(f"failing checks: {', '.join(ck['failing'])}")
    if ck["pending"]:
        blockers.append(f"pending checks: {', '.join(ck['pending'])}")
    if ck["state"] == "NONE":
        blockers.append("no checks ran")
    if changes:
        blockers.append(f"changes requested by {', '.join(changes)}")
    if human_open:
        blockers.append(f"{len(human_open)} unresolved human review thread(s)")
    if bot_open:
        blockers.append(f"{len(bot_open)} unresolved bot review thread(s)")
    if not approvals and pr["reviewDecision"] != "APPROVED":
        blockers.append("no approving review")

    return {
        "number": pr["number"], "title": pr["title"], "url": pr["url"], "author": author,
        "mine": author == me, "bot": is_bot(author) or author.startswith("app/"),
        "head_sha": head.get("oid"), "created": pr["createdAt"][:10], "updated": pr["updatedAt"][:10], "last_push": (last_push or "")[:10],
        "age_days": age_days, "draft": pr["isDraft"], "base": pr["baseRefName"], "head": pr["headRefName"],
        "mergeable": pr["mergeable"], "merge_state": pr["mergeStateStatus"], "local_merge": local, "review_decision": pr["reviewDecision"],
        "size": {"additions": pr["additions"], "deletions": pr["deletions"], "files": pr["changedFiles"]},
        "labels": [l["name"] for l in pr["labels"]["nodes"]],
        "review_requests": [r["requestedReviewer"].get("login") or r["requestedReviewer"].get("slug")
                            for r in pr["reviewRequests"]["nodes"] if r["requestedReviewer"]],
        "approvals": approvals, "checks": ck,
        "unresolved_threads": {"human": len(human_open), "bot": len(bot_open)},
        "blockers": blockers,
    }


def git(args):
    return subprocess.run(["git", *args], capture_output=True, text=True)


def local_merge(repo, prs):
    """Test each PR against its base with `git merge-tree` in the current clone.

    GitHub often leaves `mergeable` as UNKNOWN for long-lived repos, even after a
    REST read. A local trial merge answers the question without touching the
    working tree. Returns {} when the current directory is not a clone of `repo`.
    """
    remote = git(["remote", "get-url", "origin"]).stdout.strip()
    if repo.lower() not in remote.lower().removesuffix(".git"):
        return {}
    bases = sorted({x["baseRefName"] for x in prs if x["baseRefName"]})
    specs = [f"+refs/heads/{b}:refs/pr-triage/base/{b}" for b in bases]
    specs += [f"+pull/{x['number']}/head:refs/pr-triage/{x['number']}" for x in prs]
    if git(["fetch", "-q", "--no-tags", "origin", *specs]).returncode != 0:
        return {}
    result = {}
    for x in prs:
        base, head = f"refs/pr-triage/base/{x['baseRefName']}", f"refs/pr-triage/{x['number']}"
        mt = git(["merge-tree", "--write-tree", "--name-only", "--no-messages", base, head])
        if mt.returncode not in (0, 1):
            continue
        behind = git(["rev-list", "--count", f"{head}..{base}"]).stdout.strip()
        result[x["number"]] = {
            "conflict": mt.returncode == 1,
            "conflict_files": mt.stdout.split("\n")[1:-1] if mt.returncode == 1 else [],
            "behind_base": int(behind or 0),
        }
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo")
    p.add_argument("--since")
    p.add_argument("--me")
    p.add_argument("--all", action="store_true")
    p.add_argument("--save", action="store_true")
    a = p.parse_args()
    repo = a.repo or gh(["repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"]).strip()
    owner, name = repo.split("/")
    me = a.me or gh(["api", "user", "-q", ".login"]).strip()
    since = None if a.all else (a.since or (dt.date.today() - dt.timedelta(days=30)).isoformat())

    default, prs = fetch(owner, name)
    if since:
        prs = [x for x in prs if x["createdAt"][:10] >= since]
    local = local_merge(repo, prs)
    out = [shape(x, me, default, local.get(x["number"])) for x in prs]

    state_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "local-state.json")
    state = json.load(open(state_path)) if os.path.exists(state_path) else {}
    seen = state.get(repo, {}).get("heads", {})
    for x in out:
        prev = seen.get(str(x["number"]))
        x["status"] = "new" if prev is None else ("unchanged" if prev == x["head_sha"] else "updated")

    last_run = state.get(repo, {}).get("last_run")
    json.dump({"repo": repo, "me": me, "default_branch": default, "since": since,
               "last_run": last_run, "prs": out}, sys.stdout, indent=1)
    print()
    if a.save:
        heads = dict(seen)
        heads.update({str(x["number"]): x["head_sha"] for x in out})
        state[repo] = {"last_run": dt.date.today().isoformat(), "heads": heads}
        with open(state_path, "w") as f:
            json.dump(state, f, indent=1)


if __name__ == "__main__":
    main()
