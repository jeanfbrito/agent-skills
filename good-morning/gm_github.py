#!/usr/bin/env python3
"""GitHub slice of the good-morning briefing, as JSON on stdout.

Every list is sorted by last update, newest first. Each item carries `age`.
`awaiting_me` is true when a human other than me wrote after my last word.

Sections:
  review_requests  open PRs that ask ME for review (team requests are left out)
  my_prs           my open PRs in --org orgs: checks, review, threads, feedback
  new_prs          PRs opened by others in the watched repos inside the window
  issue_activity   issues in the watched repos with new comments or opened
  notifications    unread participating threads (not review_requested), each
                   with the last human comment and awaiting_me
  release_health   per watched repo: failed or running push/tag/schedule runs
                   on protected branches and tags, latest releases, open PRs
                   into release branches

  gm_github.py --since 2026-10-14T09:00:00Z --repo RocketChat/Rocket.Chat.Electron \
      --org RocketChat --branch dev --branch master --branch 'release/*'
"""
import argparse
import fnmatch
import json
import re
import sys

from gm_common import age, days_since, gh_graphql, gh_json, iso, parse_ts, short, utcnow
from datetime import timedelta

AUTHOR = "author { __typename login }"
BASE = f"number title url createdAt updatedAt isDraft repository {{ nameWithOwner }} {AUTHOR}"
DISCUSSION = f"""comments(last: 10) {{ nodes {{ {AUTHOR} createdAt url bodyText }} }}"""
REVIEWS = f"""reviews(last: 10) {{ nodes {{ {AUTHOR} createdAt url state bodyText }} }}"""


def is_bot(author):
    if not author:
        return True
    login = author["login"]
    return author.get("__typename") == "Bot" or login.endswith("[bot]") or login.endswith("-bot") \
        or login in ("codecov-commenter", "coderabbitai", "cubic-dev-ai")


def newest_first(items, key="updated"):
    return sorted(items, key=lambda i: i.get(key) or "", reverse=True)


def search(query, fields, kind="PullRequest", limit=50):
    """GitHub search, newest update first, paginated up to `limit` nodes."""
    gql = f"""query($q: String!, $n: Int!, $after: String) {{
      search(query: $q, type: ISSUE, first: $n, after: $after) {{
        pageInfo {{ hasNextPage endCursor }}
        nodes {{ ... on {kind} {{ {fields} }} }}
      }}
    }}"""
    nodes, after, truncated = [], None, False
    while len(nodes) < limit:
        variables = {"q": f"{query} sort:updated-desc", "n": min(25, limit - len(nodes))}
        if after:
            variables["after"] = after
        page = gh_graphql(gql, **variables)["search"]
        nodes += [n for n in page["nodes"] if n]  # other kinds come back as {}
        if not page["pageInfo"]["hasNextPage"]:
            break
        after = page["pageInfo"]["endCursor"]
    else:
        truncated = True
    return nodes, truncated


def human_comments(items, me):
    return sorted(
        ({"author": i["author"]["login"], "at": i["createdAt"], "url": i.get("url"),
          "state": i.get("state"), "text": short(i.get("bodyText"), 280), "_full": i.get("bodyText") or ""}
         for i in items if not is_bot(i["author"])),
        key=lambda c: c["at"])


REQUEST = re.compile(r"\?|\b(can|could|would) you\b|\bif you can\b|\bplease\b|\blet me know\b", re.I)


def asks(text, me):
    """A question or a request: more than an acknowledgement or a thank-you."""
    return bool(REQUEST.search(text or ""))


