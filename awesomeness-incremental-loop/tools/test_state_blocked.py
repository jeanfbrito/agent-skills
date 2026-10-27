"""Regression checks for a human-blocked loop that still has unrelated open rows."""

import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


SCRIPT = Path(__file__).with_name("state.py")
spec = importlib.util.spec_from_file_location("awesome_state", SCRIPT)
state = importlib.util.module_from_spec(spec)
spec.loader.exec_module(state)

JOURNAL = """# Loop

## Direction

- Product focus: Hear nearby footsteps.

## Gap matrix

| Item | Done when | Status |
| --- | --- | --- |
| Ground footsteps | Human hears four paired clips. | blocked |
| Door routing | Open routes match the flood. | partial |
"""


class BlockedCycleTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name)
        (self.project / "docs").mkdir()
        (self.project / "docs/awesomeness-loop.md").write_text(JOURNAL)
        self.root = self.project / ".localdev/awesomeness"
        self.root.mkdir(parents=True)
        self.args = SimpleNamespace(project=str(self.project), journal="docs/awesomeness-loop.md",
                                    root=".localdev/awesomeness", stale_min=90, drift_depth=0)

    def brief(self, entries):
        (self.root / "trail.jsonl").write_text("".join(json.dumps(e) + "\n" for e in entries))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(state.brief(self.args), 0)
        return out.getvalue()

    def test_open_blocked_cycle_must_end_not_recheck(self):
        """Catches resuming a human-blocked cycle and rechecking its clips forever."""
        text = self.brief([
            {"cycle": 73, "kind": "pick", "row": "Ground footsteps", "mode": "gap"},
            {"cycle": 73, "kind": "blocked", "row": "Ground footsteps",
             "text": "Waiting for a human verdict on four clips"},
        ])
        self.assertIn("END-BLOCKED-CYCLE", text)
        self.assertIn("note end", text)
        self.assertIn("Door routing", text)

    def test_retracted_pick_is_not_treated_as_a_parked_cycle(self):
        """Catches forcing a parked status for a pick retracted on an open row."""
        text = self.brief([
            {"cycle": 70, "kind": "pick", "row": "Door routing", "mode": "gap"},
            {"cycle": 70, "kind": "blocked", "row": "Door routing", "text": "Retract this pick"},
        ])
        self.assertNotIn("END-BLOCKED-CYCLE", text)

    def test_typed_human_block_survives_note_serialization(self):
        """Catches depending on whether the note prose happens to say 'human'."""
        self.args.rest = ["blocked", "Waiting for the verdict"]
        self.args.row = None
        self.args.mode = self.args.why = self.args.drift = None
        self.args.metric = self.args.file = []
        self.args.commit = self.args.status = self.args.progress = self.args.next = None
        self.args.blocker = "human"
        (self.root / "trail.jsonl").write_text(json.dumps(
            {"cycle": 73, "kind": "pick", "row": "Ground footsteps", "mode": "gap"}) + "\n")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(state.note(self.args), 0)
        entries = state.read_trail(str(self.root))
        self.assertEqual(entries[-1]["blocker"], "human")

    def test_six_idle_cycles_wait_even_with_open_rows_after_human_block(self):
        """Catches cycling reviews and blocked rows when an unrelated row is still open."""
        entries = []
        for n in range(68, 74):
            row = "Ground footsteps" if n == 73 else "Door routing"
            entries.append({"cycle": n, "kind": "pick", "row": row, "mode": "gap"})
            if n == 73:
                entries.append({"cycle": n, "kind": "blocked", "row": row,
                                "text": "A human listening verdict is required"})
            entries.append({"cycle": n, "kind": "end", "row": row,
                            "status": "blocked -> blocked" if n == 73 else "partial -> partial",
                            "progress": "none"})
        text = self.brief(entries)
        self.assertIn("WAITING:", text)
        self.assertLess(text.index("WAITING:"), text.index("REVIEW-DUE:"))

    def test_parked_row_cannot_be_picked_again_as_normal_work(self):
        """Catches picking the same blocked listening row after its cycle ended."""
        self.args.rest = ["pick", "Try the same footstep clips"]
        self.args.row = "Ground footsteps"
        self.args.mode = "gap"
        self.args.why = "The player hears nearby footsteps."
        self.args.metric = []
        self.args.file = []
        self.args.commit = self.args.status = self.args.progress = self.args.next = self.args.drift = None
        self.args.blocker = None
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = state.note(self.args)
        self.assertEqual(result, 2)
        self.assertIn("parked", out.getvalue())
        self.assertFalse((self.root / "trail.jsonl").exists())

    def test_new_nonhuman_block_replaces_old_human_block(self):
        """Catches waiting on an obsolete verdict after a later blocker replaces it."""
        entries = [{"cycle": 60, "kind": "pick", "row": "Ground footsteps"},
                   {"cycle": 60, "kind": "blocked", "row": "Ground footsteps", "blocker": "human",
                    "text": "Need a verdict"},
                   {"cycle": 60, "kind": "end", "row": "Ground footsteps",
                    "status": "partial -> blocked", "progress": "none"},
                   {"cycle": 61, "kind": "pick", "row": "Ground footsteps", "mode": "unblock"},
                   {"cycle": 61, "kind": "blocked", "row": "Ground footsteps",
                    "text": "No source asset is available"},
                   {"cycle": 61, "kind": "end", "row": "Ground footsteps",
                    "status": "blocked -> blocked", "progress": "none"}]
        for n in range(62, 68):
            entries += [{"cycle": n, "kind": "pick", "row": "Door routing", "mode": "gap"},
                        {"cycle": n, "kind": "end", "row": "Door routing",
                         "status": "partial -> partial", "progress": "none"}]
        self.assertNotIn("WAITING:", self.brief(entries))

    def test_waiting_cycle_resets_idle_count(self):
        """Catches immediately asking for another WAITING cycle after a human wake."""
        entries = [{"cycle": 68, "kind": "pick", "row": "Ground footsteps"},
                   {"cycle": 68, "kind": "blocked", "row": "Ground footsteps",
                    "text": "Waiting for a human listening verdict"},
                   {"cycle": 68, "kind": "end", "row": "Ground footsteps",
                    "status": "partial -> blocked", "progress": "none"}]
        for n in range(69, 75):
            entries += [{"cycle": n, "kind": "pick", "row": "Door routing", "mode": "gap"},
                        {"cycle": n, "kind": "end", "row": "Door routing",
                         "status": "partial -> partial", "progress": "none"}]
        entries += [{"cycle": 75, "kind": "pick", "row": "waiting", "mode": "waiting"},
                    {"cycle": 75, "kind": "end", "row": "waiting", "status": "waiting", "progress": "none"}]
        self.assertNotIn("WAITING:", self.brief(entries))

    def test_independent_progress_prevents_waiting(self):
        """Catches waiting while an independent row's measured result improves."""
        entries = [{"cycle": 68, "kind": "pick", "row": "Ground footsteps"},
                   {"cycle": 68, "kind": "blocked", "row": "Ground footsteps",
                    "text": "Waiting for a human listening verdict"},
                   {"cycle": 68, "kind": "end", "row": "Ground footsteps",
                    "status": "partial -> blocked", "progress": "none"}]
        for n in range(69, 75):
            entries += [{"cycle": n, "kind": "pick", "row": "Door routing", "mode": "gap"},
                        {"cycle": n, "kind": "end", "row": "Door routing",
                         "status": "partial -> partial", "progress": "22/391 -> 10/391" if n == 72 else "none"}]
        self.assertNotIn("WAITING:", self.brief(entries))

    def test_independent_work_does_not_wait_without_human_block(self):
        """Catches suppressing an ordinary open row just because six measurements did not change code."""
        entries = []
        for n in range(68, 74):
            entries += [{"cycle": n, "kind": "pick", "row": "Door routing", "mode": "gap"},
                        {"cycle": n, "kind": "end", "row": "Door routing",
                         "status": "partial -> partial", "progress": "none"}]
        self.assertNotIn("WAITING:", self.brief(entries))


if __name__ == "__main__":
    unittest.main()
