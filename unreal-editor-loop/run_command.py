#!/usr/bin/env python3
"""Submit one local editor command. Require start and completion evidence. Never retry."""
import argparse
import csv
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.request

SLATE = "SlateInspectorToolset.SlateInspectorToolset"
APP = "EditorToolset.EditorAppToolset"
ERROR = re.compile(r"Fatal error[!:]|=== Critical error|Assertion failed|Ensure condition failed|LogPython: Error:|Live coding failed", re.I)


class CommandWatch:
    """Track observed execution separately from a successful Type response."""
    def __init__(self, start_marker, done_marker, start_timeout=8.0, timeout=120.0):
        if not start_marker or not done_marker or start_marker == done_marker:
            raise ValueError("Supply distinct start and completion markers.")
        self.start_marker, self.done_marker = start_marker, done_marker
        self.start_timeout, self.timeout = start_timeout, timeout
        self.status, self.reason, self.started_at = "submitted", "Awaiting start acknowledgment.", None

    def observe(self, text, elapsed, alive=True):
        if self.status in ("completed", "failed", "not-submitted"):
            return self.status
        for line in text.splitlines():
            # An echoed command can contain both markers. It is not script execution.
            if re.search(r"\bCmd:", line):
                continue
            if ERROR.search(line):
                self.status, self.reason = "failed", line.strip()
                return self.status
            if self.start_marker in line and self.started_at is None:
                self.started_at = elapsed
                self.status, self.reason = "started", "The editor acknowledged execution."
            if self.done_marker in line:
                if self.started_at is None:
                    self.status, self.reason = "failed", "Completion appeared without a start acknowledgment."
                    return self.status
                else:
                    self.status, self.reason = "completed", "The editor reported completion."
        if self.status in ("completed", "failed"):
            return self.status
        if not alive:
            self.status, self.reason = "failed", "The editor exited before completion."
        elif self.started_at is None and elapsed >= self.start_timeout:
            self.status = "not-submitted"
            self.reason = "No start acknowledgment. Inspect focus and logs before another submission. Execution is unknown."
        elif self.started_at is not None and elapsed - self.started_at >= self.timeout:
            self.status, self.reason = "failed", "The started command did not complete within its time limit."
        return self.status


class LogCursor:
    def __init__(self, path):
        self.path = Path(path)
        stat = self.path.stat()
        self.identity, self.offset, self.pending = (stat.st_dev, stat.st_ino), stat.st_size, b""

    def read(self):
        stat = self.path.stat()
        if (stat.st_dev, stat.st_ino) != self.identity or stat.st_size < self.offset:
            raise RuntimeError("The editor log changed identity. Start a new observation before submitting again.")
        with self.path.open("rb") as stream:
            stream.seek(self.offset)
            data = self.pending + stream.read()
            self.offset = stream.tell()
        end = data.rfind(b"\n") + 1
        self.pending = data[end:]
        if len(self.pending) > 1024 * 1024:
            raise RuntimeError("The editor log has an oversized incomplete line.")
        return data[:end].decode("utf-8", errors="replace")


class Client:
    def __init__(self, port):
        self.url = f"http://127.0.0.1:{port}/mcp"
        self.session = None
        self.request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                    "clientInfo": {"name": "local-editor-command", "version": "1"}})
        self.request("notifications/initialized", {}, notification=True)

    def request(self, method, params, notification=False):
        body = {"jsonrpc": "2.0", "method": method, "params": params}
        if not notification:
            body["id"] = 1
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if self.session:
            headers["Mcp-Session-Id"] = self.session
        request = urllib.request.Request(self.url, json.dumps(body).encode("utf-8"), headers)
        with urllib.request.urlopen(request, timeout=15) as response:
            self.session = response.headers.get("Mcp-Session-Id") or self.session
            text = response.read().decode("utf-8-sig")
        if not text:
            return None
        if text.lstrip().startswith("data:"):
            records = [json.loads(line[5:].strip()) for line in text.splitlines() if line.startswith("data:")]
            result = next((row for row in records if row.get("id") == 1), {})
        else:
            result = json.loads(text)
        if "error" in result:
            raise RuntimeError(str(result["error"]))
        return result.get("result")

    def call(self, toolset, tool, arguments):
        result = self.request("tools/call", {"name": "call_tool", "arguments": {
            "toolset_name": toolset, "tool_name": tool, "arguments": arguments}})
        if not isinstance(result, dict) or result.get("isError"):
            raise RuntimeError(f"Editor tool failed: {tool}")
        value = json.loads("\n".join(item["text"] for item in result.get("content", []) if item.get("type") == "text"))
        return value["returnValue"]


