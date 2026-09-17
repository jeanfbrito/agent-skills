---
name: babysit
description: Babysits an open pull request until every check is green — always in its own git worktree, never asking first — by dispatching a background haiku watcher that polls for new review-bot comments and check results, then reading the whole batch, triaging all of it through `superpowers:receiving-code-review`, planning every change before editing, pushing, and re-dispatching the watcher. Stops and hands back the moment a human reviewer comments. Triggered by "/babysit", "babysit this PR", "babysit PR #123", "watch the PR", "keep an eye on that PR", "get the PR green", "handle the review bots", or immediately after a skill opens a PR. Draft-first for anything posted to the PR.
---

# Babysit

Take a PR from "filed" to **green** without the user relaying comments by
hand. Green — every check concluded successfully, no unanswered bot finding —
is the only condition under which this skill reports "done". Everything else
is a hand-back with a reason.

## Purpose

The loop being replaced: PR opens → bots comment / CI fails → user reads →
user pastes what they agree with into a session → agent fixes → push → repeat.

The failure mode to avoid: an agent that implements every bot suggestion is
not reviewing, it is laundering noise into commits. **Judgment is the point.**
A batch that declines four of five suggestions with reasons is a good batch.

## 0. State the contract (once, before the first push)

This skill pushes commits without per-commit approval, so scope is stated
once. Present this and get a clear yes — the worktree line is a statement,
not a question:

> Babysitting PR #N (`<title>`), branch `<headRefName>`, in its own worktree.
> Each round I read every new bot comment and failing check, decide which are
> worth acting on, plan all fixes together, commit, push, and go back to
> watching. I keep going until every check is green.
> I will NOT: force-push, rebase, touch the base branch, resolve review
> threads, merge, or post any comment until you approve the text.
> I stop and hand back the moment a human comments or the branch moves under
> me. Proceed?

If the user wants zero autonomous pushes, degrade gracefully: same triage,
hand back a patch per round instead of pushing.

## Tone (every word that lands on the PR)

**Read the full rules first**: `~/Github/agent-skills/shared/tone.md`
(REQUIRED — load it with Read; absolute path, this skill is symlink-installed).
Inline, because declining review feedback is where tone goes wrong:

- **No defensive lead.** A declined suggestion opens with what was checked,
  then the reason. Never "as the code already shows".
- **Real numbers only.** "Runs on every keystroke" needs a line reference or
  a measurement.
- **Frame gaps as scope**, not failure — Rule 1 of the tone doc.

## 1. Resolve the PR

```bash
gh pr view <n> --json number,url,title,state,headRefName,headRefOid,author
```

`state` must be `OPEN`; a closed or merged PR is nothing to babysit. Record
`headRefOid` (detects someone else pushing) and `author.login` (excluded
from the poll — the author is the person directing the loop, not a reviewer).

## 2. Worktree — always, without asking

Every babysit runs in an isolated worktree on the PR's head branch. Do not
ask; the user has declared this preference here. Follow
`superpowers:using-git-worktrees` with that preference already answered:

- Already in a linked worktree on `<headRefName>` → use it.
- Native tool available (`EnterWorktree`) → use it, checking out the
  **existing** branch `<headRefName>`.
- Otherwise `git worktree add .worktrees/<headRefName> <headRefName>` (no
  `-b`; the branch exists), after confirming `.worktrees` is gitignored.

Skip the full baseline test run — a monorepo baseline is not what this skill
verifies. Install dependencies lazily, the first time a focused check needs
them. All edits, checks, commits and pushes happen inside this worktree; the
user's main checkout is never touched.

## 3. Dispatch the haiku watcher

The main model does **not** poll. It dispatches one background watcher and
waits for the notification:

- Agent tool, `subagent_type: "watcher"`, `model: "haiku"`, background.
- Prompt from `~/Github/agent-skills/babysit/references/watcher-brief.md`,
  filled with PR number, `headRefOid`, the three id cursors (0 on the first
  round), `bot_authors` from `local-config.yml`, and the poll interval.
- The watcher loops `~/Github/agent-skills/babysit/watch-pr.sh` and returns
  one structured report: `STATUS`, `HEAD`, `CURSORS`, `HUMANS`, `CHECKS`,
  every new feedback item verbatim, and ≤ 40 lines of verbatim error per
  failed check. Raw comment bodies and CI logs stay in the watcher.

