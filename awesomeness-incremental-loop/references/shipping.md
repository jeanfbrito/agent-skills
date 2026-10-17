# Shipping modes

The project decides how loop work reaches review. Read the mode from the
project rules (`AGENTS.md`, `CLAUDE.md`) or from a human rule in the journal.
A human rule in the journal wins over the project file for this run.

| Mode | When | Where the product commits go |
| --- | --- | --- |
| `loop-branch` | No project rule (default) | The loop branch `awesomeness/<date>` |
| `pr-per-task` | The project asks for one worktree and one PR for each task | One task branch and worktree for each item |

## `pr-per-task`

The goal: the human reviews each task as one clean PR. No PR carries a second
task, a journal change or a loop chore.

1. The loop branch holds only the journal, the drafts and loop chores. It
   never holds a product commit. Never push it.
2. For each item that changes product files, make a new worktree from the
   freshly fetched default branch of the remote:

   ```sh
   git fetch origin <default>
   git worktree add <worktrees-dir>/<branch-slug> -b <type>/<KEY-or-issue>-<slug> origin/<default>
   ```

   Use the worktree directory and the branch-name form that the project rules
   give. Install the dependencies in the new worktree when the project needs
   them.
3. Build, test and check in that worktree only. Run the senses (dev app,
   VMs, captures) from that worktree, so that a check sees only this task.
4. Commit in the task branch. Push it and open the PR when the project rules
   or the human approve it. Open a draft PR while a required platform check
   is still open.
5. Write the worktree path, the branch and the PR number in the item's gap
   row and in the `commit` note. Then commit the journal on the loop branch.
6. A follow-up for a task (a review comment, a CI failure, a missed case)
   goes on the same task branch and PR. Do not open a second PR for the same
   task.
7. A later cycle can check the open PRs (CI, review comments) as its item.
8. Remove a task worktree only after the human merges or closes its PR. Remove it
   with `git worktree remove`, never with `rm -rf`.

### Work already on the loop branch

When a run changes to `pr-per-task` with product commits already on the loop
branch, move each task to its own worktree. Cherry-pick only that task's
commits onto a fresh task branch. Leave out journal and loop commits. Check
the result in the task worktree before the push.
