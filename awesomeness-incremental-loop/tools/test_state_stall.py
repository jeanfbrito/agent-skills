"""Regression checks for the no-product signal, which never stops the loop."""

import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


SCRIPT = Path(__file__).with_name("state.py")
spec = importlib.util.spec_from_file_location("awesome_state_stall", SCRIPT)
state = importlib.util.module_from_spec(spec)
spec.loader.exec_module(state)

JOURNAL = """# Loop

## Direction
- Product focus: Actors hear and make sounds in the same world.

## Gap matrix
| Item | Done when | Status |
| --- | --- | --- |
| Branch sound | Both actors hear a rustle on contact. | partial |
"""


class StallHoldTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.project = Path(tmp.name)
        (self.project / "docs").mkdir()
        (self.project / "docs/awesomeness-loop.md").write_text(JOURNAL)
        self.root = self.project / ".localdev/awesomeness"
        self.root.mkdir(parents=True)
        self.args = SimpleNamespace(project=str(self.project), journal="docs/awesomeness-loop.md",
                                    root=".localdev/awesomeness", stale_min=90, drift_depth=0,
                                    owner="test", mode="gap", row="Branch sound", why="Actors hear the branches.",
                                    rest=["pick", "Branch sound"], metric=[], file=[], commit=None, status=None,
                                    progress=None, next=None, drift=None, blocker=None)

    def arm_goal(self):
        self.args.target = "World rustle reaches player and NPC at two trees"
        self.args.check = "Listen to real-recording A/B and run two-tree actor test"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(state.arm(self.args), 0)

    def write_cycles(self, cycles):
        entries = []
        for n, mode, product in cycles:
            entries.extend([{"cycle": n, "row": "Branch sound", "kind": "pick", "mode": mode},
                            {"cycle": n, "row": "Branch sound", "kind": "end",
                             "progress": "none" if not product else "0 -> 1", "status": "partial -> partial"}])
        (self.root / "trail.jsonl").write_text("".join(json.dumps(e) + "\n" for e in entries))

    def assertLoopContinues(self):
        """The signal steers the next cycle; arm and lock still start it."""
        self.arm_goal()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(state.lock(self.args), 0)

    def brief(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            state.brief(self.args)
        return out.getvalue()

    def test_nonproduct_cycles_signal_but_never_stop_when_review_interleaves(self):
        self.write_cycles([(93, "gap", False), (94, "review", False)])
        text = self.brief()
        self.assertIn("NO-PRODUCT:", text)
        self.assertNotIn("No new cycle starts", text)
        self.assertLoopContinues()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(state.note(self.args), 0)
        self.assertEqual(len((self.root / "trail.jsonl").read_text().splitlines()), 5)

    def test_committed_tree_probe_is_not_a_product_change(self):
        self.write_cycles([(93, "gap", False), (94, "gap", False)])
        trail = state.read_trail(str(self.root))
        trail[0]["target"] = "Branches yield to both actors"
        for i in (1, 3):
            trail[i]["commit"] = "823e6f1"
            trail[i]["progress"] = "0/3 -> 3/3 blocked rays"
        (self.root / "trail.jsonl").write_text("".join(json.dumps(e) + "\n" for e in trail))
        original = state.commit_files
        try:
            state.commit_files = lambda project, sha: ["godot/src/tools/tree_collision_probe.gd"]
            self.assertIn("NO-PRODUCT:", self.brief())
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(state.lock(self.args), 4)
        finally:
            state.commit_files = original

    def test_registered_sensor_does_not_count_as_product_change(self):
        sensor = self.project / "godot/src/tools/actor_contact_sensor.gd"
        sensor.parent.mkdir(parents=True)
        sensor.write_text("extends SceneTree\n")
        journal = self.project / "docs/awesomeness-loop.md"
        journal.write_text(JOURNAL + "\n## Senses\n| Sense | How to call it |\n| --- | --- |\n"
                           "| Actor contact | godot/src/tools/actor_contact_sensor.gd |\n")
        self.write_cycles([(93, "gap", False), (94, "gap", False)])
        trail = state.read_trail(str(self.root))
        trail[1]["commit"] = trail[3]["commit"] = "sensor-only"
        (self.root / "trail.jsonl").write_text("".join(json.dumps(e) + "\n" for e in trail))
        original = state.commit_files
        try:
            state.commit_files = lambda project, sha: ["godot/src/tools/actor_contact_sensor.gd"]
            self.assertIn("NO-PRODUCT:", self.brief())
        finally:
            state.commit_files = original

    def test_one_diagnostic_work_cycle_does_not_signal(self):
        self.write_cycles([(93, "gap", False)])
        self.assertNotIn("NO-PRODUCT:", self.brief())

    def test_two_nonproduct_work_cycles_signal_even_when_metric_claims_progress(self):
        self.write_cycles([(93, "gap", False), (94, "gap", False)])
        trail = state.read_trail(str(self.root))
        trail[-1]["progress"] = "0 verified branch routes -> 1 verified branch route"
        (self.root / "trail.jsonl").write_text("".join(json.dumps(e) + "\n" for e in trail))
        self.assertIn("NO-PRODUCT:", self.brief())
        self.assertLoopContinues()

    def test_intervening_product_commit_counts_even_if_end_notes_only_docs_commit(self):
        self.write_cycles([(101, "gap", False), (102, "gap", False)])
        trail = state.read_trail(str(self.root))
        trail[1]["commit"] = "before"
        trail[3]["commit"] = "docs"
        (self.root / "trail.jsonl").write_text("".join(json.dumps(e) + "\n" for e in trail))
        original_files = state.commit_files
        original_range = state.commit_range_files
        try:
            state.commit_files = lambda project, sha: ["docs/awesomeness-loop.md"]
            state.commit_range_files = lambda project, before, after: ["godot/src/map/private_scene_adapter.gd"]
            self.assertNotIn("NO-PRODUCT:", self.brief())
        finally:
            state.commit_files = original_files
            state.commit_range_files = original_range

    def test_product_commit_clears_the_streak(self):
        self.write_cycles([(93, "gap", False), (94, "gap", True), (95, "review", False)])
        # The product cycle is represented by a changed source file in a real commit.
        # Patch the commit lookup so this test targets classification rather than Git setup.
        original = state.commit_files
        try:
            state.commit_files = lambda project, sha: ["godot/src/game/tree_branch_bend.gd"] if sha == "product" else None
            trail = state.read_trail(str(self.root))
            trail.insert(3, {"cycle": 94, "row": "Branch sound", "kind": "commit", "commit": "product"})
            (self.root / "trail.jsonl").write_text("".join(json.dumps(e) + "\n" for e in trail))
            self.assertNotIn("NO-PRODUCT:", self.brief())
        finally:
            state.commit_files = original

    def test_explicit_resume_clears_the_signal_without_erasing_history(self):
        self.write_cycles([(93, "gap", False), (94, "review", False)])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(state.pause(self.args, False), 0)
        self.assertNotIn("NO-PRODUCT:", self.brief())
        self.write_cycles([(93, "gap", False), (94, "review", False),
                           (96, "gap", False), (97, "review", False)])
        self.assertIn("NO-PRODUCT:", self.brief())

    def test_new_work_requires_a_measurable_product_objective_before_pick(self):
        self.args.target = None
        self.args.check = None
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(state.note(self.args), 2)
        self.assertIn("unarmed", out.getvalue().lower())
        self.assertFalse((self.root / "trail.jsonl").exists())
        self.arm_goal()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(state.note(self.args), 0)
        pick = state.read_trail(str(self.root))[0]
        self.assertEqual(pick["target"], self.args.target)
        self.assertEqual(pick["check"], self.args.check)

    def test_cycle_cannot_start_until_orchestrator_arms_a_goal(self):
        self.args.target = "Make branch contact audible to both actors"
        self.args.check = "Run real recording A/B with two actor contacts"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(state.lock(self.args), 4)
            self.assertEqual(state.note(self.args), 2)
            self.assertEqual(state.arm(self.args), 0)
        self.assertIn("ARMED:", self.brief())
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(state.lock(self.args), 0)
            self.assertEqual(state.note(self.args), 0)
        self.assertEqual(state.read_trail(str(self.root))[0]["target"], self.args.target)

    def test_two_unmet_armed_goals_signal_even_with_product_commit(self):
        self.arm_goal()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(state.note(self.args), 0)
        trail = state.read_trail(str(self.root))
        trail.extend([{"cycle": 1, "row": "Branch sound", "kind": "commit", "commit": "product"},
                      {"cycle": 1, "row": "Branch sound", "kind": "end", "status": "partial -> partial",
                       "progress": "none", "achieved": "no"}])
        (self.root / "trail.jsonl").write_text("".join(json.dumps(e) + "\n" for e in trail))
        original = state.commit_files
        try:
            state.commit_files = lambda project, sha: ["godot/src/game/tree_branch_bend.gd"]
            self.assertNotIn("NO-PRODUCT:", self.brief())
            with (self.root / "trail.jsonl").open("a") as fh:
                for e in ({"cycle": 2, "row": "Branch sound", "kind": "pick", "mode": "gap"},
                          {"cycle": 2, "row": "Branch sound", "kind": "commit", "commit": "product"},
                          {"cycle": 2, "row": "Branch sound", "kind": "end", "status": "partial -> partial",
                           "progress": "none", "achieved": "no"}):
                    fh.write(json.dumps(e) + "\n")
            self.assertIn("NO-PRODUCT:", self.brief())
        finally:
            state.commit_files = original

    def test_armed_cycle_end_requires_explicit_check_result(self):
        self.arm_goal()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(state.note(self.args), 0)
        self.args.rest = ["end"]
        self.args.status = "partial -> partial"
        self.args.progress = "none"
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(state.note(self.args), 2)
        self.assertIn("--achieved", out.getvalue())
        self.args.achieved = "no"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(state.note(self.args), 0)
        self.assertEqual(state.read_trail(str(self.root))[-1]["achieved"], "no")

    def test_cycle_cannot_replace_armed_goal(self):
        self.arm_goal()
        self.args.target = "Write another collision probe"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(state.note(self.args), 2)
        self.assertFalse((self.root / "trail.jsonl").exists())

    def test_review_also_requires_an_objective_and_check(self):
        self.args.mode = "review"
        self.args.row = "review"
        self.args.rest = ["pick", "sense-check review"]
        self.args.target = None
        self.args.check = None
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(state.note(self.args), 2)
        self.args.target = "Decide which of the last three cycles changed player experience"
        self.args.check = "Compare cycle commits with their delivered game behavior"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(state.arm(self.args), 0)
            self.assertEqual(state.note(self.args), 0)

    def test_open_cycle_can_finish_after_signal(self):
        self.write_cycles([(93, "gap", False), (94, "review", False)])
        with (self.root / "trail.jsonl").open("a") as fh:
            fh.write(json.dumps({"cycle": 96, "row": "Branch sound", "kind": "pick"}) + "\n")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(state.lock(self.args), 0)
        self.assertTrue((self.root / "lock").exists())


if __name__ == "__main__":
    unittest.main()
