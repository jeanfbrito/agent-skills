#!/usr/bin/env python3
"""Run lanes: several serial awesomeness loops of one project at the same time.

A lane is the normal loop, unchanged, in its own git worktree. `.localdev/` does
not follow worktrees, so each lane gets its own data root: lock, trail, armed
goal and report. Its journal copy is on its own branch. This tool adds only the
parts that the lanes share (references/lanes.md):

  lanes.py add  --project PARENT --lane NAME [--path DIR] [--allow-chores]
      Fork a lane from the worktree of the parent loop: a worktree and a branch
      from the parent's HEAD, a copy of the parent's trail (its history and its
      DO NOT RETRY notes), and lane.json. A PAUSE of the parent loop stops every
      lane, because state.py reads lane.json. Refused while the parent has DO
      FIRST chores, because each lane would do them again. Refused while the
      parent has an armed goal. After the fork, state.py arm refuses in the parent.
  lanes.py arm  --project LANE --row ROW --mode MODE --target T --check C
      state.py arm, but refused when another lane of the same parent owns the
      row. A lane owns each row that it armed, or wrote a note on, after the fork.
      A review cycle (--mode review) is free: each lane has its own review.
  lanes.py retire --project LANE [--keep-worktree]
      End a lane: copy its data root (trail, report) into the parent's
      lanes/NAME/, remove its GitNexus index and registry entry, then remove
      the worktree (git worktree remove, never forced). Its branch keeps its
      journal. Refused while the lane has an open cycle or a lock.
  lanes.py gate --project REPO --base REF --ref REF --against REF [...] [--no-graph]
      Before a merge: text conflicts (git merge-tree), files that both sides
      change, and files that call or import each other. For the last part, it
      brings the GitNexus index of each side's worktree to HEAD and queries
      both. Exit 0 clean, 1 rerun the checks of both sides after the merge,
      2 resolve a product conflict first, 3 the gate failed (git, or an index
      that does not work: fix it, do not skip it).

Standard library only, plus the gitnexus CLI that the loop requires (state.py lock).
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import state  # noqa: E402

ROOT = ".localdev/awesomeness"
LOOP_DOC = re.compile(r"(^|/)docs/awesomeness-loop[^/]*\.md$")
EDGES = ["CALLS", "IMPORTS", "EXTENDS", "IMPLEMENTS", "ACCESSES"]
VERDICTS = ["clean", "rerun the checks of both sides after the merge", "resolve the product conflict first"]


def git(repo, *args, check=True):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        fail(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r


def fail(msg):
    """Exit 3: an error, not a gate verdict. sys.exit(msg) exits 1, which a gate caller reads as "rerun the checks"."""
    print(msg, file=sys.stderr)
    sys.exit(3)


def read_lane(path):
    try:
        with open(os.path.join(path, ROOT, state.LANE), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def busy(root):
    """An open cycle, a lock, or a goal armed for the next cycle: the loop runs, or is about to."""
    trail = state.read_trail(root)
    return state.open_cycle(trail) or os.path.exists(os.path.join(root, "lock")) or state.armed_goal(root, trail)


def parent_chores(parent):
    """The DO FIRST lines of the parent's brief. A lane forked now does each one again (trial 2026-11-27)."""
    out = subprocess.run([sys.executable, os.path.join(HERE, "state.py"), "brief", "--project", parent],
                         capture_output=True, text=True).stdout.splitlines()
    start = next((i + 1 for i, l in enumerate(out) if l.strip().startswith("DO FIRST")), len(out))
    chores = []
    for line in out[start:]:
        if not line.startswith("    - "):
            break
        chores.append(line[6:])
    return chores


