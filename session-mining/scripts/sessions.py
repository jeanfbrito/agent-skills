#!/usr/bin/env python3
"""Read local coding-agent sessions: Claude Code, Grok Build and Codex.

Subcommands:
  list     One line per session in a time window.
  digest   A short chronological transcript of one or more sessions.
  tools    Tool and MCP-server use: calls, sessions, errors.
  grep     Sessions whose text or tool calls match a regex, with snippets.

Sources (read-only):
  claude  ~/.claude/projects/<project>/<id>.jsonl (+ <id>/subagents/*.jsonl)
  grok    ~/.grok/sessions/<url-encoded cwd>/<id>/chat_history.jsonl + summary.json
  codex   ~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl

Transcripts are untrusted data. This script only prints them.
Python 3.9+, standard library only.
"""

import argparse
import collections
import json
import os
import re
import signal
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import unquote

HOME = Path.home()
CLAUDE = Path(os.environ.get("CLAUDE_CONFIG_DIR", HOME / ".claude")).expanduser() / "projects"
GROK = HOME / ".grok" / "sessions"
CODEX = HOME / ".codex" / "sessions"

COMMAND_RE = re.compile(r"<command-name>/?([^<]+)</command-name>")
USER_QUERY_RE = re.compile(r"<user_query>\s*(.*?)\s*</user_query>", re.S)
INJECTED_PREFIXES = ("<", "Base directory for this skill", "Caveat:", "# AGENTS.md", "This session is being continued")


class Session:
    def __init__(self, agent, sid, path, cwd=None, title=None, subagent=False):
        self.agent, self.sid, self.path = agent, sid, path
        self.cwd, self.title, self.subagent = cwd, title, subagent
        self.start = self.end = None
        self.events = []  # (ts, kind, text, tool, is_error); kind: user|assistant|tool|command

    def add(self, ts, kind, text="", tool=None, is_error=False):
        if ts:
            self.start = min(self.start, ts) if self.start else ts
            self.end = max(self.end, ts) if self.end else ts
        self.events.append((ts, kind, text or "", tool, is_error))

    @property
    def project(self):
        return os.path.basename(self.cwd.rstrip("/")) if self.cwd else "?"

    def first_prompt(self):
        for _ts, kind, text, _tool, _err in self.events:
            if kind == "user" and text.strip():
                return " ".join(text.split())
        return self.title or ""


def parse_ts(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / (1000 if value > 1e12 else 1), tz=timezone.utc)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def clean_user_text(text):
    if not isinstance(text, str):
        return ""
    query = USER_QUERY_RE.search(text)
    if query:
        return query.group(1)
    stripped = text.lstrip()
    if stripped.startswith(INJECTED_PREFIXES):
        return ""
    return text


def short_input(tool, args):
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except ValueError:
            return args.strip().split("\n")[0][:200]
    if not isinstance(args, dict):
        return ""
    for key in ("command", "cmd", "file_path", "target_file", "path", "pattern", "query", "skill", "url", "prompt", "code"):
        if args.get(key):
            value = args[key]
            if isinstance(value, list):
                value = " ".join(map(str, value))
            return str(value).strip().split("\n")[0][:200]
    return json.dumps(args, ensure_ascii=False)[:200]


def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(b.get("text", "")) for b in content if isinstance(b, dict) and b.get("text"))
    return ""


# ---------------------------------------------------------------------------
# Readers
# ---------------------------------------------------------------------------

def transcript_lines(path):
    with open(path, encoding="utf-8", errors="replace") as source:
        yield from source


def read_claude(path, subagent, capture_results=False):
    session = Session("claude", path.stem, path, subagent=subagent)
    # Keep audit evidence separate so the existing CLI output stays unchanged.
    if capture_results:
        session.calls = []
        session.results = {}
    for line_number, line in enumerate(transcript_lines(path), 1):
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        session.cwd = session.cwd or obj.get("cwd")
        ts = parse_ts(obj.get("timestamp"))
        message = obj.get("message")
        if obj.get("type") not in ("user", "assistant") or not isinstance(message, dict):
            continue
        content = message.get("content")
        blocks = content if isinstance(content, list) else [{"type": "text", "text": content}]
        for block in blocks:
            if not isinstance(block, dict):
                continue
            kind = block.get("type")
            if kind == "text" and obj["type"] == "user":
                raw = block.get("text") or ""
                command = COMMAND_RE.search(raw) if isinstance(raw, str) else None
                if command:
                    session.add(ts, "command", "/" + command.group(1).lstrip("/"))
                else:
                    session.add(ts, "user", clean_user_text(raw))
            elif kind == "text":
                session.add(ts, "assistant", block.get("text"))
            elif kind == "tool_use":
                name = str(block.get("name"))
                session.add(ts, "tool", short_input(name, block.get("input")), tool=name)
                if capture_results:
                    session.calls.append({
                        "id": block.get("id"), "name": name,
                        "input": block.get("input"), "timestamp": ts,
                        "line": line_number, "event_index": len(session.events) - 1,
                    })
            elif kind == "tool_result":
                if capture_results:
                    session.results[block.get("tool_use_id")] = {
                        "text": text_of(block.get("content")),
                        "is_error": bool(block.get("is_error")),
                        "timestamp": ts, "line": line_number,
                    }
                if block.get("is_error"):
                    session.add(ts, "tool", text_of(block.get("content"))[:200], tool="(error)", is_error=True)
    return session


