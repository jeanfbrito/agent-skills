#!/usr/bin/env python3
"""Check command acknowledgment, input release and terminal failures without an editor."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("run_command", Path(__file__).parents[1] / "run_command.py")
subject = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(subject)


class PathAndLockTests(unittest.TestCase):
    def test_git_bash_paths_become_windows_paths(self):
        # The editor answered "Could not load Python file '/c/Users/...'" for a Git Bash path.
        home = Path.home().as_posix()
        self.assertEqual(subject.editor_command('py "/c/Users/me/a b/x.py" /Game/Maps/Lvl', nt=True),
                         'py "C:/Users/me/a b/x.py" /Game/Maps/Lvl')
        self.assertEqual(subject.editor_command("py ~/tools/x.py /d/data", nt=True), f"py {home}/tools/x.py D:/data")
        self.assertEqual(subject.editor_command('py "C:/x.py" /Game/c/Asset', nt=True), 'py "C:/x.py" /Game/c/Asset')
        self.assertEqual(subject.editor_command("stat fps", nt=True), "stat fps")
        self.assertEqual(subject.editor_command('py "/c/x.py"', nt=False), 'py "/c/x.py"')

    def test_a_second_command_on_the_same_editor_is_refused(self):
        # Two runners typed into one Cmd box at once and broke each other's checks.
        with tempfile.TemporaryDirectory() as folder:
            with subject.EditorLock(8000, folder):
                with self.assertRaisesRegex(RuntimeError, "Another runner command"):
                    with subject.EditorLock(8000, folder):
                        pass
                with subject.EditorLock(8001, folder):
                    pass
            with subject.EditorLock(8000, folder):
                pass


class CommandTests(unittest.TestCase):
    def watch(self):
        return subject.CommandWatch("PROBE: started", "PROBE: done", 2, 5)

    def test_true_type_without_acknowledgment_does_not_wait_full_timeout(self):
        watch = self.watch()
        self.assertEqual(watch.observe("", 1.9), "submitted")
        self.assertEqual(watch.observe("", 2.0), "not-submitted")
        self.assertIn("Execution is unknown", watch.reason)

    def test_delayed_start_and_completion(self):
        watch = self.watch()
        self.assertEqual(watch.observe("LogPython: PROBE: started\n", 1.5), "started")
        self.assertEqual(watch.observe("", 5.0), "started")
        self.assertEqual(watch.observe("LogPython: PROBE: done\n", 6.0), "completed")

    def test_command_echo_is_not_execution(self):
        watch = self.watch()
        echo = 'Cmd: py "print(\"PROBE: started\"); print(\"PROBE: done\")"\n'
        self.assertEqual(watch.observe(echo, 2.0), "not-submitted")

    def test_orphan_completion_fails(self):
        watch = self.watch()
        self.assertEqual(watch.observe("PROBE: done\nPROBE: started\n", 1), "failed")

    def test_fatal_logs_and_process_exit_end_the_wait(self):
        for fatal in ("Fatal error!", "Fatal error:", "Assertion failed: X", "LogPython: Error: failure"):
            with self.subTest(fatal=fatal):
                self.assertEqual(self.watch().observe(fatal + "\n", .1), "failed")
        watch = self.watch()
        watch.observe("PROBE: started\n", .1)
        self.assertEqual(watch.observe("", .2, alive=False), "failed")
        self.assertIn("exited", watch.reason)

    def test_deleted_actors_fail_at_once_with_the_undo(self):
        # 2026-11-18: after Play ended, the clear keys reached the level and deleted the Landscape
        for line in ("Cmd: DELETE", "Cmd: ACTOR DELETE"):
            with self.subTest(line=line):
                watch = self.watch()
                self.assertEqual(watch.observe("[2026.11.18-01.44.25:100][1]" + line + "\n", 0.5), "failed")
                self.assertIn("TRANSACTION UNDO", watch.reason)
        self.assertEqual(self.watch().observe('Cmd: py "/local/delete_probe.py"\n', 0.5), "submitted")

    def test_started_command_uses_its_own_timeout(self):
        watch = self.watch()
        watch.observe("PROBE: started\n", 1.9)
        self.assertEqual(watch.observe("", 6.8), "started")
        self.assertEqual(watch.observe("", 6.9), "failed")

    def test_log_cursor_ignores_old_lines_and_keeps_partial_marker(self):
        with tempfile.TemporaryDirectory() as folder:
            log = Path(folder) / "editor.log"
            log.write_bytes(b"PROBE: started\nPROBE: done\n")
            cursor = subject.LogCursor(log)
            self.assertEqual(cursor.read(), "")
            with log.open("ab") as stream:
                stream.write(b"LogPython: PROBE: sta")
            self.assertEqual(cursor.read(), "")
            with log.open("ab") as stream:
                stream.write(b"rted\n")
            self.assertEqual(cursor.read(), "LogPython: PROBE: started\n")
            log.write_bytes(b"")
            with self.assertRaisesRegex(RuntimeError, "changed identity"):
                cursor.read()

    def test_pie_capture_releases_immediately_before_clear_and_type(self):
        class FakeClient:
            def __init__(self):
                self.calls = []

            def call(self, toolset, tool, args):
                self.calls.append((tool, args))
                if tool == "Windows" and args["action"] == "list":
                    return '[{"title":"Fixture - Unreal Editor","index":0}]'
                if tool == "Snapshot":
                    return '  text "Cmd" [ref=x1]\n  textbox [ref=tb2]\n'
                return True

        client = FakeClient()
        subject.submit(client, 'py "/local/probe.py"')
        self.assertEqual(client.calls[-5:], [
            ("PressKey", {"key": "Shift+F1"}), ("Type", {"ref": "tb2", "text": " ", "submit": False}),
            ("PressKey", {"key": "Ctrl+A"}), ("PressKey", {"key": "BackSpace"}),
            ("Type", {"ref": "tb2", "text": 'py "/local/probe.py"', "submit": True})])
        with self.assertRaisesRegex(ValueError, "direct Type"):
            subject.submit(client, "QUIT_EDITOR")

    def test_a_type_call_that_times_out_can_be_running(self):
        class BusyClient:
            def __init__(self, error):
                self.error = error

            def call(self, toolset, tool, args):
                if tool == "Windows" and args["action"] == "list":
                    return '[{"title":"Fixture - Unreal Editor","index":0}]'
                if tool == "Snapshot":
                    return '  text "Cmd" [ref=x1]\n  textbox [ref=tb2]\n'
                if tool == "Type" and args.get("submit"):
                    raise self.error
                return False if tool == "IsPIERunning" else True

        # A long script blocks the game thread: the Type answer comes after the socket timeout.
        self.assertFalse(subject.submit(BusyClient(TimeoutError("timed out")), "py long.py"))
        self.assertFalse(subject.submit(BusyClient(subject.urllib.error.URLError(TimeoutError())), "py long.py"))
        with self.assertRaises(ConnectionRefusedError):
            subject.submit(BusyClient(ConnectionRefusedError()), "py long.py")


if __name__ == "__main__":
    unittest.main()
