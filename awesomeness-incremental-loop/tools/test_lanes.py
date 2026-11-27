"""Lanes: forks of one loop that run at the same time (references/lanes.md)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from test_state_index import write_fake_gitnexus

HERE = Path(__file__).parent
LANES = [sys.executable, str(HERE / "lanes.py")]
STATE = [sys.executable, str(HERE / "state.py")]
JOURNAL = """# Loop

## Direction

- Product focus: Find a message fast.

## Gap matrix

| Item | Done when | Status |
| --- | --- | --- |
| R1 search | A search returns in 1 s. | partial |
| R2 filter | A filter keeps the order. | missing |
| R3 export | An export opens in a spreadsheet. | missing |
"""


def run(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def git(repo, *args):
    r = run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *args])
    assert r.returncode == 0, r.stderr
    return r.stdout


class LanesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        env = mock.patch.dict(os.environ, {"AWESOMENESS_GITNEXUS": write_fake_gitnexus(self.tmp.name),
                                           "FAKE_GITNEXUS_LOG": os.path.join(self.tmp.name, "calls.log"),
                                           "GITNEXUS_SCOPE_DIR": os.path.join(self.tmp.name, "scope")})
        env.start()  # no test indexes a real checkout or adds it to the GitNexus registry
        self.addCleanup(env.stop)
        self.parent = Path(os.path.realpath(self.tmp.name)) / "app"
        (self.parent / "docs").mkdir(parents=True)
        (self.parent / "docs/awesomeness-loop.md").write_text(JOURNAL)
        (self.parent / ".gitignore").write_text(".localdev/\n")
        (self.parent / "a.txt").write_text("one\ntwo\nthree\nfour\nfive\nsix\nseven\neight\n")
        git(self.parent, "init", "-q", "-b", "awesomeness/day")
        git(self.parent, "add", ".")
        git(self.parent, "commit", "-qm", "start")
        self.proot = self.parent / ".localdev/awesomeness"
        self.proot.mkdir(parents=True)
        notes = [{"cycle": 1, "kind": "pick", "row": "R1 search"}, {"cycle": 1, "kind": "end", "row": "R1 search"},
                 {"cycle": 2, "kind": "pick", "row": "R2 filter"}, {"cycle": 2, "kind": "end", "row": "R2 filter"}]
        (self.proot / "trail.jsonl").write_text("".join(json.dumps(n) + "\n" for n in notes))

    def add(self, lane):
        r = run(LANES + ["add", "--project", str(self.parent), "--lane", lane])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return Path(f"{self.parent}-lane-{lane}")

    def arm(self, lane, row, *mode):
        return run(LANES + ["arm", "--project", str(lane), "--row", row, "--target", "t", "--check", "c", *mode])

    def test_add_forks_a_worktree_with_the_parent_history(self):
        lane = self.add("a")
        self.assertIn("awesomeness/day-lane-a", git(lane, "branch", "--show-current"))
        meta = json.loads((lane / ".localdev/awesomeness/lane.json").read_text())
        self.assertEqual(os.path.normpath(meta["parent_root"]), str(self.proot))  # lanes.py joins ".localdev/awesomeness"
        self.assertEqual(meta["forked_cycle"], 2)
        self.assertEqual((lane / ".localdev/awesomeness/trail.jsonl").read_text(), (self.proot / "trail.jsonl").read_text())

    def test_add_refuses_a_parent_with_an_open_cycle(self):
        with open(self.proot / "trail.jsonl", "a") as fh:
            fh.write(json.dumps({"cycle": 3, "kind": "pick", "row": "R3 export"}) + "\n")
        r = run(LANES + ["add", "--project", str(self.parent), "--lane", "a"])
        self.assertEqual(r.returncode, 2)
        self.assertIn("open cycle", r.stdout)

    def test_add_refuses_a_parent_with_chores_that_each_lane_would_repeat(self):
        (self.parent / "docs/awesomeness-loop.md").write_text(JOURNAL.replace("An export opens in a spreadsheet.", ""))
        git(self.parent, "commit", "-qam", "row without done when")
        r = run(LANES + ["add", "--project", str(self.parent), "--lane", "a"])
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("NO-DONE-WHEN", r.stdout)
        r = run(LANES + ["add", "--project", str(self.parent), "--lane", "a", "--allow-chores"])
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_add_refuses_loop_docs_that_are_not_committed(self):
        (self.parent / "docs/awesomeness-loop.md").write_text(JOURNAL + "\nedit\n")
        r = run(LANES + ["add", "--project", str(self.parent), "--lane", "a"])
        self.assertEqual(r.returncode, 2)
        self.assertIn("not committed", r.stdout)

    def test_a_row_belongs_to_one_lane(self):
        a, b = self.add("a"), self.add("b")
        self.assertEqual(self.arm(a, "R1 search").returncode, 0)
        r = self.arm(b, "R1 search")
        self.assertEqual(r.returncode, 2)
        self.assertIn("lane a owns row", r.stdout)
        self.assertEqual(self.arm(b, "R2 filter").returncode, 0)

    def test_a_row_stays_with_the_lane_that_worked_it(self):
        a, b = self.add("a"), self.add("b")
        with open(a / ".localdev/awesomeness/trail.jsonl", "a") as fh:
            fh.write(json.dumps({"cycle": 3, "kind": "end", "row": "`R3 export`"}) + "\n")
        r = self.arm(b, "R3 export")
        self.assertEqual(r.returncode, 2, r.stdout)
        # A row that both lanes only inherited from the parent is free.
        self.assertEqual(self.arm(b, "R1 search").returncode, 0)

    def test_each_lane_runs_its_own_review(self):
        a, b = self.add("a"), self.add("b")
        with open(a / ".localdev/awesomeness/trail.jsonl", "a") as fh:  # the row that review-prompt.md picks
            fh.write(json.dumps({"cycle": 3, "kind": "pick", "row": "review", "mode": "review"}) + "\n")
            fh.write(json.dumps({"cycle": 3, "kind": "end", "row": "review"}) + "\n")
        r = self.arm(b, "review", "--mode", "review")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_the_parent_does_not_run_next_to_its_lanes(self):
        parent_arm = STATE + ["arm", "--project", str(self.parent), "--row", "R3 export", "--target", "t", "--check", "c"]
        self.assertEqual(run(parent_arm).returncode, 0)
        r = run(LANES + ["add", "--project", str(self.parent), "--lane", "a"])
        self.assertEqual(r.returncode, 2, r.stdout)  # a goal armed before the fork would run next to the lanes
        self.assertIn("armed goal", r.stdout)
        (self.proot / "armed-goal.json").unlink()
        self.add("a")
        r = run(parent_arm)
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("this loop has lanes (a)", r.stdout)

    def test_retire_keeps_the_trail_and_frees_the_parent(self):
        a = self.add("a")
        r = run(LANES + ["retire", "--project", str(a)])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(a.exists())
        self.assertTrue((self.proot / "lanes/a/trail.jsonl").exists())  # the lane's history outlives its worktree
        self.assertIn(f"remove --force {a}", Path(os.environ["FAKE_GITNEXUS_LOG"]).read_text())
        r = run(STATE + ["arm", "--project", str(self.parent), "--row", "R3 export", "--target", "t", "--check", "c"])
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_retire_refuses_a_lane_that_runs_a_cycle(self):
        a = self.add("a")
        with open(a / ".localdev/awesomeness/trail.jsonl", "a") as fh:
            fh.write(json.dumps({"cycle": 3, "kind": "pick", "row": "R1 search"}) + "\n")
        r = run(LANES + ["retire", "--project", str(a)])
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertTrue(a.exists())

    def test_retire_can_keep_the_worktree(self):
        a = self.add("a")
        r = run(LANES + ["retire", "--project", str(a), "--keep-worktree"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(a.exists())
        self.assertFalse((a / ".localdev/awesomeness/lane.json").exists())

    def test_the_parent_pause_stops_every_lane(self):
        a = self.add("a")
        self.assertEqual(self.arm(a, "R1 search").returncode, 0)
        r = run(STATE + ["pause", "--project", str(self.parent)])
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("LANE a: LOCK: free.", r.stdout)  # the human sees each lane cycle that still runs
        r = run(STATE + ["lock", "--project", str(a)])
        self.assertEqual(r.returncode, 4, r.stdout)
        r = run(STATE + ["arm", "--project", str(a), "--row", "R2 filter", "--target", "t", "--check", "c"])
        self.assertEqual(r.returncode, 4, r.stdout)
        r = run(STATE + ["brief", "--project", str(a)])
        self.assertIn("Lane stopped by its parent loop", r.stdout)
        run(STATE + ["resume", "--project", str(self.parent)])
        r = run(STATE + ["lock", "--project", str(a)])
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_a_plain_loop_pause_message_is_unchanged(self):
        run(STATE + ["pause", "--project", str(self.parent)])
        r = run(STATE + ["brief", "--project", str(self.parent)])
        self.assertIn("PAUSED: the human paused the loop (state.py resume to continue).\n", r.stdout)

    def gate(self, ref, other):
        return run(LANES + ["gate", "--project", str(self.parent), "--base", "awesomeness/day",
                            "--ref", ref, "--against", other, "--no-graph"])

    def branch(self, name, edits):
        git(self.parent, "branch", name, "awesomeness/day")
        tree = Path(os.path.realpath(self.tmp.name)) / name.replace("/", "-")
        git(self.parent, "worktree", "add", "-q", str(tree), name)
        for path, text in edits.items():
            (tree / path).parent.mkdir(parents=True, exist_ok=True)
            (tree / path).write_text(text)
        git(tree, "add", ".")
        git(tree, "commit", "-qm", name)

    def test_gate_separates_product_conflicts_from_loop_docs(self):
        self.branch("x", {"a.txt": "ONE\ntwo\nthree\nfour\nfive\nsix\nseven\neight\n",
                          "docs/awesomeness-loop.md": JOURNAL + "x\n"})
        self.branch("y", {"a.txt": "uno\ntwo\nthree\nfour\nfive\nsix\nseven\neight\n",
                          "docs/awesomeness-loop.md": JOURNAL + "y\n"})
        r = self.gate("x", "y")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("CONFLICT a.txt", r.stdout)
        self.assertIn("LOOP-DOC docs/awesomeness-loop.md", r.stdout)
        self.assertNotIn("SHARED docs/awesomeness-loop.md", r.stdout)

    def test_gate_asks_for_both_checks_when_a_file_is_shared(self):
        self.branch("x", {"a.txt": "ONE\ntwo\nthree\nfour\nfive\nsix\nseven\neight\n"})
        self.branch("y", {"a.txt": "one\ntwo\nthree\nfour\nfive\nsix\nseven\nEIGHT\n"})
        r = self.gate("x", "y")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("SHARED a.txt", r.stdout)

    def graph_gate(self, ref="x", **env):
        files = json.dumps({"markdown": "| f.filePath |\n| --- |\n| src/p.txt |\n| src/q.txt |", "row_count": 2})
        cmd = LANES + ["gate", "--project", str(self.parent), "--base", "awesomeness/day", "--ref", ref, "--against", "y"]
        return subprocess.run(cmd, capture_output=True, text=True, env={**os.environ, "FAKE_GITNEXUS_FILES": files, **env})

    def test_gate_reads_a_graph_query_with_no_rows(self):
        self.branch("x", {"src/p.txt": "p\n"})
        self.branch("y", {"src/q.txt": "q\n"})
        r = self.graph_gate()  # the coupling query prints [] for no rows
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("have 2 of 2 changed files", r.stdout)

    def test_gate_reports_coupled_files_from_the_graph(self):
        self.branch("x", {"src/p.txt": "p\n"})
        self.branch("y", {"src/q.txt": "q\n"})
        rows = json.dumps({"markdown": "| src | dst | rel |\n| --- | --- | --- |\n| src/q.txt | src/p.txt | IMPORTS |"})
        r = self.graph_gate(FAKE_GITNEXUS_COUPLING=rows)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("COUPLED src/q.txt -> src/p.txt (IMPORTS)", r.stdout)

    def test_gate_stops_on_an_index_that_does_not_work(self):
        self.branch("x", {"src/p.txt": "p\n"})
        self.branch("y", {"src/q.txt": "q\n"})
        r = self.graph_gate(FAKE_GITNEXUS_FAIL="all")
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)  # not a quiet gate with git only
        self.assertIn("does not work", r.stderr)

    def test_gate_needs_a_worktree_for_each_side(self):
        self.branch("y", {"src/q.txt": "q\n"})
        git(self.parent, "branch", "z", "awesomeness/day")
        r = self.graph_gate(ref="z")
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("no worktree has z checked out", r.stderr)

    def test_a_gate_error_is_not_a_verdict(self):
        self.branch("x", {"src/p.txt": "p\n"})
        r = run(LANES + ["gate", "--project", str(self.parent), "--base", "no-such-ref", "--ref", "x",
                         "--against", "x", "--no-graph"])
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)  # exit 1 would mean "merge, then rerun the checks"
        self.assertIn("failed", r.stderr)

    def test_gate_is_clean_for_separate_files(self):
        self.branch("x", {"src/p.txt": "p\n"})
        self.branch("y", {"src/q.txt": "q\n"})
        r = self.gate("x", "y")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("VERDICT: clean", r.stdout)


if __name__ == "__main__":
    unittest.main()