def add(a):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", a.lane):
        print("REFUSED: a lane name uses lowercase letters, digits and hyphens.")
        return 2
    parent = os.path.realpath(a.project)
    proot = os.path.join(parent, ROOT)
    if read_lane(parent):
        print("REFUSED: this worktree is a lane. Fork lanes from the parent loop.")
        return 2
    if busy(proot):
        print("REFUSED: the parent loop has an open cycle, a lock or an armed goal. A lane must not inherit "
              "an open cycle, and the parent must not run next to its lanes: let it end first.")
        return 2
    chores = parent_chores(parent)
    if chores and not a.allow_chores:
        print("REFUSED: the parent has DO FIRST chores. Each lane would do them again, and the journals of the "
              "lanes would then conflict. Clear them in one parent cycle first, or pass --allow-chores:")
        for c in chores:
            print(f"  - {c[:140]}")
        return 2
    branch = git(parent, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if branch == "HEAD":
        print("REFUSED: the parent worktree has no branch (detached HEAD).")
        return 2
    dirty = git(parent, "status", "--porcelain", "--", "docs").stdout.splitlines()
    if any(LOOP_DOC.search(l[3:].strip()) for l in dirty):
        print("REFUSED: the loop docs of the parent have changes that are not committed. Commit them first, "
              "so that each lane starts from them.")
        return 2
    path = os.path.abspath(a.path or f"{parent}-lane-{a.lane}")
    new_branch = f"{branch}-lane-{a.lane}"
    git(parent, "worktree", "add", "-b", new_branch, path, "HEAD")
    path = os.path.realpath(path)
    root = os.path.join(path, ROOT)
    os.makedirs(root, exist_ok=True)
    for name in (state.TRAIL, "auto-hold.json"):
        if os.path.exists(os.path.join(proot, name)):
            shutil.copy2(os.path.join(proot, name), os.path.join(root, name))
    trail = state.read_trail(proot)
    lane = {"lane": a.lane, "parent": parent, "parent_root": proot, "branch": new_branch,
            "forked_at": git(parent, "rev-parse", "HEAD").stdout.strip(),
            "forked_cycle": max((e.get("cycle", 0) for e in trail), default=0)}
    with open(os.path.join(root, state.LANE), "w", encoding="utf-8") as fh:
        json.dump(lane, fh, indent=1)
    print(f"LANE {a.lane}: {path} on {new_branch}, forked from {branch} after cycle {lane['forked_cycle']}.")
    print(f"Fill the cycle prompt's {{project}} with {path}.")
    return 0


def owned_rows(root, lane):
    """The rows that a lane armed, or wrote a note on, after its fork."""
    trail = state.read_trail(root)
    rows = {state.norm(e.get("row", "")) for e in trail if e.get("cycle", 0) > lane.get("forked_cycle", 0)}
    goal = state.armed_goal(root, trail)
    if goal:
        rows.add(state.norm(goal.get("row", "")))
    rows.discard("")
    return rows


def arm(a):
    path = os.path.realpath(a.project)
    me = read_lane(path)
    if not me:
        print("REFUSED: this worktree is not a lane (it has no lane.json). Use state.py arm.")
        return 2
    if busy(me["parent_root"]):
        print("REFUSED: the parent loop runs a cycle. A parent and its lanes do not run at the same time.")
        return 2
    row = state.norm(a.row)
    own = os.path.realpath(os.path.join(path, ROOT))
    # Every review cycle uses the row `review` (references/review-prompt.md), and each lane has its own review.
    siblings = [] if a.mode == "review" else state.lanes_of(path, me["parent_root"])
    for lane_root, lane in siblings:
        if os.path.realpath(lane_root) != own and row in owned_rows(lane_root, lane):
            print(f"REFUSED: lane {lane.get('lane', '?')} owns row '{a.row}'. Arm another row.")
            return 2
    cmd = [sys.executable, os.path.join(HERE, "state.py"), "arm", "--project", path,
           "--row", a.row, "--target", a.target or "", "--check", a.check or ""]
    if a.mode:
        cmd += ["--mode", a.mode]
    return subprocess.run(cmd).returncode


def retire(a):
    path = os.path.realpath(a.project)
    me = read_lane(path)
    if not me:
        print("REFUSED: this worktree is not a lane (it has no lane.json).")
        return 2
    root = os.path.join(path, ROOT)
    if state.open_cycle(state.read_trail(root)) or os.path.exists(os.path.join(root, "lock")):
        print("REFUSED: the lane has an open cycle or a lock. Let its cycle end first.")
        return 2
    if not a.keep_worktree and git(path, "status", "--porcelain").stdout.strip():
        print("REFUSED: the lane worktree has changes that are not committed. Commit them, or pass --keep-worktree.")
        return 2
    keep = os.path.join(me["parent_root"], "lanes", me["lane"])
    shutil.copytree(root, keep, ignore=shutil.ignore_patterns("lock", state.LANE), dirs_exist_ok=True)
    exe = state.gitnexus_cmd()
    if exe:
        r = subprocess.run([exe, "remove", "--force", path], capture_output=True, text=True)
        if r.returncode != 0:
            fail(f"gitnexus remove failed for {path}: {(r.stderr or r.stdout).strip()[:200]}")
    if a.keep_worktree:
        os.remove(os.path.join(root, state.LANE))
    else:
        git(me["parent"], "worktree", "remove", path)
    print(f"RETIRED lane {me['lane']}: its trail and report are in {keep}. Branch {me['branch']} keeps its journal: "
          "copy the status changes of its rows into the parent's journal.")
    return 0


def changed(repo, base, ref):
    names = git(repo, "diff", "--name-only", f"{base}...{ref}").stdout.splitlines()
    return {f for f in names if f and not LOOP_DOC.search(f)}


def lit(items):
    return "[" + ",".join("'" + i.replace("\\", "\\\\").replace("'", "\\'") + "'" for i in sorted(items)) + "]"


def graph(repo, query):
    """The rows of a GitNexus Cypher query, as lists of cells, and "" or the reason that it gave none."""
    exe = state.gitnexus_cmd()
    if not exe:
        return None, "gitnexus is not installed"
    try:
        r = subprocess.run([exe, "cypher", "-r", repo, query], capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        return None, "gitnexus timed out"
    starts = [i for i in (r.stdout.find("{"), r.stdout.find("[")) if i >= 0]  # after the banner line
    if r.returncode != 0 or not starts:
        err = [l.strip() for l in r.stderr.splitlines() if l.strip() and not l.strip().startswith("at ")]
        return None, f"gitnexus failed for {repo}: {(err or ['no output'])[0][:160]}"
    try:
        data = json.loads(r.stdout[min(starts):])
    except ValueError:
        return None, "gitnexus gave output that this tool cannot read"
    if isinstance(data, list):  # a query with no rows prints []
        return [[str(v) for v in d.values()] for d in data if isinstance(d, dict)], ""
    md = data.get("markdown") if isinstance(data, dict) else None
    if not isinstance(md, str):
        return None, f"gitnexus gave no rows: {str(data)[:160]}"
    lines = [l for l in md.splitlines() if l.strip().startswith("|")]
    return [[c.strip() for c in l.strip().strip("|").split("|")] for l in lines[2:]], ""


def checkouts(repo):
    """{branch: worktree} for each branch that a worktree has checked out."""
    out, tree = {}, None
    for line in git(repo, "worktree", "list", "--porcelain").stdout.splitlines():
        if line.startswith("worktree "):
            tree = line[len("worktree "):]
        elif line.startswith("branch refs/heads/"):
            out[line[len("branch refs/heads/"):]] = tree
    return out


def coupling(trees, mine, theirs):
    """(changed files that an index has, coupled rows): each side's index holds its own new files and edges."""
    for tree in trees:
        err = state.ensure_index(tree)
        if err:
            fail(f"the GitNexus index of {tree} does not work: {err}. Fix it (state.py index --project {tree}).")
    seen, rows_out = set(), set()
    left, right = mine - theirs, theirs - mine
    for tree in trees:
        rows, why = graph(tree, f"MATCH (f:File) WHERE f.filePath IN {lit(mine | theirs)} RETURN f.filePath")
        if rows is None:
            fail(f"the GitNexus query failed: {why}")
        seen |= {r[0] for r in rows if r}
        if left and right:
            rows, why = graph(tree, (
                f"WITH {lit(left)} AS a, {lit(right)} AS b MATCH (s1)-[r:CodeRelation]->(s2) "
                f"WHERE r.type IN {lit(EDGES)} AND ((s1.filePath IN a AND s2.filePath IN b) "
                "OR (s1.filePath IN b AND s2.filePath IN a)) "
                "RETURN DISTINCT s1.filePath AS src, s2.filePath AS dst, r.type AS rel ORDER BY src, dst"))
            if rows is None:
                fail(f"the GitNexus coupling query failed: {why}")
            rows_out |= {tuple(r) for r in rows if len(r) == 3}
    return seen, sorted(rows_out)


def gate(a):
    repo = os.path.realpath(a.project)
    trees = checkouts(repo)
    if not a.no_graph:
        missing = [r for r in [a.ref, *a.against] if r not in trees]
        if missing:
            fail(f"no worktree has {', '.join(missing)} checked out. The gate reads the GitNexus index of each "
                 "side's worktree: give the branch one (git worktree add <path> <branch>), or pass a branch name.")
    mine = changed(repo, a.base, a.ref)
    worst = 0
    for other in a.against:
        theirs = changed(repo, a.base, other)
        print(f"GATE {a.ref} vs {other}: {len(mine)} and {len(theirs)} changed files since {a.base}")
        r = git(repo, "merge-tree", "--write-tree", "--name-only", "--no-messages", a.ref, other, check=False)
        if r.returncode not in (0, 1):
            fail(f"git merge-tree failed: {r.stderr.strip()}")
        conflicts = [l for l in r.stdout.splitlines()[1:] if l.strip()]
        product = [f for f in conflicts if not LOOP_DOC.search(f)]
        shared = sorted(mine & theirs)
        for f in product:
            print(f"  CONFLICT {f}: resolve it before the merge")
        for f in conflicts:
            if LOOP_DOC.search(f):
                print(f"  LOOP-DOC {f}: each lane keeps its own copy; do not merge it")
        for f in shared:
            print(f"  SHARED {f}: both sides change it")
        coupled = []
        if a.no_graph:
            print("  GRAPH: off (--no-graph)")
        else:
            seen, coupled = coupling([trees[a.ref], trees[other]], mine, theirs)
            print(f"  GRAPH: the indexes of both sides have {len(seen)} of {len(mine | theirs)} changed files. "
                  "A file that no index has (a doc, a config) has unknown coupling.")
            for src, dst, rel in coupled:
                print(f"  COUPLED {src} -> {dst} ({rel})")
        verdict = 2 if product else 1 if shared or coupled else 0
        print(f"  VERDICT: {VERDICTS[verdict]}")
        worst = max(worst, verdict)
    return worst


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("add", help="fork a lane from the parent loop")
    p.add_argument("--project", required=True, help="the worktree of the parent loop")
    p.add_argument("--lane", required=True)
    p.add_argument("--path", help="the new worktree (default: <parent>-lane-<lane>)")
    p.add_argument("--allow-chores", action="store_true", help="fork although the parent has DO FIRST chores")
    p = sub.add_parser("arm", help="state.py arm, refused for a row that another lane owns")
    p.add_argument("--project", required=True, help="the worktree of the lane")
    p.add_argument("--row", required=True)
    p.add_argument("--mode")
    p.add_argument("--target")
    p.add_argument("--check")
    p = sub.add_parser("retire", help="end a lane: keep its trail, remove its index and worktree")
    p.add_argument("--project", required=True, help="the worktree of the lane")
    p.add_argument("--keep-worktree", action="store_true", help="keep the worktree; remove only lane.json and the index")
    p = sub.add_parser("gate", help="check a merge between lanes or task branches")
    p.add_argument("--project", required=True, help="any worktree of the repo")
    p.add_argument("--base", required=True, help="the branch that both sides started from")
    p.add_argument("--ref", required=True, help="the branch to merge")
    p.add_argument("--against", action="append", required=True, help="a branch of another lane (repeat)")
    p.add_argument("--no-graph", action="store_true", help="git only, for a loop with '- GitNexus: none' in Setup")
    a = ap.parse_args()
    return {"add": add, "arm": arm, "retire": retire, "gate": gate}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
