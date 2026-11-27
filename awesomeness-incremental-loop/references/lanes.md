# Lanes: forks of the loop that run at the same time

A lane is this loop, unchanged, in its own git worktree. `.localdev/` does not
follow worktrees, so each lane has its own data root: lock, trail, armed goal
and report. Its journal copy is on its own branch. The serial rules of a cycle
do not change. `tools/lanes.py` adds only what the lanes share:

| Part | Mechanism |
| --- | --- |
| Fork | `lanes.py add` makes the worktree and the branch, copies the parent's trail, and writes `lane.json` |
| One lane for each row | `lanes.py arm` refuses a row that another lane armed, or wrote a note on, after the fork. A review cycle is free: each lane has its own review |
| The parent waits | `state.py arm` refuses in a loop that has lanes, and `lanes.py add` refuses a parent with an armed goal. The parent and its lanes never work the same row |
| The brake | `state.py pause --project <parent>` stops every lane: `lock`, `arm` and `pick` read `lane.json` |
| The merge check | `lanes.py gate`: text conflicts, files that both sides change, and files that call or import each other (GitNexus, when the repo has an index) |

Use lanes only when the human asks for more speed with full cycles. They cost
one cycle on the session model for each lane, so the cost grows with the
number of lanes. Do not use lanes when most rows need the one live app (a game
editor, a single dev server). The lanes then wait for each other.

## Fork

1. Let the parent loop end its open cycle, and clear its `DO FIRST` chores
   in one parent cycle. `lanes.py add` refuses a parent with an open cycle, a
   lock, an armed goal or a chore. Each lane would continue that cycle or do
   that chore again, and an armed parent would run next to its lanes. In the 2026-11-27 trial, two lanes each wrote design-record entries
   for the same 4 commits, and their journals then conflicted.
2. Do the Start steps in the parent first, Start step 5 included. An edit to an
   ignore file that each lane makes alone causes a merge conflict
   (`.prettierignore` in the 2026-10-27 run). Commit the loop docs.
3. Write the human rules of this run in the parent's journal Setup, then
   commit. Each lane gets them at the fork. Example:
   `- Lanes 2026-11-27: no push, no PR, no issue comment. Task branches stay local.`
4. Run `lanes.py add --project <parent worktree> --lane a`. Do the same for
   `b`. Start with 2 lanes. Add a third only after both lanes run some cycles
   with no refused arm, no product conflict and no killed app.
5. Give each lane one line in its own journal Setup, and commit it on the
   lane branch:
   - Lane `a` is the live lane. It owns the dev app, the debug port and the
     rows that have a timing in their `Done when`.
   - Every other lane takes rows that it can check with no live app: unit
     tests, the type check, lint, and source reading. Write
     `- Lane: b. Do not start the dev app. Do not take a timing row.`

## Orchestrator

The orchestrator in `references/drivers.md` runs for each lane. It does not
wait for all lanes to end. When one lane's cycle ends, it continues that lane.

1. For each lane that has no cycle, run `state.py brief --project <lane>`.
   Choose a row, then run `lanes.py arm --project <lane> --row ... --mode ...
   --target ... --check ...`. A `REFUSED` line names the lane that owns the
   row. Choose another row.
2. Spawn one cycle subagent for the lane, in the background. Use the prompt in
   `references/fire-prompt.md` with `{project}` set to the lane's worktree.
3. When a cycle ends, print `lane <name> | <status line>`. Run the gate for
   the new product branch (below). Then do step 1 for that lane again.
4. Do not run `state.py lock` on a lane. The orchestrator and its cycle
   subagents share one agent pid, so the call takes over the lock of a
   cycle that runs (lesson 47). `brief` and `arm` are safe.
5. To read a brief with less context, the context-mode tools can print only
   the `LOCK`, `PAUSED`, `ARMED`, `NOW`, `ROWS`, `DIRECTION`, `DECISIONS` and
   `THIS CYCLE'S ITEM` lines. The `DO FIRST` chores are for the cycle.

Each lane has its own review every 3 cycles, critic gate, decisions file and
report. Ask the open decisions of every lane when the human comes back. Only
lane `a` does the `EXHAUSTED` procedure. Another lane with no open row ends:
do not arm it again.

## Gate and merge

Run the gate before a merge, and after a cycle that commits product code:

```sh
python3 ~/Github/agent-skills/awesomeness-incremental-loop/tools/lanes.py gate \
  --project <repo> --base <the branch both sides started from> \
  --ref <the new branch> --against <a branch of another lane> [--against ...]
```

| Line | Meaning | Do |
| --- | --- | --- |
| `CONFLICT` | Both sides change the same lines of a product file | Resolve it before the merge, then run the checks of both sides |
| `LOOP-DOC` | Both lanes change their journal or decisions file | Do not merge it. Each lane keeps its own copy |
| `SHARED` | Both sides change the file, with no conflict | Merge, then run the checks of both sides on the merged tree |
| `COUPLED` | One side changes a file that the other side's file calls or imports | Merge, then run the checks of both sides on the merged tree |
| `GRAPH` | How many changed files the index has | A file that the index does not have has unknown coupling |

- `loop-branch` mode: merge a lane's product commits into the integration
  branch only between that lane's cycles. Do not merge the loop docs. A pass
  in the lane's worktree does not count: run the checks that the gate names
  on the merged tree.
- `pr-per-task` mode: the lanes do not merge into each other. Run the gate
  for each new task branch against the open task branches of the other lanes.
  Write each `SHARED` or `COUPLED` file in the rows of both tasks. The PR that
  merges second runs its checks again on the new base.

## GitNexus

The gate uses the GitNexus index of the main checkout, if that index exists. It
sees only code that is in that checkout. A lane's new files have unknown
coupling until they land there. Reindex the main checkout at a quiet point
after a batch of merges. Never run `gitnexus analyze` inside a lane worktree:
it registers a second index under the same name, and lookups by that name
then fail.

## Stop and retire

- The human runs `state.py pause --project <parent>`. Each lane stops at its
  next `lock` or `arm`. A cycle that holds its lock runs to its end, as in
  one loop. `state.py resume --project <parent>` starts them again.
- Retire a lane when it has no open row, or when the human stops the run. Copy the
  status changes of its rows into the parent's journal. The rows are separate
  lines, so a merge of the journals conflicts only in the sections that each
  lane appends to. Keep the lane's worktree while someone needs its trail or
  its report. Then remove it with `git worktree remove`.
- The parent arms again only when it has no lane. `state.py arm` finds a lane
  by the `lane.json` in its worktree. To keep a retired lane's worktree, remove
  its `.localdev/awesomeness/lane.json`.

## Limits

- A lane's trail stays in its worktree. The parent's brief does not see the
  cycles of its lanes.
- Cycle numbers repeat across lanes. The status line names the lane.
- A row stays in the lane that worked it. To move a row, retire that lane.