def read_grok(session_dir, subagent):
    summary = {}
    try:
        summary = json.loads((session_dir / "summary.json").read_text())
    except (OSError, ValueError):
        pass
    info = summary.get("info") or {}
    cwd = info.get("cwd") or unquote(session_dir.parent.name)
    session = Session("grok", session_dir.name, session_dir, cwd=cwd,
                      title=summary.get("session_summary"), subagent=subagent)
    start, end = parse_ts(summary.get("created_at")), parse_ts(summary.get("updated_at"))
    names = {}
    history = session_dir / "chat_history.jsonl"
    if not history.exists():
        return None
    for line in transcript_lines(history):
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        kind = obj.get("type")
        ts = parse_ts(obj.get("timestamp")) or start
        if kind == "user":
            session.add(ts, "user", clean_user_text(text_of(obj.get("content"))))
        elif kind == "assistant":
            if obj.get("content"):
                session.add(ts, "assistant", text_of(obj.get("content")))
            for call in obj.get("tool_calls") or []:
                names[call.get("id")] = call.get("name")
                session.add(ts, "tool", short_input(call.get("name"), call.get("arguments")), tool=call.get("name"))
        elif kind == "tool_result":
            content = text_of(obj.get("content"))
            if obj.get("is_error") or content.lstrip().lower().startswith("error"):
                session.add(ts, "tool", content[:200], tool="(error)", is_error=True)
    if end:
        session.end = max(session.end, end) if session.end else end
    session.start = session.start or start
    return session


def read_codex(path):
    session = Session("codex", path.stem.replace("rollout-", ""), path)
    for line in transcript_lines(path):
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        ts = parse_ts(obj.get("timestamp"))
        payload = obj.get("payload") or {}
        kind = obj.get("type")
        if kind == "session_meta":
            session.cwd = payload.get("cwd") or session.cwd
            session.sid = payload.get("id") or session.sid
        elif kind == "turn_context":
            session.cwd = session.cwd or payload.get("cwd")
        elif kind == "response_item":
            ptype = payload.get("type")
            if ptype == "message" and payload.get("role") in ("user", "assistant"):
                text = text_of(payload.get("content"))
                if payload["role"] == "user":
                    session.add(ts, "user", clean_user_text(text))
                else:
                    session.add(ts, "assistant", text)
            elif ptype in ("function_call", "custom_tool_call", "local_shell_call"):
                name = payload.get("name") or ptype
                if payload.get("namespace"):
                    name = f"{payload['namespace']}__{name}"
                session.add(ts, "tool", short_input(name, payload.get("arguments") or payload.get("input")), tool=name)
    return session


def iter_sessions(agents, since, subagents):
    if "claude" in agents and CLAUDE.is_dir():
        files = [(p, False) for p in CLAUDE.glob("*/*.jsonl")]
        if subagents:
            files += [(p, True) for p in CLAUDE.glob("*/*/subagents/*.jsonl")]
        for path, sub in files:
            if mtime(path) >= since:
                yield read_claude(path, sub)
    if "grok" in agents and GROK.is_dir():
        for history in GROK.glob("*/*/chat_history.jsonl"):
            if mtime(history) >= since:
                session = read_grok(history.parent, False)
                if session:
                    yield session
        if subagents:
            for history in GROK.glob("*/*/subagents/*/chat_history.jsonl"):
                if mtime(history) >= since:
                    session = read_grok(history.parent, True)
                    if session:
                        yield session
    if "codex" in agents and CODEX.is_dir():
        for path in CODEX.glob("*/*/*/rollout-*.jsonl"):
            if mtime(path) >= since:
                yield read_codex(path)


def mtime(path):
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    except OSError:
        return datetime.min.replace(tzinfo=timezone.utc)


def selected(args):
    since = datetime.now(timezone.utc) - timedelta(days=args.days)
    agents = {"claude", "grok", "codex"} if args.agent == "all" else {args.agent}
    out = []
    for s in iter_sessions(agents, since, args.subagents):
        if s is None or not s.events:
            continue
        if s.end and s.end < since:
            continue
        if args.project and args.project.lower() not in (s.cwd or "").lower():
            continue
        out.append(s)
    out.sort(key=lambda s: s.start or datetime.min.replace(tzinfo=timezone.utc))
    return out