Never predict the watcher's result. If the user asks before it returns, say
it is still watching. Carry the returned `CURSORS` and `HEAD` into the next
dispatch so nothing is re-triaged; track **ids only** — GitHub re-anchors an
inline comment's `commit_id` onto later commits, so `commit_id` is not
evidence of anything new.

## 4. On report: classify before anything else

| `STATUS` | Action |
| --- | --- |
| `human` | **STOP.** Summarize what arrived and hand back. A human reviewer is owed the user's reply, not an agent's. |
| `sha_moved` | **STOP.** Someone else pushed; the user decides how to reconcile. |
| `closed` | Stop; nothing to babysit. |
| `checks-green` with no new feedback | **Done** — go to §7. |
| `feedback`, `checks-failed`, `deadline` | Continue to §5. |

A bot is `user.type == "Bot"`, a login ending in `[bot]`, or a login listed
in `bot_authors`. `gh pr comment` posts as the authenticated user, which is
the PR author — already excluded by the poll, so the loop cannot stop on its
own output.

## 5. Read everything, then plan everything, then edit

No file is touched until the whole batch has been read and planned.

1. **Read every item** in the report — every comment, every review body,
   every inline finding, every failed-check excerpt. Not the first few.
2. **Route every item through `superpowers:receiving-code-review`.** It
   exists to stop feedback being implemented on reflex. Do not skip it
   because a suggestion looks obvious.
3. **Write the plan** — one table for the batch, one row per item:
   `#id | source | verdict | evidence | commit group`. Verdicts:
   - **Act** — the finding is real. Say which files change.
   - **Decline** — wrong, already handled, out of scope. Record the
     evidence (file:line, a test, a doc link).
   - **Escalate** — correct but bigger than this PR or changes a contract.
     Goes to the user in the final report, not fixed silently.
   A failing check is a row too: caused by this PR → Act; flaky or
   pre-existing → rerun it once (`gh run rerun <run-id> --failed`), and if it
   fails again → Escalate, because the PR cannot go green without the user.
4. Group the Act rows into coherent commits — one per fix, not one per
   comment — and note where two items touch the same code so one edit
   resolves both.
5. Only now start editing, working the plan in order.

Planning the batch as a whole is what stops item 3 undoing item 1's fix.

## 6. Fix, verify, push, watch again

- Run the project's focused checks on what changed. Dispatch a `watcher`
  (haiku) to run them and return `STATUS:` plus verbatim failures; never let
  a full test log into this loop. Never push an unverified fix.
- `git push` from the worktree to the existing branch. Never `--force`,
  never rebase.
- Record the new `headRefOid`, then **re-dispatch the watcher (§3)** with the
  new HEAD and the cursors from the last report. Go back to §4.
- Round bookkeeping: if the same finding has now survived two of your
  fixes, stop trying variants — per AGENTIC.md, diagnose the root constraint
  before a third attempt, and say so in the report.
- Every `cycle_cap` rounds, post a short progress note to the user (rounds,
  commits, what is still red) and keep going. The cap is a check-in, not an
  exit.

## 7. Finish: green only

Done means: the latest report is `checks-green`, it carried no new bot
feedback, and every Act row from every batch is pushed. Then:

**The one comment.** If anything was declined or escalated across all
rounds, draft **one** PR comment: fixed / declined with reasons / escalated.
Run the tone doc's reread gate and grep check. Show the exact text, get
explicit approval, then `gh pr comment <n> --body-file <file>`. If nothing
was declined or escalated, skip the comment and say so.

**Final report**, plain language first:
- Rounds run, commits pushed, check status (green)
- **Acted** / **Declined** (with reason) / **Escalated** — one line each;
  Escalated is the section the user has to read
- Worktree path, and whether it can be removed
- Whether the PR now looks ready for a human

Any exit other than green is a **hand-back**, not a finish: lead with the
reason (`human`, `sha_moved`, root-constraint, un-rerunnable failure), then
the same report.

## local-config.yml (optional, gitignored)

Created lazily on first run, next to this file. Ships with no real values.

```yaml
# ~/Github/agent-skills/babysit/local-config.yml
poll_interval: 120      # seconds between polls inside the watcher
watcher_deadline: 45    # minutes a single watcher dispatch lives before reporting "deadline"
cycle_cap: 6            # rounds between progress check-ins (not an exit)
bot_authors:            # extra non-"[bot]" accounts to treat as automated
  - coderabbitai
  - sonarcloud
```

Match `poll_interval` to the project's CI duration: polling every minute
during a 12-minute pipeline burns tokens for no signal.
