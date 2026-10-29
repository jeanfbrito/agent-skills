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

## Split plan

In both modes, the loop's work becomes PRs that people must review. Past
about 1000 changed lines or 40 files, nobody can review and agree with a PR
at once. Lockfiles, build output and the loop docs do not count. The project
can set another limit in the journal's Setup:
`- PR size limit: 600 lines, 25 files`.

`state.py brief` raises `PR-SPLIT` when a local branch that holds recent loop
commits is past the limit, and the journal's "PR plan" section does not name
that branch. It also sizes each branch that the plan names, local or pushed.
You can rebuild a PR branch from the loop work with cherry-picks, squashes
or new commits. Then its commits are different, and only its row in the plan
lets the check find it. Add the row when you create the branch. Write the
repo folder name in the `Repo` column, as in Setup. Then a branch name that
two repos use is sized only in the repo that the row names. Commits already in the default branch do not count. Write the
plan when the chore first shows. Do not wait for the handover: a plan made
early keeps each new commit in one slice.

1. **The design record goes first.** Reviewers validate the decisions
   (`references/design-record.md`) before they read any PR.
2. **Split by layer, in merge order.** A usual stack: the contract (types,
   API, settings and their defaults), then storage and indexing, then the
   backend logic, then the UI. Each PR builds, passes its tests and changes
   no behavior for users that the next PR needs to fix. Put a new feature
   behind its opt-in setting from the first PR.
3. **Each PR stays under the limit.** When one slice cannot, write
   `whole: <why>` in its row ("whole: one generated worker bundle"). A
   numbered slice past the limit with no `whole:` raises `PR-SPLIT` again.
   Write `-` in the `#` column for a branch that is not for review.
4. **Name every branch.** The integration branch, where the demo runs, stays
   whole. Name it in the plan with the role "integration and demo, not for
   review". Name each side branch with its role too.
5. **Cross-repo work** gets one plan with both repos, and the order between
   them (the server contract before the client that reads it).
6. **Keep each commit inside one slice.** A commit that mixes two layers
   cannot go to two PRs. Then each slice is a cherry-pick of its commits.

The base of each PR is the remote HEAD of its repo. When that is wrong or
missing, set it in Setup: `- Default branch: dev, core: develop`. A bare
name is the project's base. `<repo folder>: <branch>` sets the base of an
other repo.

```markdown
## PR plan

| # | Repo | Branch | Carries | Size | Depends on |
| --- | --- | --- | --- | --- | --- |
| - | app | `awesomeness/2026-10-26` | integration and demo, not for review | 17818 lines | - |
| 1 | app | `feat/search-contract` | bridge types, settings, defaults | 420 lines | design record |
| 2 | app | `feat/search-index` | index schema and storage | 880 lines | 1 |
```

Update the plan when a slice grows past the limit. The PR description of
each slice names its place in the stack (the `pr-description` skill).
