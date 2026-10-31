"""Check required skill text, not model obedience or live GitHub behavior."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]


def missing_gates(text, gates):
    return [name for name, pattern in gates.items() if not re.search(pattern, text, re.S)]


CLOSED_GATES = {
    "finite scope": r"finite completion condition",
    "separate permissions": r"Commit or push authorization does not authorize comments, thread resolution, reopening, or merging",
    "keep closed": r"Require it to remain CLOSED",
    "no green watcher": r"Do not run `watch-pr\.sh` in this mode",
    "remote readback": r"Read the actual remote ref after pushing.*match the intended commit SHA",
    "workflow effects": r"Inspect workflow runs for the pushed SHA.*IDs, events, status, and URLs",
    "human stop": r"Stop on new human feedback, another person's branch changes",
    "exact comment approval": r"Comments still require approval of their exact text before posting",
    "verified publication": r"Do not publish while a required result is `FAIL` or `UNVERIFIED`",
}

PREFLIGHT_GATES = {
    "exact heads": r"exact commit SHA, base branch and SHA",
    "remote identity": r"git ls-remote <remote> refs/heads/<branch>",
    "actual commands": r"Record actual CI commands, including working directories, flags, environment, setup, and matrix variants",
    "proof categories": r"local checks, CI runs, and missing proof",
    "node identity": r"A combined-tree PASS is not evidence for the extracted node",
    "workflow fanout": r"Estimate workflow runs and matrix jobs per action and for the full batch",
    "wave authority": r"Publish only within explicit batch or wave authorization and approved exact PR text",
    "first wave": r"Check the first wave's remote refs and actual triggered workflows before the next wave",
}


class SkillContracts(unittest.TestCase):
    def read(self, path):
        return (ROOT / path).read_text()

    def test_frontmatter_line_limits_and_readme_rows(self):
        readme = self.read("README.md")
        for name in ("commit", "pr-description", "babysit"):
            with self.subTest(skill=name):
                text = self.read(f"{name}/SKILL.md")
                self.assertTrue(text.startswith(f"---\nname: {name}\n"))
                self.assertLessEqual(len(text.splitlines()), 200)
                self.assertIn(f"[{name}]({name}/SKILL.md)", readme)

    def test_mode_routes_precede_normal_open_gate(self):
        text = self.read("babysit/SKILL.md")
        self.assertLess(text.index("## Mode"), text.index("## 1. Resolve the PR (normal mode only)"))
        for row in (
            "| Normal | OPEN PR and approved contract |",
            "| Review-only | Explicit review request, OPEN or CLOSED PR |",
            "| Closed correction | CLOSED PR and explicit edit, commit, and push authorization |",
        ):
            self.assertIn(row, text)
        self.assertIn("instead of §§0–7", text)
        self.assertIn("MERGED PRs are outside this mode", text)

    def test_closed_correction_gates(self):
        self.assertEqual(missing_gates(self.read("babysit/references/closed-correction.md"), CLOSED_GATES), [])

    def test_publication_preflight_gates(self):
        self.assertEqual(missing_gates(self.read("pr-description/references/publication-preflight.md"), PREFLIGHT_GATES), [])

    def test_negative_controls_detect_removed_closed_gates(self):
        text = self.read("babysit/references/closed-correction.md")
        for name, pattern in CLOSED_GATES.items():
            with self.subTest(gate=name):
                mutated = re.sub(pattern, "REMOVED", text, count=1, flags=re.S)
                self.assertIn(name, missing_gates(mutated, CLOSED_GATES))

    def test_negative_controls_detect_removed_preflight_gates(self):
        text = self.read("pr-description/references/publication-preflight.md")
        for name, pattern in PREFLIGHT_GATES.items():
            with self.subTest(gate=name):
                mutated = re.sub(pattern, "REMOVED", text, count=1, flags=re.S)
                self.assertIn(name, missing_gates(mutated, PREFLIGHT_GATES))

    def test_commit_artifact_report_and_push_permission(self):
        text = self.read("commit/SKILL.md")
        for phrase in (
            "repository, branch, commit SHA, and uncommitted remainder",
            "Mark uncommitted concerns `NOT COMMITTED`",
            "A push restriction does not prohibit an authorized commit",
            "each node's validator result",
        ):
            self.assertIn(phrase, text)

    def test_shared_checker_contract(self):
        for path in (
            "commit/references/stack-verification.md",
            "pr-description/references/publication-preflight.md",
            "babysit/references/closed-correction.md",
        ):
            with self.subTest(reference=path):
                text = self.read(path)
                self.assertIn("~/Github/agentic-workflow-framework/skills/agentic-workflow/scripts/evidence.py check <manifest.json> --json", text)
                self.assertIn("Exit 0 means `PASS`. Exit 1 means `FAIL`. Exit 2 means `UNVERIFIED`.", text)
                self.assertIn("split-pr-stack", text)
                self.assertIn("each node's", text)
                self.assertIn("separate index", text)
                self.assertIn("~/Github/agentic-workflow-framework/skills/agentic-workflow/references/evidence.md", text)
                self.assertNotIn("Rocket.Chat", text)

    def test_thread_resolution_source_of_truth_and_approval(self):
        text = self.read("babysit/SKILL.md")
        self.assertIn("existing sequential thread-resolution reference as the source of truth", text)
        canonical = self.read("babysit/references/thread-resolution.md")
        self.assertIn("Finish each PR's source checks, resolutions, and readback before the next PR", canonical)
        self.assertIn("A new comment needs approval of its exact text before posting", canonical)
        pr = self.read("pr-description/SKILL.md")
        self.assertIn("Show the user the exact title and body, and wait for explicit approval", pr)
        self.assertIn("Stop if they changed", pr)


if __name__ == "__main__":
    unittest.main()