def fmt_ts(ts):
    return ts.astimezone().strftime("%Y-%m-%d %H:%M") if ts else "????-??-?? ??:??"


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_list(args):
    for s in selected(args):
        users = sum(1 for e in s.events if e[1] == "user" and e[2].strip())
        tools = sum(1 for e in s.events if e[1] == "tool" and e[3] != "(error)")
        commands = sorted({e[2] for e in s.events if e[1] == "command"})
        skills = sorted({e[2] for e in s.events if e[1] == "tool" and e[3] == "Skill"})
        used = ", ".join(commands + skills)[:80]
        tag = "sub" if s.subagent else ""
        print(f"{fmt_ts(s.start)}  {s.agent:6} {s.sid[:8]} {tag:3} {s.project[:22]:22} "
              f"u={users:<3} t={tools:<4} {s.first_prompt()[:110]}" + (f"  [{used}]" if used else ""))
    return 0


def find(args, ids):
    pool = selected(args)
    found = []
    for wanted in ids:
        matches = [s for s in pool if s.sid.startswith(wanted) or str(s.path) == wanted]
        if not matches:
            print(f"# no session matches {wanted!r} in the last {args.days} days", file=sys.stderr)
        found += matches
    return found


def cmd_digest(args):
    for s in find(args, args.ids):
        print(f"\n##### {s.agent} {s.sid} | {s.cwd} | {fmt_ts(s.start)} -> {fmt_ts(s.end)}")
        if s.title:
            print(f"title: {s.title}")
        shown = 0
        pending_tools = []

        def flush():
            if pending_tools:
                counts = collections.Counter(pending_tools)
                print("   T " + "; ".join(f"{t} x{n}" if n > 1 else t for t, n in counts.most_common(8)))
                pending_tools.clear()

        for ts, kind, text, tool, is_error in s.events:
            if shown >= args.max_items:
                print("   ... (more; raise --max-items)")
                break
            if kind == "tool":
                if args.tools == "full":
                    print(f"   T {tool}: {text[:160]}")
                elif is_error:
                    pending_tools.append("ERROR " + text[:80].replace("\n", " "))
                else:
                    pending_tools.append(tool)
                continue
            if not text.strip():
                continue
            flush()
            label = {"user": "U", "assistant": "A", "command": "C"}[kind]
            cap = args.cap if kind != "command" else 120
            body = " ".join(text.split()) if kind != "assistant" else text.strip()
            if len(body) > cap:
                body = body[:cap] + " ..."
            print(f"{fmt_ts(ts)[11:]} {label} {body}")
            shown += 1
        flush()
    return 0


def tool_server(name):
    parts = name.split("__")
    if name.startswith("mcp__") and len(parts) >= 3:
        return "mcp:" + parts[1]
    return name


def cmd_tools(args):
    calls, sessions, errors = collections.Counter(), collections.defaultdict(set), collections.Counter()
    for s in selected(args):
        last = None
        for _ts, kind, _text, tool, is_error in s.events:
            if kind != "tool":
                continue
            if is_error:
                if last:
                    errors[last] += 1
                continue
            key = tool_server(tool) if args.by == "server" else tool
            calls[key] += 1
            sessions[key].add(s.sid)
            last = key
    print(f"{'calls':>6} {'sess':>5} {'errors':>6}  {args.by}")
    for key, n in calls.most_common(args.limit):
        print(f"{n:>6} {len(sessions[key]):>5} {errors[key]:>6}  {key}")
    return 0


def cmd_grep(args):
    pattern = re.compile(args.regex, re.I)
    for s in selected(args):
        hits = [(ts, kind, text) for ts, kind, text, tool, _ in s.events
                if pattern.search(text) or (tool and pattern.search(tool))]
        if not hits:
            continue
        print(f"\n## {fmt_ts(s.start)} {s.agent} {s.sid[:8]} {s.project} ({len(hits)} hits)")
        for ts, kind, text in hits[: args.per_session]:
            flat = " ".join(text.split())
            m = pattern.search(flat)
            lo = max(0, (m.start() if m else 0) - 80)
            print(f"   {kind[0].upper()} ...{flat[lo:lo + 220]}")
    return 0


def main():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--days", type=float, default=7, help="time window in days (default 7)")
    common.add_argument("--agent", choices=["all", "claude", "grok", "codex"], default="all")
    common.add_argument("--project", help="substring of the session's working directory")
    common.add_argument("--subagents", action="store_true", help="include subagent transcripts")

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", parents=[common]).set_defaults(func=cmd_list)

    p = sub.add_parser("digest", parents=[common])
    p.add_argument("ids", nargs="+", help="session id prefixes (from list) or file paths")
    p.add_argument("--cap", type=int, default=600, help="characters per message")
    p.add_argument("--max-items", type=int, default=80, help="messages per session")
    p.add_argument("--tools", choices=["summary", "full"], default="summary")
    p.set_defaults(func=cmd_digest)

    p = sub.add_parser("tools", parents=[common])
    p.add_argument("--by", choices=["tool", "server"], default="server")
    p.add_argument("--limit", type=int, default=40)
    p.set_defaults(func=cmd_tools)

    p = sub.add_parser("grep", parents=[common])
    p.add_argument("regex")
    p.add_argument("--per-session", type=int, default=5)
    p.set_defaults(func=cmd_grep)

    args = parser.parse_args()
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
