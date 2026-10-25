---
name: branch-triage
description: Sorts the remote branches of a repo into merged and open. Shows what each open branch carries (commits ahead, last date, author). Deletes the merged ones only after the user confirms the list. Triggers include '/branch-triage', 'which branches were being worked', 'merge all branches into main', 'clean up the remote branches'. Also 'delete the merged branches', 'what is open on origin'.
---

# Branch triage

Use this when a repo comes back from another machine or another agent and the
remote has many branches. The question is always the same: which branches are
done, which carry work, and which were the last ones in progress.

For local worktrees, local branches and stashes, use `worktree-gc` instead.
This skill reads and deletes **remote** branches only.

## Steps

1. Run the audit. It fetches with prune first.

   ```bash
   ~/Github/agent-skills/branch-triage/branch-audit.sh --remote origin --base main
   ```

   One tab-separated line per branch: `GROUP branch ahead behind date author subject`.
   `MERGED` means every commit is in the base: an ancestor, or each patch is in
   the base by `git cherry`, which catches squash and rebase merges. `OPEN`
   means the branch carries commits the base does not have.

2. Show the user two short tables, newest first:
   - **Open**: branch, ahead/behind, last commit date, author, subject. Mark
     the newest two or three as "last worked". A branch named like an agent
     worktree (`worktree-agent-*`, `agent/*`) is a candidate for a merge, not
     for a delete.
   - **Merged**: the count and the names. When there are more than about 15,
     show the count and list the names in a fenced block.

3. For each open branch the user wants merged, merge it on the base with
   `git merge --no-edit origin/<branch>`, or in a worktree. Run the repo's
   test commands and report. Do not merge while a process reads the tree. A game
   engine or a dev server with lazy script loading mixes the versions.

4. Delete the merged branches only after the user confirms the exact list
   shown in step 2. Then run the same command with the flag:

   ```bash
   ~/Github/agent-skills/branch-triage/branch-audit.sh --remote origin --base main --delete-merged --keep 'release/*'
   ```

   `--keep` takes a shell glob and can repeat. The base branch is always kept.
   A remote delete is outward-facing: no delete without the confirmation of
   the list, and never a branch in the OPEN group.

5. Report: how many deleted, which open branches stay with their last date,
   and which of them the user said to continue.

## Rules

- Fetch before you judge. A stale remote-tracking ref makes a merged branch
  look open.
- Zero commits ahead is merged. Commits ahead with every patch in the base is
  merged too (squash or rebase merge). Commits ahead with a new patch is open,
  even when the branch is old.
- Report dates and counts from the audit output. Do not guess what a branch
  contains from its name. Read `git log origin/main..origin/<branch>` when the
  user asks what it carries.
- The script prints the list and deletes only with `--delete-merged`. Show
  the list first, every time.