def editor_pids():
    if os.name == "nt":
        output = subprocess.check_output(["tasklist", "/FI", "IMAGENAME eq UnrealEditor.exe", "/FO", "CSV", "/NH"])
        return [int(row[1]) for row in csv.reader(output.decode(errors="replace").splitlines())
                if len(row) > 1 and row[0].lower() == "unrealeditor.exe"]
    result = subprocess.run(["pgrep", "-x", "UnrealEditor"], capture_output=True, text=True)
    if result.returncode not in (0, 1):
        raise RuntimeError("Cannot inspect editor processes.")
    return [int(pid) for pid in result.stdout.split()]


def submit(client, command):
    if re.search(r"\bQUIT_EDITOR\b", command, re.I):
        raise ValueError("Send QUIT_EDITOR through a direct Type call, not this runner.")
    windows = json.loads(client.call(SLATE, "Windows", {"action": "list"}))
    mains = [window for window in windows if window["title"].endswith(" - Unreal Editor")]
    if len(mains) != 1:
        raise RuntimeError("Require one main editor window.")
    client.call(SLATE, "Windows", {"action": "select", "index": mains[0]["index"]})
    client.call(SLATE, "Observe", {"ref": "", "maxDepth": 60})
    snapshot = client.call(SLATE, "Snapshot", {"ref": "", "maxDepth": 60})
    match = re.search(r'text "Cmd"[^\n]*\n(?:[^\n]*\n){0,3}?[^\n]*textbox[^\n]*\[ref=(\w+)\]', snapshot)
    if not match:
        raise RuntimeError("The current snapshot does not identify Cmd.")
    if client.call(APP, "IsPIERunning", {}):
        if client.call(SLATE, "PressKey", {"key": "Shift+F1"}) is not True:
            raise RuntimeError("Cannot release PIE input capture.")
    for tool, args in (("Click", {"ref": match[1]}), ("PressKey", {"key": "Ctrl+A"}),
                       ("PressKey", {"key": "BackSpace"}),
                       ("Type", {"ref": match[1], "text": command, "submit": True})):
        if client.call(SLATE, tool, args) is not True:
            raise RuntimeError(f"{tool} failed. Inspect the log before another submission.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command")
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--start-marker", required=True)
    parser.add_argument("--done-marker", required=True)
    parser.add_argument("--start-timeout", type=float, default=8.0)
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args()
    try:
        if not args.log.is_absolute() or not 1 <= args.port <= 65535:
            raise ValueError("Supply an absolute log path and a valid local port.")
        if args.start_timeout <= 0 or args.timeout <= 0:
            raise ValueError("Timeouts must be positive.")
        pids = editor_pids()
        if len(pids) != 1:
            raise RuntimeError("Require exactly one running editor process.")
        watch = CommandWatch(args.start_marker, args.done_marker, args.start_timeout, args.timeout)
        client = Client(args.port)
        cursor = LogCursor(args.log)
        start = time.monotonic()
        submit(client, args.command)
        previous = None
        while True:
            watch.observe(cursor.read(), time.monotonic() - start, pids[0] in editor_pids())
            if watch.status != previous:
                print(json.dumps({"status": watch.status, "reason": watch.reason}), flush=True)
                previous = watch.status
            if watch.status in ("completed", "failed", "not-submitted"):
                return 0 if watch.status == "completed" else 1
            time.sleep(0.2)
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        print(json.dumps({"status": "failed", "reason": str(error),
                          "retry": "Inspect the editor log before another submission."}), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
