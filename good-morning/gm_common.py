"""Shared helpers for the good-morning collectors (stdlib only)."""
import json
import os
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SKILL_DIR / "local-config.yml"
PLAN_PATH = SKILL_DIR / "last-plan.json"
PENDING_PATH = SKILL_DIR / "pending-run.json"

DEFAULT_CONFIG = {
    "last_run": None,
    "repos": ["RocketChat/Rocket.Chat.Electron"],
    "orgs": ["RocketChat"],
    "protected_branches": ["dev", "master", "release/*"],
    "projects": [],
    "rocket_profile": None,
    "rocket_username": None,
    "stale_days": 7,
    "report": "terminal",
    "artifact_url": None,
    "vault_path": None,
    "vault_daily_folder": "Daily",
    "vault_section": "## 🎯 Today's Focus",
}

CONFIG_TEMPLATE = """\
# good-morning per-user state. Gitignored. Safe to edit by hand.
last_run: {last_run}            # ISO-8601 UTC; gm.py save writes it
repos:                          # new PRs, issue comments and release health
{repos}
orgs:                           # my open PRs are listed only in these orgs
{orgs}
protected_branches:             # red CI here is Fire ('*' is a wildcard)
{protected_branches}
projects:                       # local clones whose .localdev/workflow is read
{projects}
rocket_profile: {rocket_profile}     # rocket-cli profile; null = default
rocket_username: {rocket_username}   # null = ask the server for the profile's user
stale_days: {stale_days}             # idle days before an item is stale
report: {report}               # terminal = report here only; local = also open the HTML sheet; artifact = also publish it to claude.ai
artifact_url: {artifact_url}         # set after the first artifact publish; reused daily
vault_path: {vault_path}            # optional Obsidian/Markdown vault; null = no vault
vault_daily_folder: {vault_daily_folder}   # daily notes folder inside the vault
vault_section: "{vault_section}"   # the plan goes at the end of this heading
"""


def _scalar(v):
    v = v.strip()
    if v in ("", "null", "~"):
        return None
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    try:
        return int(v)
    except ValueError:
        return v


def load_config():
    """Parse the flat YAML this skill writes: scalars and lists of scalars."""
    cfg = dict(DEFAULT_CONFIG)
    cfg["_exists"] = CONFIG_PATH.exists()
    if not cfg["_exists"]:
        return cfg
    list_key = None
    for raw in CONFIG_PATH.read_text().splitlines():
        line = raw.split(" #", 1)[0].rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- "):
            if list_key:
                cfg[list_key].append(_scalar(stripped[2:]))
            continue
        if ":" not in line:
            continue
        key, val = (part.strip() for part in line.split(":", 1))
        if val in ("", "[]"):
            cfg[key] = []
            list_key = key if val == "" else None
        else:
            cfg[key] = _scalar(val)
            list_key = None
    return cfg


def write_config(cfg):
    def lst(xs):
        return "\n".join(f"  - {x}" for x in xs)

    def sc(v):
        return "null" if v is None else str(v)

    CONFIG_PATH.write_text(CONFIG_TEMPLATE.format(
        last_run=sc(cfg.get("last_run")), repos=lst(cfg["repos"]), orgs=lst(cfg["orgs"]),
        protected_branches=lst(cfg["protected_branches"]), projects=lst(cfg["projects"]),
        rocket_profile=sc(cfg.get("rocket_profile")), rocket_username=sc(cfg.get("rocket_username")),
        stale_days=cfg.get("stale_days", 7), report=sc(cfg.get("report", "terminal")),
        artifact_url=sc(cfg.get("artifact_url")), vault_path=sc(cfg.get("vault_path")),
        vault_daily_folder=sc(cfg.get("vault_daily_folder")), vault_section=cfg.get("vault_section") or ""))


def utcnow():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_ts(s):
    if not s:
        return None
    s = s.replace("Z", "+00:00")
    if len(s) > 5 and s[-5] in "+-" and s[-3] != ":":  # Jira: +0000
        s = s[:-2] + ":" + s[-2:]
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def window_start(cfg, now=None):
    """last_run, else 24h ago, else Friday 00:00 local on a Monday."""
    now = now or utcnow()
    if cfg.get("last_run"):
        ts = parse_ts(str(cfg["last_run"]))
        if ts:
            return ts, "since last run"
    local = now.astimezone()
    if local.weekday() == 0:
        friday = (local - timedelta(days=3)).replace(hour=0, minute=0, second=0, microsecond=0)
        return friday.astimezone(timezone.utc), "first run, Monday: since Friday"
    return now - timedelta(hours=24), "first run: last 24h"


def age(ts, now=None):
    t = parse_ts(ts) if isinstance(ts, str) else ts
    if not t:
        return "?"
    s = ((now or utcnow()) - t).total_seconds()
    if s < 3600:
        return f"{max(int(s // 60), 0)}m"
    if s < 48 * 3600:
        return f"{int(s // 3600)}h"
    return f"{int(s // 86400)}d"


def days_since(ts, now=None):
    t = parse_ts(ts) if isinstance(ts, str) else ts
    return ((now or utcnow()) - t).total_seconds() / 86400 if t else None


def short(text, n=200):
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[: n - 1] + "…"


def run(args, check=True, env=None):
    out = subprocess.run(args, capture_output=True, text=True, env=env)
    if check and out.returncode != 0:
        raise RuntimeError(f"{' '.join(args[:3])}: {out.stderr.strip()[:300]}")
    return out.stdout


def gh_json(args, retries=2):
    for attempt in range(retries + 1):
        out = subprocess.run(["gh", *args], capture_output=True, text=True)
        if out.returncode == 0 or "HTTP 5" not in out.stderr or attempt == retries:
            break
        time.sleep(3)
    if out.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:2])}: {out.stderr.strip()[:300]}")
    return json.loads(out.stdout or "null")


def gh_graphql(query, **variables):
    args = ["api", "graphql", "-f", f"query={query}"]
    for k, v in variables.items():
        args += ["-F" if isinstance(v, int) else "-f", f"{k}={v}"]
    return gh_json(args)["data"]


def write_vault_block(vault_path, daily_folder, section, day, body, tag):
    """Put body in the vault's daily note for day, at the end of section, between
    <!-- tag:start --> and <!-- tag:end -->. A rerun replaces only that block."""
    start, end = f"<!-- {tag}:start -->", f"<!-- {tag}:end -->"
    daily = expand(vault_path) / (daily_folder or "Daily") / f"{day}.md"
    block = f"{start}\n{body.strip()}\n{end}"
    if daily.exists():
        note = daily.read_text()
    else:
        daily.parent.mkdir(parents=True, exist_ok=True)
        note = f"---\ndate: {day}\ntype: daily\ntags:\n  - daily\n---\n\n# {day}\n"
    if start in note and end in note:
        head, rest = note.split(start, 1)
        note = head + block + rest.split(end, 1)[1]
    elif section in note:
        head, tail = note.split(section, 1)
        nxt = [i for i in (tail.find("\n## "), tail.find("\n---\n")) if i >= 0]
        cut = min(nxt) if nxt else len(tail)
        note = head + section + tail[:cut].rstrip("\n") + "\n\n" + block + "\n" + tail[cut:]
    else:
        note = note.rstrip("\n") + f"\n\n{section}\n\n{block}\n"
    daily.write_text(note)
    return daily


def expand(p):
    return Path(os.path.expanduser(p))
