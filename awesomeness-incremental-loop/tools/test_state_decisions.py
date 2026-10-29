"""Regression checks that keep each loop decision reviewable: the design record, its acks, and the PR split plan."""

import contextlib
import importlib.util
import io
import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


SCRIPT = Path(__file__).with_name("state.py")
spec = importlib.util.spec_from_file_location("awesome_state_decisions", SCRIPT)
state = importlib.util.module_from_spec(spec)
spec.loader.exec_module(state)

JOURNAL = """# Loop

## Setup

- Project: demo
{setup}

## Direction

- Product focus: Find old encrypted messages.

## Gap matrix

| Item | Done when | Status |
| --- | --- | --- |
| Local search | A query returns old messages. | partial |

{extra}
"""

RECORD = """# Design record

### R1 · Backfill pace · proposed

- Question: How fast does the history backfill run?
- Options:
  1. **One page each 12 s**: for a calm server load; against a slow first index
  2. As fast as possible: for a quick index; against the server load
- Choice: one page each 12 s
- Why: the server team asked for a calm, steady load
- Evidence: load test in cycle 40
- Kind: configurable (setting `E2E_Search_Backfill_Interval`, default 12 s)
- Validate with: infra, product
- Commits: {commits}
- Decided by: loop cycle 40
- Validation:
"""

GIT_ENV = dict(os.environ, GIT_AUTHOR_NAME="loop", GIT_AUTHOR_EMAIL="loop@example.com",
               GIT_COMMITTER_NAME="loop", GIT_COMMITTER_EMAIL="loop@example.com")


def run_git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false", *args],
                          capture_output=True, text=True, check=True, env=GIT_ENV).stdout.strip()


def lines(n):
    return "".join(f"line {i}\n" for i in range(n))


class DesignRecordTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name) / "app"
        self.project.mkdir()
        run_git(self.project, "init", "-q", "-b", "main")
        self.commit(self.project, {"README.txt": "demo\n"}, "base")
        run_git(self.project, "checkout", "-q", "-b", "awesomeness/2026-10-29")
        (self.project / "docs").mkdir()
        self.root = self.project / ".localdev/awesomeness"
        self.root.mkdir(parents=True)
        self.trail = []
        self.journal()

    def journal(self, setup="", extra=""):
        (self.project / "docs/awesomeness-loop.md").write_text(JOURNAL.format(setup=setup, extra=extra))

    def record(self, body):
        (self.project / "docs/awesomeness-loop-design-record.md").write_text(body)

    def commit(self, repo, files, message):
        for name, body in files.items():
            path = Path(repo) / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body)
        run_git(repo, "add", *files)
        run_git(repo, "commit", "-q", "-m", message)
        return run_git(repo, "rev-parse", "--short=9", "HEAD")

    def loop_commit(self, files, message, repo=None):
        sha = self.commit(repo or self.project, files, message)
        self.trail.append({"cycle": 1, "kind": "commit", "row": "Local search", "commit": sha})
        return sha

    def args(self, **kw):
        base = dict(project=str(self.project), journal="docs/awesomeness-loop.md", root=".localdev/awesomeness",
                    stale_min=90, drift_depth=0)
        base.update(kw)
        return SimpleNamespace(**base)

    def brief(self):
        (self.root / "trail.jsonl").write_text("".join(json.dumps(e) + "\n" for e in self.trail))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(state.brief(self.args()), 0)
        return out.getvalue()

    def test_contract_commit_without_a_record_is_a_chore(self):
        """Catches the E2EE handover: contract commits shipped with their decisions only in prose."""
        sha = self.loop_commit({"src/settings/backfill.ts": "export const pace = 12;\n"}, "feat: backfill pace")
        text = self.brief()
        self.assertIn("UNRECORDED-DECISION: 1 loop commit(s)", text)
        self.assertIn(sha, text)
        self.assertIn("does not exist", text)
        self.assertIn(sha, json.loads((self.root / "commit-files.json").read_text()))

    def test_record_that_lists_the_commit_clears_it(self):
        sha = self.loop_commit({"src/settings/backfill.ts": "export const pace = 12;\n"}, "feat: backfill pace")
        self.record(RECORD.format(commits=sha))
        text = self.brief()
        self.assertNotIn("UNRECORDED-DECISION", text)
        self.assertNotIn("RECORD-INCOMPLETE", text)
        self.assertIn("DESIGN RECORD: 1 decision(s) (1 proposed; 1 configurable)", text)
        self.assertIn("infra 1, product 1", text)

    def test_ack_clears_a_commit_that_decides_nothing(self):
        sha = self.loop_commit({"src/settings/backfill.ts": "export const pace = 12;\n"}, "refactor: move pace")
        self.trail.append({"cycle": 1, "kind": "ack", "decision": sha, "text": "no new decision: same default"})
        self.assertNotIn("UNRECORDED-DECISION", self.brief())

    def test_note_ack_needs_a_reason_and_full_shas(self):
        sha = self.loop_commit({"src/ipc/channels.ts": "export {};\n"}, "feat: channel")
        (self.root / "trail.jsonl").write_text(json.dumps(self.trail[0]) + "\n")
        common = dict(drift=None, row=None, mode=None, why=None, metric=None, file=None, commit=None, blocker=None,
                      status=None, progress=None, next=None)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(state.note(self.args(rest=["ack"], decision=sha, **common)), 2)
            why = ["ack", "no new decision: renames the channel constant only"]
            self.assertEqual(state.note(self.args(rest=why, decision="abc", **common)), 2)
            self.assertEqual(state.note(self.args(rest=why, decision="zzzzzzz", **common)), 2)
            self.assertEqual(state.note(self.args(rest=["ack", "x"], decision=sha, **common)), 2)
            self.assertEqual(state.note(self.args(rest=["ack", "no new decision: ok"], decision=sha, **common)), 2)
            self.assertEqual(state.note(self.args(rest=why, decision=",".join([sha] * 6), **common)), 2)
            self.assertEqual(state.note(self.args(rest=why, decision=sha.upper(), **common)), 0)
        last = json.loads((self.root / "trail.jsonl").read_text().splitlines()[-1])
        self.assertEqual(last["decision"], sha)

    def test_ui_commit_is_not_a_contract_surface(self):
        self.loop_commit({"src/ui/SearchBox.tsx": "export {};\n", "src/settings/SearchBox.spec.ts": "test\n"}, "feat: box")
        self.assertNotIn("UNRECORDED-DECISION", self.brief())

    def test_journal_surfaces_add_and_remove_paths(self):
        self.journal(extra="## Contract surfaces\n\n| Pattern | What it decides | Validate with |\n| --- | --- | --- |\n"
                           "| `src/store/*.ts` | the stored index format | security |\n"
                           "| `!src/settings/labels.ts` | display text only | - |\n")
        store = self.loop_commit({"src/store/index.ts": "export {};\n"}, "feat: index format")
        labels = self.loop_commit({"src/settings/labels.ts": "export {};\n"}, "chore: label text")
        text = self.brief()
        self.assertIn(store, text)
        self.assertNotIn(labels, text)

    def test_incomplete_record_is_a_chore(self):
        sha = self.loop_commit({"src/settings/cap.ts": "export const cap = 200000;\n"}, "feat: index cap")
        self.record("### R2 · Index cap · validated\n\n- Question: How many messages does the index keep?\n"
                    f"- Choice: 200000\n- Kind: maybe\n- Commits: {sha}\n")
        text = self.brief()
        self.assertIn("RECORD-INCOMPLETE", text)
        for missing in ("Options", "Why", "Validate with", "fixed or configurable", "Validation (who, when)"):
            self.assertIn(missing, text)

    def test_format_example_in_a_code_block_is_not_an_entry(self):
        sha = self.loop_commit({"src/settings/backfill.ts": "export const pace = 12;\n"}, "feat: backfill pace")
        self.record("# Design record\n\n```markdown\n### R<n> · <title> · proposed\n```\n\n" + RECORD.format(commits=sha))
        self.assertIn("DESIGN RECORD: 1 decision(s)", self.brief())

    def test_big_branch_without_a_plan_is_a_chore(self):
        """Catches the 149-file, 16533-line PR that reviewers could not agree with at once."""
        self.loop_commit({"src/search/engine.ts": lines(1200)}, "feat: search engine")
        text = self.brief()
        self.assertIn("PR-SPLIT: app has loop work too big to review as one PR, against main", text)
        self.assertIn("'awesomeness/2026-10-29' 1200 lines in 1 files", text)

    def test_pr_plan_that_names_the_branch_clears_it(self):
        self.journal(extra="## PR plan\n\n| PR | Branch | Carries |\n| --- | --- | --- |\n"
                           "| - | `awesomeness/2026-10-29` | integration and demo only, not for review |\n")
        self.loop_commit({"src/search/engine.ts": lines(1200)}, "feat: search engine")
        self.assertNotIn("PR-SPLIT", self.brief())

    def test_lockfiles_and_loop_docs_do_not_count_toward_pr_size(self):
        self.loop_commit({"yarn.lock": lines(5000), "docs/awesomeness-loop-notes.md": lines(900),
                          "src/search/engine.ts": lines(10)}, "feat: add a dependency")
        self.assertNotIn("PR-SPLIT", self.brief())

    def test_size_limit_comes_from_setup(self):
        self.journal(setup="- PR size limit: 5 lines, 40 files")
        self.loop_commit({"src/search/engine.ts": lines(10)}, "feat: search engine")
        self.assertIn("limit 5 lines or 40 files", self.brief())

    def test_merged_work_needs_no_plan(self):
        self.loop_commit({"src/search/engine.ts": lines(1200)}, "feat: search engine")
        run_git(self.project, "branch", "-f", "main", "HEAD")
        self.assertNotIn("PR-SPLIT", self.brief())

    def test_other_repos_are_checked(self):
        """Catches a cross-repo loop: the server half of the feature lived in a second repo."""
        core = Path(self.tmp.name) / "core"
        core.mkdir()
        run_git(core, "init", "-q", "-b", "main")
        self.commit(core, {"README.txt": "core\n"}, "base")
        run_git(core, "checkout", "-q", "-b", "feat/search")
        sha = self.loop_commit({"server/settings/e2e.ts": lines(1100)}, "feat: e2e search settings", repo=core)
        self.journal(setup="- Other repos: `../core`")
        text = self.brief()
        self.assertIn(sha, text)
        self.assertIn("PR-SPLIT: core has loop work", text)
        self.assertIn("'feat/search' 1100 lines", text)


    def signal_keys(self):
        return sorted(json.loads((self.root / "signals.json").read_text()))

    def test_record_written_in_the_same_commit_covers_it(self):
        """A commit cannot hold its own sha, so the record file in the same commit is the proof."""
        self.record("# Design record\n")
        sha = self.loop_commit({"src/settings/backfill.ts": "export const pace = 12;\n",
                                "docs/awesomeness-loop-design-record.md": RECORD.format(commits="this commit")},
                               "feat: backfill pace")
        text = self.brief()
        self.assertNotIn("UNRECORDED-DECISION", text)
        self.assertNotIn(sha, text)

    def test_chore_key_follows_the_oldest_unrecorded_commit(self):
        """A cycle that records the listed commits is not OVERDUE for the commits after them."""
        first = self.loop_commit({"src/settings/a.ts": "a\n"}, "feat: a")
        second = self.loop_commit({"src/settings/b.ts": "b\n"}, "feat: b")
        self.brief()
        self.assertIn(f"UNRECORDED-DECISION:{first}", self.signal_keys())
        self.record(RECORD.format(commits=first))
        self.brief()
        self.assertIn(f"UNRECORDED-DECISION:{second}", self.signal_keys())
        self.assertNotIn(f"UNRECORDED-DECISION:{first}", self.signal_keys())

    def test_copied_template_is_incomplete(self):
        sha = self.loop_commit({"src/settings/cap.ts": "export const cap = 1;\n"}, "feat: cap")
        self.record("### R1 · <short title> · proposed\n\n- Question: <one sentence that ends with \"?\">\n"
                    "- Options:\n  1. **<chosen option>**: for <...>; against <...>\n  2. <other option>: for <...>\n"
                    "- Choice: <what the loop built>\n- Why: <the reason>\n- Evidence: <measure, test, live run, doc>\n"
                    "- Kind: fixed | configurable (setting `<name>`, default <value>)\n- Validate with: security\n"
                    f"- Commits: {sha}\n")
        text = self.brief()
        for missing in ("Question", "Options lists 2 or more", "Choice", "Why", "Evidence", "Kind"):
            self.assertIn(missing, text)

    def test_record_rules_from_the_format(self):
        self.record("### R1 · Cap · proposed\n\n- Question: The index cap\n- Options:\n  1. 200k\n"
                    "- Choice: 200k\n- Why: memory\n- Evidence: guess\n- Kind: configurable\n- Validate with: product\n\n"
                    "### R1 · Pace · proposed\n\n- Question: How fast?\n- Options:\n  1. Fast\n  2. Slow\n"
                    "- Choice: slow\n- Why: load\n- Evidence: guess\n- Kind: fixed\n- Validate with: infra\n")
        text = self.brief()
        for problem in ("Question ends with ?", "Options lists 2 or more", "Kind names the setting and its default",
                        "Options marks the chosen one in bold", "R1: the number is used 2 times"):
            self.assertIn(problem, text)

    def test_other_headings_and_tilde_fences_are_not_records(self):
        sha = self.loop_commit({"src/settings/backfill.ts": "export const pace = 12;\n"}, "feat: backfill pace")
        self.record("# Design record\n\n### How to read this\n\nText.\n\n~~~markdown\n### R99 · x · proposed\n~~~\n\n"
                    + RECORD.format(commits=sha))
        text = self.brief()
        self.assertIn("DESIGN RECORD: 1 decision(s)", text)
        self.assertNotIn("RECORD-INCOMPLETE", text)

    def test_default_words_and_files(self):
        match = state.surface_matcher([])
        for path in ("src/search/lifecycle.ts", "src/search/fileStore.ts", "package.json", "src/search/indexLimit.ts"):
            self.assertTrue(match(path), path)
        for path in ("src/servers/cache.ts", "src/e2eeSearch/keyStore.ts", "src/settings/backfill.ts"):
            self.assertTrue(match(path), path)
        for path in ("rollup.config.mjs", "jest.config.js", ".vscode/settings.json", "src/ui/SearchBox.tsx",
                     "src/ui/SettingsView/features/IndexStats.tsx", "src/store/rootReducer.ts",
                     "client/views/account/security/EndToEnd.tsx"):
            self.assertFalse(match(path), path)
        self.assertTrue(state.surface_matcher([{"Pattern": "`rollup.config.mjs`"}])("rollup.config.mjs"))

    def test_merge_commit_files_count(self):
        run_git(self.project, "checkout", "-q", "-b", "side")
        self.commit(self.project, {"src/ipc/channels.ts": "export {};\n"}, "feat: channel")
        run_git(self.project, "checkout", "-q", "awesomeness/2026-10-29")
        run_git(self.project, "merge", "-q", "--no-ff", "-m", "merge side", "side")
        sha = run_git(self.project, "rev-parse", "--short=9", "HEAD")
        self.trail.append({"cycle": 1, "kind": "commit", "row": "Local search", "commit": sha})
        self.assertIn(sha, self.brief())

    def test_numbered_slice_past_the_limit_needs_a_reason(self):
        plan = "## PR plan\n\n| # | Repo | Branch | Carries |\n| --- | --- | --- | --- |\n| 1 | app | `awesomeness/2026-10-29` | {} |\n"
        self.journal(extra=plan.format("the whole feature"))
        self.loop_commit({"src/search/engine.ts": lines(1200)}, "feat: search engine")
        self.assertIn("PR-SPLIT: 1 numbered PR slice(s) in the PR plan are past the limit", self.brief())
        self.journal(extra=plan.format("whole: one generated worker bundle"))
        self.assertNotIn("PR-SPLIT", self.brief())

    def test_limit_with_a_thousands_comma(self):
        self.journal(setup="- PR size limit: 1,500 lines, 40 files")
        self.loop_commit({"src/search/engine.ts": lines(1200)}, "feat: search engine")
        self.assertNotIn("PR-SPLIT", self.brief())

    def test_default_branch_from_setup_wins(self):
        self.loop_commit({"src/search/engine.ts": lines(1200)}, "feat: search engine")
        run_git(self.project, "branch", "trunk", "HEAD")
        self.journal(setup="- Default branch: `trunk`")
        self.assertNotIn("PR-SPLIT", self.brief())

    def test_commit_note_asks_for_the_record_now(self):
        sha = self.commit(self.project, {"src/settings/backfill.ts": "export const pace = 12;\n"}, "feat: backfill pace")
        (self.root / "trail.jsonl").write_text(json.dumps({"cycle": 1, "kind": "pick", "row": "Local search",
                                                           "target": "t", "check": "c"}) + "\n")
        common = dict(drift=None, decision=None, row=None, mode=None, why=None, metric=None, file=None, blocker=None,
                      status=None, progress=None, next=None)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(state.note(self.args(rest=["commit", "feat: backfill pace"], commit=sha, **common)), 0)
        self.assertIn(f"RECORD-NOW: {sha}", out.getvalue())

    def test_report_shows_records_and_acks(self):
        import report
        sha = self.loop_commit({"src/settings/backfill.ts": "export const pace = 12;\n"}, "feat: backfill pace")
        self.record("# Design record\n\n### Notes\n\nText.\n\n" + RECORD.format(commits=sha))
        self.trail.append({"cycle": 2, "kind": "ack", "decision": "abcdef1", "text": "no new decision: moves a constant"})
        (self.root / "trail.jsonl").write_text("".join(json.dumps(e) + "\n" for e in self.trail))
        out = self.root / "report"
        report.build(str(self.root), str(self.project / "docs/awesomeness-loop.md"), str(out))
        data = json.loads((out / "report-data.json").read_text())
        self.assertEqual([r["id"] for r in data["design_record"]], ["R1"])
        self.assertEqual(data["decision_acks"][0]["commits"], "abcdef1")
        html = (out / "index.html").read_text()
        self.assertIn("infra · 1 to validate", html)
        self.assertIn("Acknowledged as no new decision · 1", html)


    def test_rebuilt_branch_named_in_the_plan_is_sized(self):
        """A PR slice rebuilt from the loop work has other shas and patch ids. The plan names it, so the check sizes it."""
        sha = self.loop_commit({"src/search/engine.ts": lines(1200)}, "feat: search engine")
        self.assertTrue(sha)
        run_git(self.project, "checkout", "-q", "-b", "feat/search", "main")  # rebuilt in other steps: no shared patch id
        self.commit(self.project, {"src/search/engine.ts": lines(600)}, "feat: search engine, part 1")
        self.commit(self.project, {"src/search/engine.ts": lines(1200)}, "feat: search engine, part 2")
        run_git(self.project, "checkout", "-q", "awesomeness/2026-10-29")
        plan = ("## PR plan\n\n| # | Repo | Branch | Carries |\n| --- | --- | --- | --- |\n"
                "| - | app | `awesomeness/2026-10-29` | integration and demo, not for review |\n"
                "| 1 | app | `feat/search` | {} |\n")
        self.journal(extra=plan.format("the search engine"))
        self.assertIn("app 'feat/search' 1200 lines", self.brief())
        core = Path(self.tmp.name) / "core"  # the same branch name in another repo folder of the loop
        core.mkdir()
        run_git(core, "init", "-q", "-b", "main")
        self.commit(core, {"README.txt": "core\n"}, "base")
        self.journal(setup="- Other repos: `../core`", extra=plan.format("the search engine").replace("| 1 | app |", "| 1 | core |"))
        self.assertNotIn("feat/search", self.brief())
        self.journal(extra=plan.format("whole: one engine file"))
        self.assertNotIn("PR-SPLIT", self.brief())


class PointerTest(unittest.TestCase):
    def test_brief_pointers_name_real_sections(self):
        """Catches a moved section: a brief line that sends the agent to a file or heading that does not exist."""
        skill = Path(__file__).resolve().parent.parent
        code = (skill / "tools/state.py").read_text()
        for ref in set(re.findall(r"references/[\w-]+\.md", code)):
            self.assertTrue((skill / ref).is_file(), ref)
        headings = (skill / "references/signals.md").read_text()
        for name in re.findall(r"references/signals\.md, ([\w ]+)\)", code):
            self.assertRegex(headings, rf"(?m)^## .*{re.escape(name)}", name)


if __name__ == "__main__":
    unittest.main()
