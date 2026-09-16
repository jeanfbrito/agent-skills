---
name: babysit
description: Monitors an open pull request after it is filed, triages incoming automated review-bot comments and CI failures through `superpowers:receiving-code-review`, pushes the fixes worth making, and loops until a full cycle produces no actionable feedback. Stops and hands back the moment a human reviewer comments. Triggered by "/babysit", "babysit this PR", "babysit PR #123", "watch the PR", "keep an eye on that PR", "handle the review bots", or immediately after a skill opens a PR. Draft-first: agrees an explicit autonomy contract before the first push, and batches all outward-facing PR prose into one summary comment approved before posting.
---

# Babysit

Take a PR from "filed" to "the bots have nothing left to say" without the
user relaying comments by hand.

## Purpose

The loop being replaced is: PR opens → review bots comment → user reads the
comments → user copy-pastes the ones they agree with into a session → agent
fixes → push → bots comment again. Three or four rounds of that is normal,
and every round costs a context switch.

This skill closes that loop. The failure mode it must avoid is the obvious
one: an agent that implements every bot suggestion is not reviewing, it is
laundering bot noise into commits. **Judgment is the point.** A cycle that
declines four of five suggestions with reasons is a successful cycle.

## 0. Agree the autonomy contract (REQUIRED, before anything else)

This skill pushes commits without per-commit approval, so the scope has to be
explicit once, up front. Present this and get a clear yes:

> Babysitting PR #N (`<title>`), branch `<headRefName>`.
> I will: read new bot comments and failing checks each cycle, decide which
> are worth acting on, commit and push fixes to that branch.
> I will NOT: force-push, rebase, touch the base branch, resolve review
> threads, merge, or post any comment until you approve the text.
> I will stop and hand back if a human comments, if CI fails for a reason
> unrelated to my changes, or after <N> cycles.
> Cadence: every <interval>. Proceed?

If the user declines any part, adjust the contract, don't proceed around it.
If they want zero autonomous pushes, degrade gracefully: run the same triage
and hand back a patch per cycle instead of pushing.

## Tone (applies to every word that lands on the PR)

**Read the full rules first**: `~/Github/agent-skills/shared/tone.md`
(REQUIRED — load it with Read; absolute path, this skill is symlink-installed
and a relative path breaks).

Called out inline, because declining review feedback is exactly where tone
goes wrong:

- **No defensive lead.** A declined suggestion opens with what was checked,
  then the reason. Never "as the code already shows" or "that's not how it
  works".
- **Real numbers only.** "Runs on every keystroke" needs a line reference or
  a measurement, not an impression.
- **Frame gaps as scope**, not failure — per Rule 1 of the tone doc.

## 1. Resolve the PR

If the user gave a number, use it. If they said "this PR" or the skill was
chained after one was opened, resolve from the branch:

```bash
gh pr view --json number,url,title,state,headRefName,headRefOid,mergeStateStatus,reviewDecision
```

Confirm `state` is `OPEN`. A closed or merged PR is nothing to babysit — say
so and stop. Record `headRefOid`; it is how you detect that someone else
pushed underneath you.

## 2. Each cycle: gather

```bash
# issue-level comments (review bots usually post here)
gh pr view <n> --json comments,reviews,statusCheckRollup,headRefOid

# inline review comments — this endpoint carries user.type, which the
# above does not reliably expose
gh api repos/{owner}/{repo}/pulls/<n>/comments --paginate

# check status, human-readable
gh pr checks <n>
```

Process only what is **new since the last cycle** — track the highest comment
id and the last `headRefOid` you saw. Re-triaging the same comment every
cycle is the main way this skill wastes tokens.

Prefer routing the raw output through context-mode so full comment bodies and
CI logs stay out of the conversation; surface only the triaged items.

When a check has failed and you need the actual log to triage it, do not pull
`gh run view --log` into this loop. Dispatch a `watcher` agent (when delegation
is authorized) pointed at the failing run and keep only what it returns — a
`STATUS:` line plus the verbatim error. Over six cycles that is the difference
between a lean loop and one slowly filling with build output.

## 3. Each cycle: classify the author

| Author | Action |
| --- | --- |
| `user.type == "Bot"`, or login ends in `[bot]` | Triage autonomously |
| Known bot account in `local-config.yml` | Triage autonomously |
| Anyone else — a human | **STOP the loop.** Summarize and hand back. |

A human reviewer spent real attention and is owed a real reply from the user,
not an agent's. Ending the loop on the first human comment is a feature.

## 4. Each cycle: triage

**Route every item through `superpowers:receiving-code-review`** before
touching code. That skill exists to keep review feedback from being
implemented on reflex, and it is the difference between this loop improving
the PR and it degrading the PR. Do not skip it because the suggestion looks
obvious.

For each item, land on one of:

- **Act** — the finding is real. Fix it.
- **Decline** — wrong, already handled, or out of scope. Record the reason
  and the evidence (file:line, a test, a doc link).
- **Escalate** — correct but larger than this PR, or it changes a contract.
  Do not fix it silently; it goes to the user in the final report.

A failing check is triaged the same way: if the failure is caused by this
PR, fix it. If it is a flaky or pre-existing failure, that is an Escalate,
not something to paper over by touching unrelated code.

## 5. Each cycle: fix and push

- One commit per coherent fix, not one commit per bot comment.
- Run the project's own focused checks on what changed before pushing. Same
  rule as §2: dispatch a `watcher` to run them and return the verdict, rather
  than letting a full test or build log into the loop. If delegation is not
  authorized, run them directly but keep only the verdict and any verbatim
  failure. Never push on an unverified fix.
- `git push` to the existing branch. Never `--force`, never rebase — the
  user or a reviewer may be reading the diff while you work.
- If `headRefOid` moved without you, someone else pushed: stop, report, and
  let the user decide. Do not merge or reconcile on your own.

## 6. Exit conditions

Stop and report when any of these hit — whichever comes first:

- A full cycle produced no new actionable bot feedback **and** checks pass.
- A human commented (§3).
- The branch moved underneath you (§5).
- The cycle cap from the contract is reached.
- The same finding has now failed to be resolved twice — per AGENTIC.md,
  that is a root-constraint problem, not a third-attempt problem.

## 7. The one comment

Do not reply per item during the loop; batch it. On exit, if anything was
declined or escalated, draft **one** summary comment covering all of it:
what was fixed, what was declined and why, what was escalated.

Show the user the exact final text and get explicit approval before posting.
Run the tone doc's reread gate and its grep check on the draft first. Post
with `gh pr comment <n> --body-file <file>` only after approval.

If everything was acted on and nothing declined, there is nothing worth
posting. Say so and skip the comment.

## 8. Final report

Lead with plain language, then detail:

- Cycles run, commits pushed, current check status
- **Acted**: one line each
- **Declined**: one line each, with the reason
- **Escalated**: what needs the user's decision — this is the section they
  actually have to read
- Whether the PR now looks ready for a human

## Cadence

`/loop <interval> /babysit <n>` is the natural driver. Match the interval to
the project's CI duration — polling every minute while a 12-minute pipeline
runs burns tokens for no signal. When the CI time is unknown, 5 minutes is a
reasonable first guess; widen it once the real duration is observed.

## local-config.yml (optional, gitignored)

Created lazily on first run, next to this file. Ships with no real values.

```yaml
# ~/Github/agent-skills/babysit/local-config.yml
poll_interval: 5m       # default cadence
cycle_cap: 6            # max cycles before handing back
bot_authors:            # extra non-"[bot]" accounts to treat as automated
  - coderabbitai
  - sonarcloud
```
