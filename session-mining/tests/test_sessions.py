"""Exercise readers and commands with synthetic transcripts only."""
import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "sessions.py"
SPEC = importlib.util.spec_from_file_location("sessions", SCRIPT)
sessions = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sessions)


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ts = datetime.now(timezone.utc).isoformat()
        self.claude = self.root / "claude"
        self.grok = self.root / "grok"
        self.codex = self.root / "codex"
        for name, value in [("CLAUDE", self.claude), ("GROK", self.grok), ("CODEX", self.codex)]:
            replacement = patch.object(sessions, name, value)
            replacement.start()
            self.addCleanup(replacement.stop)

    def write_lines(self, path, records):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")
        return path

    def claude_records(self):
        return [
            {"type": "user", "cwd": "/projects/demo", "timestamp": self.ts,
             "message": {"content": "Inspect the demo"}},
            {"type": "assistant", "timestamp": self.ts, "message": {"content": [
                {"type": "tool_use", "id": "call-1", "name": "mcp__example__query",
                 "input": {"query": "demo"}}]}},
            {"type": "user", "timestamp": self.ts, "message": {"content": [
                {"type": "tool_result", "tool_use_id": "call-1", "is_error": True,
                 "content": [{"type": "text", "text": "Synthetic error"}]}]}},
        ]

    def test_claude_reader_and_optional_result_capture(self):
        path = self.write_lines(self.claude / "project" / "claude-demo.jsonl", self.claude_records())
        with path.open("a") as output:
            output.write("not-json\n")
        result = sessions.read_claude(path, False, capture_results=True)
        self.assertEqual(result.cwd, "/projects/demo")
        self.assertEqual(result.first_prompt(), "Inspect the demo")
        self.assertEqual(result.calls[0]["id"], "call-1")
        self.assertEqual(result.calls[0]["line"], 2)
        self.assertTrue(result.results["call-1"]["is_error"])
        self.assertEqual(result.results["call-1"]["text"], "Synthetic error")
        self.assertEqual(sum(event[4] for event in result.events), 1)

    def test_user_commands_and_injected_text(self):
        records = [
            {"type": "user", "timestamp": self.ts, "message": {"content": text}}
            for text in ["<system-reminder>ignore this</system-reminder>",
                         "<command-name>/demo</command-name>",
                         "<user_query>Actual request</user_query>"]
        ]
        result = sessions.read_claude(self.write_lines(self.root / "commands.jsonl", records), False)
        self.assertEqual(result.first_prompt(), "Actual request")
        self.assertIn("/demo", [event[2] for event in result.events if event[1] == "command"])
        self.assertNotIn("ignore this", " ".join(event[2] for event in result.events))

    def test_grok_reader(self):
        directory = self.grok / "%2Fprojects%2Fdemo" / "grok-demo"
        self.write_lines(directory / "chat_history.jsonl", [
            {"type": "user", "timestamp": self.ts, "content": "Inspect Grok"},
            {"type": "assistant", "timestamp": self.ts, "tool_calls": [
                {"id": "g1", "name": "shell", "arguments": "{\"command\":\"pwd\"}"}]},
            {"type": "tool_result", "timestamp": self.ts, "content": "Error: synthetic"},
        ])
        (directory / "summary.json").write_text(json.dumps({
            "created_at": self.ts, "updated_at": self.ts, "session_summary": "Demo"}))
        result = sessions.read_grok(directory, False)
        self.assertEqual(result.cwd, "/projects/demo")
        self.assertEqual(result.first_prompt(), "Inspect Grok")
        self.assertEqual(result.events[1][3], "shell")
        self.assertTrue(result.events[2][4])

    def test_codex_reader(self):
        path = self.write_lines(self.codex / "2026/10/30/rollout-demo.jsonl", [
            {"type": "session_meta", "timestamp": self.ts,
             "payload": {"id": "codex-demo", "cwd": "/projects/demo"}},
            {"type": "response_item", "timestamp": self.ts, "payload": {
                "type": "message", "role": "user",
                "content": [{"type": "input_text", "text": "Inspect Codex"}]}},
            {"type": "response_item", "timestamp": self.ts, "payload": {
                "type": "function_call", "namespace": "functions", "name": "shell",
                "arguments": "{\"command\":\"pwd\"}"}},
        ])
        result = sessions.read_codex(path)
        self.assertEqual(result.sid, "codex-demo")
        self.assertEqual(result.first_prompt(), "Inspect Codex")
        self.assertEqual(result.events[1][3], "functions__shell")
        self.assertEqual(result.events[1][2], "pwd")

    def test_discovery_includes_subagents_only_when_requested(self):
        self.write_lines(self.claude / "project/main.jsonl", self.claude_records())
        self.write_lines(self.claude / "project/main/subagents/child.jsonl", self.claude_records())
        since = datetime.now(timezone.utc) - timedelta(days=1)
        self.assertEqual(len(list(sessions.iter_sessions({"claude"}, since, False))), 1)
        found = list(sessions.iter_sessions({"claude"}, since, True))
        self.assertEqual(len(found), 2)
        self.assertEqual(sum(session.subagent for session in found), 1)

    def test_cli_commands_use_only_fixture_directories(self):
        self.write_lines(self.claude / "project/claude-demo.jsonl", self.claude_records())
        cases = [
            (["list"], "Inspect the demo"),
            (["digest", "claude-demo", "--tools", "full"], "mcp__example__query"),
            (["tools", "--by", "server"], "mcp:example"),
            (["grep", "Inspect"], "Inspect the demo"),
        ]
        for args, expected in cases:
            with self.subTest(command=args[0]):
                output = io.StringIO()
                with patch.object(sys, "argv", [str(SCRIPT), *args]), \
                        patch.object(sessions.signal, "signal"), contextlib.redirect_stdout(output):
                    self.assertEqual(sessions.main(), 0)
                self.assertIn(expected, output.getvalue())
        output = io.StringIO()
        with patch.object(sys, "argv", [str(SCRIPT), "list", "--project", "other"]), \
                patch.object(sessions.signal, "signal"), contextlib.redirect_stdout(output):
            self.assertEqual(sessions.main(), 0)
        self.assertEqual(output.getvalue(), "")

    def test_empty_sources_and_missing_session(self):
        output, errors = io.StringIO(), io.StringIO()
        with patch.object(sys, "argv", [str(SCRIPT), "digest", "missing"]), \
                patch.object(sessions.signal, "signal"), \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            self.assertEqual(sessions.main(), 0)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("no session matches", errors.getvalue())

    def test_timestamp_formats(self):
        self.assertEqual(sessions.parse_ts(1700000000), sessions.parse_ts(1700000000000))
        self.assertIsNone(sessions.parse_ts("not-a-time"))
        self.assertEqual(sessions.parse_ts("2026-10-30T00:00:00Z").tzinfo, timezone.utc)

    def test_readers_close_transcript_files(self):
        source = io.StringIO(json.dumps({"type": "ignored"}) + "\n")
        with patch("builtins.open", return_value=source):
            sessions.read_claude(self.root / "closed.jsonl", False)
        self.assertTrue(source.closed)
        source = io.StringIO(json.dumps({"type": "ignored"}) + "\n")
        with patch("builtins.open", return_value=source):
            sessions.read_codex(self.root / "closed.jsonl")
        self.assertTrue(source.closed)
        directory = self.root / "grok-closed"
        self.write_lines(directory / "chat_history.jsonl", [])
        source = io.StringIO(json.dumps({"type": "ignored"}) + "\n")
        with patch("builtins.open", return_value=source):
            sessions.read_grok(directory, False)
        self.assertTrue(source.closed)

    def test_real_entrypoint_help(self):
        result = subprocess.run([sys.executable, "-I", str(SCRIPT), "--help"],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0)
        self.assertIn("digest", result.stdout)


if __name__ == "__main__":
    unittest.main()
