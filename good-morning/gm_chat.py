#!/usr/bin/env python3
"""Rocket.Chat slice of the good-morning briefing, as JSON on stdout.

Uses `rocket-cli attention` (read-only: it never marks anything as read).

Sections:
  mentions, dms, threads   items inside the window, each with `answered`
                           (I wrote in the conversation after it) and
                           `others_after_my_last` (replies since my last word)
  channels                 channel unreads inside the window, grouped by room
  older_unread             count of unread items older than the window, per
                           section (they are dropped from the lists)

  gm_chat.py --since 2026-10-14T09:00:00Z [--me <username>] [--profile work]

Without --me, the username comes from the rocket-cli profile (GET /api/v1/me).
"""
import argparse
import json
import math
import os
import subprocess
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from gm_common import age, iso, parse_ts, short, utcnow


def cli(args, profile):
    cmd = ["rocket-cli", *(["--profile", profile] if profile else []), *args, "--json"]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if out.returncode != 0:
        raise RuntimeError(f"rocket-cli {args[0]}: {out.stderr.strip()[:300]}")
    return json.loads(out.stdout)


def my_username(profile):
    """Ask the server who the rocket-cli profile belongs to."""
    path = os.path.expanduser("~/.config/rocket-cli/profiles.json")
    with open(path) as f:
        cfg = json.load(f)
    prof = cfg["profiles"][profile or os.environ.get("ROCKET_CLI_PROFILE") or cfg["defaultProfile"]]
    req = urllib.request.Request(prof["url"].rstrip("/") + "/api/v1/me",
                                 headers={"X-Auth-Token": prof["token"], "X-User-Id": prof["userId"],
                                          "User-Agent": "good-morning/1.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["username"]


def item_time(it):
    m = it.get("message", it)
    return m.get("lastReplyAt") or m.get("time") or m.get("ts")


def flatten(it, now):
    m = it.get("message", it)
    room = it.get("room", {})
    t = item_time(it)
    return {"id": m.get("id"), "room": room.get("name"), "room_type": room.get("type"),
            "author": m.get("author"), "text": short(m.get("text"), 300), "time": m.get("time"),
            "updated": t, "age": age(t, now), "link": m.get("link"),
            "thread_id": m.get("threadId"), "reply_count": m.get("replyCount"),
            "hidden_mentioned": it.get("hiddenMentioned", False)}


def answered(item, me, profile):
    """(answered, others_after_my_last): did I write after this message, and
    how many messages from others came after my last one."""
    try:
        ctx = cli(["context", item["id"], "--before", "0", "--after", "30"], profile)
    except Exception:
        return None, None
    t = parse_ts(item["time"])
    later = [m for m in ctx.get("messages", []) if parse_ts(m.get("time")) and parse_ts(m["time"]) > t]
    mine = [i for i, m in enumerate(later) if m.get("author") == me]
    if not mine:
        return False, len(later)
    return True, sum(1 for m in later[mine[-1] + 1:] if m.get("author") != me)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--since", required=True)
    p.add_argument("--me", help="my chat username (default: from the rocket-cli profile)")
    p.add_argument("--profile")
    a = p.parse_args()

    now = utcnow()
    since = parse_ts(a.since)
    if not a.me:
        a.me = my_username(a.profile)
    days = max(1, math.ceil((now - since).total_seconds() / 86400))
    raw = cli(["attention", "--since-days", str(days), "--limit", "100"], a.profile)

    out = {"since": a.since, "me": a.me, "generated_at": iso(now), "searched_since": raw.get("searchedSince"),
           "refreshing": raw.get("refreshing"), "errors": [], "older_unread": {}}
    sections = {"mentions": "mentions", "dms": "directUnreads", "threads": "threadUnreads",
                "channels": "channelUnreads"}
    for name, key in sections.items():
        items = [flatten(i, now) for i in raw.get(key, [])]
        fresh = [i for i in items if parse_ts(i["updated"]) and parse_ts(i["updated"]) >= since]
        out["older_unread"][name] = len(items) - len(fresh)
        out[name] = sorted(fresh, key=lambda i: i["updated"], reverse=True)

    # a mention, DM or thread reply that I already answered is FYI, not Unblock
    targets = [i for n in ("mentions", "dms", "threads") for i in out[n] if i["id"]]
    with ThreadPoolExecutor(max_workers=6) as pool:
        for item, (done, after) in zip(targets, pool.map(lambda i: answered(i, a.me, a.profile), targets)):
            item["answered"] = done
            item["others_after_my_last"] = after

    rooms = {}
    for i in out["channels"]:
        r = rooms.setdefault(i["room"], {"room": i["room"], "count": 0, "latest": i["updated"],
                                         "age": i["age"], "authors": set(), "samples": []})
        r["count"] += 1
        r["authors"].add(i["author"])
        if len(r["samples"]) < 3:
            r["samples"].append({k: i[k] for k in ("author", "text", "link", "age")})
    out["channel_rooms"] = sorted(({**r, "authors": sorted(r["authors"])} for r in rooms.values()),
                                  key=lambda r: r["latest"], reverse=True)
    del out["channels"]
    json.dump(out, sys.stdout, indent=1)
    print()


if __name__ == "__main__":
    main()