def conversation(items, me, since, is_open=True):
    """Fresh human feedback from others, and whether it waits for my reply.

    awaiting_me: the thread is open and someone else wrote last, inside the
    window. asks_me: that last comment holds a question or @-mentions me, so
    it is more than an acknowledgement."""
    comments = human_comments(items, me)
    mine = [c for c in comments if c["author"] == me]
    others = [c for c in comments if c["author"] != me]
    last_other = others[-1] if others else None
    my_last = mine[-1]["at"] if mine else None
    awaiting = bool(last_other and (not my_last or last_other["at"] > my_last))
    fresh = [c for c in others if c["at"] >= since]
    awaiting = awaiting and is_open and last_other["at"] >= since
    asked = awaiting and asks(last_other["_full"], me)
    for c in comments:
        c.pop("_full", None)
    return {"new_human_feedback": list(reversed(fresh)), "last_other": last_other,
            "my_last_comment": my_last, "awaiting_me": awaiting, "asks_me": asked}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--since", required=True, help="ISO-8601 UTC window start")
    p.add_argument("--repo", action="append", default=[])
    p.add_argument("--org", action="append", default=[])
    p.add_argument("--branch", action="append", default=[], help="protected branch glob")
    p.add_argument("--stale-days", type=int, default=7)
    a = p.parse_args()

    now = utcnow()
    since = a.since
    since_date = since[:10]
    me = gh_json(["api", "user"])["login"]
    out = {"me": me, "since": since, "generated_at": iso(now), "repos": a.repo, "orgs": a.org,
           "errors": [], "truncated": []}

    def section(name, fn):
        try:
            out[name] = fn()
        except Exception as e:  # keep the other sections when one call fails
            out[name] = []
            out["errors"].append(f"{name}: {e}")

    def review_requests():
        nodes, trunc = search("is:pr is:open archived:false user-review-requested:@me", BASE)
        if trunc:
            out["truncated"].append("review_requests")
        return [{"repo": n["repository"]["nameWithOwner"], "number": n["number"], "title": n["title"],
                 "url": n["url"], "author": n["author"]["login"] if n["author"] else None,
                 "draft": n["isDraft"], "updated": n["updatedAt"], "age": age(n["updatedAt"], now),
                 "waiting_days": round(days_since(n["updatedAt"], now), 1)} for n in nodes]

    section("review_requests", review_requests)

    def my_prs():
        orgs = " ".join(f"org:{o}" for o in a.org)
        fields = BASE + f""" reviewDecision mergeable baseRefName
          commits(last: 1) {{ nodes {{ commit {{ statusCheckRollup {{ state
            contexts(first: 50) {{ nodes {{ ... on CheckRun {{ name conclusion }}
                                          ... on StatusContext {{ context state }} }} }} }} }} }} }}
          reviewThreads(first: 50) {{ nodes {{ isResolved comments(first: 1) {{ nodes {{ {AUTHOR} }} }} }} }}
          {DISCUSSION} {REVIEWS}"""
        nodes, trunc = search(f"is:pr is:open archived:false author:@me {orgs}".strip(), fields, limit=100)
        if trunc:
            out["truncated"].append("my_prs")
        res = []
        for n in nodes:
            rollup = (n["commits"]["nodes"] or [{}])[0].get("commit", {}).get("statusCheckRollup")
            failing = []
            if rollup:
                for c in rollup["contexts"]["nodes"]:
                    name = c.get("name") or c.get("context")
                    if (c.get("conclusion") or c.get("state")) in ("FAILURE", "ERROR", "TIMED_OUT"):
                        failing.append(name)
            threads = [t for t in n["reviewThreads"]["nodes"] if not t["isResolved"]]
            human_threads = sum(1 for t in threads
                                if t["comments"]["nodes"] and not is_bot(t["comments"]["nodes"][0]["author"]))
            conv = conversation(n["comments"]["nodes"] + n["reviews"]["nodes"], me, since)
            idle = days_since(n["updatedAt"], now)
            res.append({
                "repo": n["repository"]["nameWithOwner"], "number": n["number"], "title": n["title"],
                "url": n["url"], "base": n["baseRefName"], "draft": n["isDraft"],
                "checks": rollup["state"] if rollup else None, "failing_checks": sorted(set(failing)),
                "review": n["reviewDecision"], "mergeable": n["mergeable"],
                "unresolved_threads": len(threads), "unresolved_human_threads": human_threads,
                **conv, "updated": n["updatedAt"], "age": age(n["updatedAt"], now),
                "stale": idle is not None and idle >= a.stale_days,
            })
        return res

    section("my_prs", my_prs)

    def new_prs():
        res = []
        for repo in a.repo:
            nodes, _ = search(f"repo:{repo} is:pr created:>={since_date} -author:@me", BASE + " state")
            for n in nodes:
                if n["createdAt"] < since:
                    continue
                res.append({"repo": repo, "number": n["number"], "title": n["title"], "url": n["url"],
                            "author": n["author"]["login"] if n["author"] else None,
                            "bot": is_bot(n["author"]), "draft": n["isDraft"], "state": n["state"],
                            "updated": n["updatedAt"], "age": age(n["createdAt"], now)})
        return res

    section("new_prs", new_prs)

    def issue_activity():
        fields = f"number title url createdAt updatedAt state repository {{ nameWithOwner }} {AUTHOR} {DISCUSSION}"
        res = []
        for repo in a.repo:
            nodes, _ = search(f"repo:{repo} is:issue updated:>={since_date}", fields, kind="Issue")
            for n in nodes:
                conv = conversation(n["comments"]["nodes"], me, since, n["state"] == "OPEN")
                opened = n["createdAt"] >= since and not is_bot(n["author"])
                if not conv["new_human_feedback"] and not opened:
                    continue
                latest = conv["new_human_feedback"][0]["at"] if conv["new_human_feedback"] else n["createdAt"]
                res.append({"repo": repo, "number": n["number"], "title": n["title"], "url": n["url"],
                            "state": n["state"], "opened_in_window": opened,
                            "author": n["author"]["login"] if n["author"] else None,
                            "new_comments": conv["new_human_feedback"], "awaiting_me": conv["awaiting_me"],
                            "asks_me": conv["asks_me"],
                            "updated": latest, "age": age(latest, now)})
        return res

    section("issue_activity", issue_activity)

    def notifications():
        threads = []
        for n in gh_json(["api", f"notifications?participating=true&since={since}&per_page=100"]):
            if n["reason"] == "review_requested":
                continue
            api_url = n["subject"].get("url") or ""
            m = re.search(r"/(pulls|issues)/(\d+)$", api_url)
            threads.append({"reason": n["reason"], "type": n["subject"]["type"],
                            "repo": n["repository"]["full_name"], "title": n["subject"]["title"],
                            "number": int(m.group(2)) if m else None,
                            "url": (api_url.replace("api.github.com/repos", "github.com")
                                    .replace("/pulls/", "/pull/")) if api_url else None,
                            "updated": n["updated_at"], "age": age(n["updated_at"], now)})
        # one GraphQL call for the last comments of every thread
        parts = []
        for i, t in enumerate(threads):
            if t["number"] is None or t["type"] not in ("PullRequest", "Issue"):
                continue
            owner, name = t["repo"].split("/")
            extra = REVIEWS if t["type"] == "PullRequest" else ""
            parts.append(f't{i}: repository(owner: "{owner}", name: "{name}") {{ '
                         f'issueOrPullRequest(number: {t["number"]}) {{ '
                         f'... on {t["type"]} {{ state {DISCUSSION} {extra} }} }} }}')
        if parts:
            data = gh_graphql("query { " + " ".join(parts) + " }")
            for key, repo in data.items():
                node = (repo or {}).get("issueOrPullRequest") or {}
                t = threads[int(key[1:])]
                t["state"] = node.get("state")
                items = node.get("comments", {}).get("nodes", []) + node.get("reviews", {}).get("nodes", [])
                conv = conversation(items, me, since, node.get("state") == "OPEN")
                t.update({"last_other": conv["last_other"], "awaiting_me": conv["awaiting_me"],
                          "asks_me": conv["asks_me"], "my_last_comment": conv["my_last_comment"]})
        return threads

    section("notifications", notifications)

    def release_health():
        res = []
        for repo in a.repo:
            default = gh_json(["repo", "view", repo, "--json", "defaultBranchRef"])["defaultBranchRef"]["name"]
            tags = {r["tagName"]: r for r in gh_json(
                ["release", "list", "-R", repo, "--limit", "5",
                 "--json", "tagName,isDraft,isPrerelease,isLatest,publishedAt,createdAt"])}
            runs = []  # pull_request runs would crowd out branch and tag runs
            for event in ("push", "release", "schedule", "workflow_dispatch", "dynamic"):
                runs += gh_json(["run", "list", "-R", repo, "--event", event, "--limit", "30", "--json",
                                 "workflowName,headBranch,event,status,conclusion,createdAt,url,displayTitle"])
            latest = {}
            for r in runs:
                if r["event"] == "pull_request":
                    continue
                branch = r["headBranch"] or ""
                is_tag = bool(re.fullmatch(r"v?\d+\.\d+\.\d+(-[\w.]+)?", branch))
                if not (is_tag or any(fnmatch.fnmatch(branch, g) for g in a.branch)):
                    continue
                key = (r["workflowName"], "tag" if is_tag else branch)
                if key not in latest or r["createdAt"] > latest[key]["createdAt"]:
                    latest[key] = {**r, "is_tag": is_tag}
            problems = [
                {"workflow": r["workflowName"], "ref": r["headBranch"], "is_tag": r["is_tag"],
                 "status": r["status"], "conclusion": r["conclusion"], "url": r["url"],
                 "at": r["createdAt"], "age": age(r["createdAt"], now)}
                for r in latest.values()
                if r["status"] != "completed" or r["conclusion"] not in ("success", "skipped", "neutral")]
            release_bases = [b for b in a.branch if b != default]
            into_release = []
            for pr in gh_json(["pr", "list", "-R", repo, "--state", "open", "--limit", "50",
                               "--json", "number,title,url,author,baseRefName,updatedAt,isDraft"]):
                if any(fnmatch.fnmatch(pr["baseRefName"], g) for g in release_bases):
                    into_release.append({"number": pr["number"], "title": pr["title"], "url": pr["url"],
                                         "author": pr["author"]["login"], "base": pr["baseRefName"],
                                         "bot": pr["author"].get("is_bot", False)
                                         or pr["author"]["login"].startswith("app/"),
                                         "draft": pr["isDraft"], "updated": pr["updatedAt"],
                                         "age": age(pr["updatedAt"], now)})
            res.append({
                "repo": repo, "default_branch": default,
                "releases": [{"tag": t, "draft": r["isDraft"], "prerelease": r["isPrerelease"],
                              "latest": r["isLatest"], "published": r["publishedAt"],
                              "age": age(r["publishedAt"] or r["createdAt"], now)} for t, r in tags.items()],
                "drafts": [t for t, r in tags.items() if r["isDraft"]],
                "run_problems": newest_first(problems, "at"),
                "runs_checked": len(latest),
                "open_prs_into_release_branches": newest_first(into_release),
            })
        return res

    section("release_health", release_health)

    for name in ("review_requests", "my_prs", "new_prs", "issue_activity", "notifications"):
        out[name] = newest_first(out[name])
    json.dump(out, sys.stdout, indent=1)
    print()


if __name__ == "__main__":
    main()
