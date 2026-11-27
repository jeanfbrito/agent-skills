"""The loop requires a GitNexus index of its checkout: state.py lock, brief and index."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).parent
STATE = [sys.executable, str(HERE / "state.py")]
JOURNAL = """# Loop

## Setup

- Project: demo
{setup}
## Gap matrix

| Item | Done when | Status |
| --- | --- | --- |
| R1 search | A search returns in 1 s. | partial |
"""
FAKE = '''#!/usr/bin/env python3
"""A stand-in for the gitnexus CLI (1.6.12 output shapes), so that no test indexes a checkout or registers it."""
import json, os, subprocess, sys
args = sys.argv[1:]
if os.environ.get("FAKE_GITNEXUS_LOG"):
    with open(os.environ["FAKE_GITNEXUS_LOG"], "a") as fh:
        fh.write(" ".join(args) + "\\n")
log = open(os.environ["FAKE_GITNEXUS_LOG"]).read() if os.environ.get("FAKE_GITNEXUS_LOG") else ""
if args[0] == "analyze":
    fail = os.environ.get("FAKE_GITNEXUS_FAIL", "")
    if fail == "collision" and "remove --force /gone/app-wt" not in log:
        sys.exit('Registry name "app@app-wt" is already used by "/gone/app-wt".\\nPass --name <alias> to register it.')
    if fail == "all" or (fail == "plain" and "--force" not in args) or (fail == "untilclean" and "clean" not in log):
        sys.exit("boom: the index is locked")
    top = next(a for a in args[1:] if a.startswith("/"))
    head = subprocess.run(["git", "-C", top, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    os.makedirs(os.path.join(top, ".gitnexus"), exist_ok=True)
    with open(os.path.join(top, ".gitnexus", "gitnexus.json"), "w") as fh:
        json.dump({"lastCommit": head}, fh)
    if os.environ.get("FAKE_GITNEXUS_TOUCH"):
        with open(os.path.join(top, os.environ["FAKE_GITNEXUS_TOUCH"]), "w") as fh:
            fh.write("generated\\n")
elif args[0] == "cypher":
    print("  GitNexus Cypher (1.6.12)")
    print(os.environ.get("FAKE_GITNEXUS_FILES" if "RETURN f.filePath" in args[-1] else "FAKE_GITNEXUS_COUPLING", "[]"))
'''
NO_GITNEXUS = {"AWESOMENESS_GITNEXUS": "", "PATH": "/usr/bin:/bin"}
AGENT = "claude"  # state.py finds the agent session by this process name (AGENT_NAMES)


def write_fake_gitnexus(folder):
    path = Path(folder) / "gitnexus"
    path.write_text(FAKE)
    path.chmod(0o755)
    return str(path)


def isolated_gitnexus():
    """Point the code under test at the stand-in CLI and a scratch scope folder. Returns the cleanup.
    Every test module that runs lock or note calls it: the real gitnexus would index and register each temp repo."""
    tmp = tempfile.mkdtemp()
    patch = mock.patch.dict(os.environ, {"AWESOMENESS_GITNEXUS": write_fake_gitnexus(tmp),
                                         "GITNEXUS_SCOPE_DIR": os.path.join(tmp, "scope")})
    patch.start()
    return lambda: (patch.stop(), shutil.rmtree(tmp, ignore_errors=True))


class IndexTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(os.path.realpath(tmp.name))
        self.repo = base / "app"
        (self.repo / "docs").mkdir(parents=True)
        self.journal()
        (self.repo / ".gitignore").write_text(".localdev/\n")
        self.git("init", "-q", "-b", "main")
        self.git("add", ".")
        self.git("commit", "-qm", "start")
        self.log = base / "calls.log"
        self.scope = base / "scope"
        self.env = {**os.environ, "AWESOMENESS_GITNEXUS": write_fake_gitnexus(base), "FAKE_GITNEXUS_LOG": str(self.log),
                    "GITNEXUS_SCOPE_DIR": str(self.scope)}
        self.agent = base / AGENT  # a shell named like the agent, so that the scope marks have a known pid
        self.agent.symlink_to("/bin/sh")

    def journal(self, setup=""):
        (self.repo / "docs/awesomeness-loop.md").write_text(JOURNAL.format(setup=setup))

    def git(self, *args):
        r = subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=t", "-c", "user.email=t@t", *args],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def state(self, *args, project=None, **env):
        return subprocess.run(STATE + [*args, "--project", str(project or self.repo)], capture_output=True, text=True,
                              env={**self.env, **env})

    def as_agent(self, script, **env):
        """Run a shell script under a process named like the agent. It prints the agent pid first."""
        r = subprocess.run([str(self.agent), "-c", f"echo $$; {script}"], capture_output=True, text=True,
                           env={**self.env, **env})
        pid, _, out = r.stdout.partition("\n")
        return pid.strip(), out

    def marks(self, pid):
        path = self.scope / f"{pid}.json"
        return json.loads(path.read_text()) if path.exists() else {}

    def lock(self, **env):
        self.state("unlock", "--orphan")
        self.assertEqual(self.state("arm", "--row", "R1 search", "--target", "t", "--check", "c").returncode, 0)
        return self.state("lock", **env)

    def analyses(self):
        return self.log.read_text().count("analyze") if self.log.exists() else 0

    def test_lock_refuses_a_loop_with_no_gitnexus(self):
        r = self.lock(**NO_GITNEXUS)
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("needs a GitNexus index", r.stdout)
        self.assertFalse((self.repo / ".localdev/awesomeness/lock").exists())
        self.assertIn("INDEX: REQUIRED", self.state("brief", **NO_GITNEXUS).stdout)

    def test_a_setup_line_with_a_reason_runs_the_loop_with_no_index(self):
        self.journal("- GitNexus: none (no parser for this language)\n")
        r = self.lock(**NO_GITNEXUS)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertNotIn("INDEX", r.stdout)
        self.assertIn("INDEX: off (none (no parser for this language))", self.state("brief", **NO_GITNEXUS).stdout)

    def test_lock_brings_the_index_to_head(self):
        self.assertIn("INDEX: missing", self.state("brief").stdout)
        r = self.lock()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn(f"INDEX: GitNexus has {self.repo} at", r.stdout)
        self.assertIn("INDEX: fresh at HEAD", self.state("brief").stdout)
        self.assertEqual(self.git("status", "--porcelain"), "")  # .gitnexus/ went to .git/info/exclude
        (self.repo / "a.txt").write_text("a\n")
        self.git("add", "a.txt")
        self.git("commit", "-qm", "a")
        self.assertIn("INDEX: behind HEAD", self.state("brief").stdout)
        self.assertEqual(self.lock().returncode, 0)
        self.assertEqual(self.state("index").returncode, 0)
        self.assertEqual(self.analyses(), 2)  # an index at HEAD is not built again

    def test_a_linked_worktree_gets_a_name_of_its_own(self):
        tree = self.repo.parent / "app-wt"
        self.git("worktree", "add", "-q", "-b", "loop", str(tree))
        self.assertEqual(self.state("index", project=tree).returncode, 0)
        self.assertIn("--name app@app-wt", self.log.read_text())  # the main checkout's name would break lookups
        self.assertEqual(self.state("index").returncode, 0)
        self.assertNotIn("--name", self.log.read_text().splitlines()[-1])

    def test_a_broken_index_is_the_first_chore_until_it_works(self):
        r = self.lock(FAKE_GITNEXUS_FAIL="all")
        self.assertEqual(r.returncode, 0, r.stdout)  # the cycle runs, and its first job is the index
        self.assertIn("INDEX-BROKEN: gitnexus analyze failed: exit 1: boom: the index is locked", r.stdout)
        self.assertIn("    - INDEX-BROKEN", self.state("brief").stdout)
        self.assertEqual(self.state("index", FAKE_GITNEXUS_FAIL="all").returncode, 1)
        self.assertEqual(self.state("index").returncode, 0)
        self.assertNotIn("INDEX-BROKEN", self.state("brief").stdout)

    def test_a_failed_update_gets_one_full_rebuild(self):
        r = self.state("index", FAKE_GITNEXUS_FAIL="plain")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("--force", self.log.read_text())

    def test_a_name_left_by_a_removed_checkout_is_freed(self):
        tree = self.repo.parent / "app-wt"
        self.git("worktree", "add", "-q", "-b", "loop", str(tree))
        r = self.state("index", project=tree, FAKE_GITNEXUS_FAIL="collision")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("remove --force /gone/app-wt", self.log.read_text())
        self.assertNotIn("--force\n", self.log.read_text())  # no rebuild was needed

    def test_a_rebuild_from_nothing_is_the_last_repair(self):
        r = self.state("index", FAKE_GITNEXUS_FAIL="untilclean")
        self.assertEqual(r.returncode, 0, r.stdout)
        calls = self.log.read_text().splitlines()
        self.assertEqual([c.split()[0] for c in calls], ["analyze", "analyze", "clean", "analyze"])

    def test_a_commit_note_indexes_the_task_worktree(self):
        self.state("unlock", "--orphan")
        self.state("arm", "--row", "R1 search", "--target", "t", "--check", "c")
        task = self.repo.parent / "app-task"
        self.git("worktree", "add", "-q", "-b", "fix/1", str(task))
        (task / "b.txt").write_text("b\n")
        subprocess.run(["git", "-C", str(task), "add", "b.txt"])
        subprocess.run(["git", "-C", str(task), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "b"])
        sha = subprocess.run(["git", "-C", str(task), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        pid, out = self.as_agent(
            f"{sys.executable} {HERE / 'state.py'} lock --project {self.repo} && "
            f"{sys.executable} {HERE / 'state.py'} note pick x --row 'R1 search' --mode gap --why w --target t --check c "
            f"--project {self.repo} && "
            f"{sys.executable} {HERE / 'state.py'} note commit 'fix b' --commit {sha} --project {self.repo} && "
            f"cat {self.scope}/$$.json")
        self.assertIn(f"INDEX: GitNexus has {task} at {sha[:9]}", out)
        self.assertIn(f"analyze --index-only {task} --name app@app-task", self.log.read_text())
        self.assertIn(f'"{task}"', out)  # the hook now fills this checkout for the session

    def test_the_lock_tells_the_hook_which_checkout_the_cycle_uses(self):
        self.state("arm", "--row", "R1 search", "--target", "t", "--check", "c")
        lock = HERE / "state.py"
        pid, out = self.as_agent(f"{sys.executable} {lock} lock --project {self.repo} >/dev/null && cat {self.scope}/$$.json")
        self.assertEqual(json.loads(out), {str(self.repo / ".localdev/awesomeness/lock"): str(self.repo)})
        token = json.loads((self.repo / ".localdev/awesomeness/lock").read_text())["token"]
        self.as_agent(f"{sys.executable} {lock} unlock --token {token} --project {self.repo}")
        self.assertEqual(self.marks(pid), {})

    def test_an_index_that_changes_the_checkout_is_broken(self):
        r = self.state("index", FAKE_GITNEXUS_TOUCH="CLAUDE.md")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("changed the checkout: ?? CLAUDE.md", r.stdout)
        self.assertIn("    - INDEX-BROKEN", self.state("brief").stdout)


if __name__ == "__main__":
    unittest.main()
