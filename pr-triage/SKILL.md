---
name: pr-triage
description: 'Triages the open pull requests of the current GitHub repo, made to run weekly. For the user''s own PRs it lists what blocks the merge (conflicts found by a local trial merge, failing checks with the failing test named, unresolved review threads, drafts, wrong or stacked base, overlap with sibling PRs) and the next action. For third-party PRs it drafts a review: what the PR does, concrete risks, a verdict and a suggested reply. Bot PRs (translations, dependency bumps) get duplicate and base checks. A snapshot script keeps the head SHA of each PR, so later runs review only new or updated PRs. Triggered by "/pr-triage", "triage the PRs", "review the open PRs", "what is blocking my PRs", "weekly PR review", "revise os PRs em aberto". Draft-first: never comments, reviews, closes or merges without approval.'
---

# PR Triage

Turn the open PR list into a short, per-PR answer: **mine → what blocks the
merge and the next action; theirs → what it is and what to reply.**

## Tone (outward text only)

Suggested replies to authors are public. Read
`~/Github/agent-skills/shared/tone.md` before you draft them. Key rules:

- **No defensive lead.** Thank the author, state the concrete ask.
- **Real facts only.** Every claim in a reply traces to a file:line, a check
  log or a linked issue. No guessed causes presented as fact.
- **Anonymize.** No customer names, no internal ticket text, no internal chat
  links in replies (a bare Jira key is fine where the repo allows it).

Write the report itself in the user's language. Write suggested replies in
the language of the PR (usually English).

## 1. Snapshot

Run from inside a clone of the repo (the local trial merge needs it):

```bash
~/Github/agent-skills/pr-triage/pr-snapshot.py [--since YYYY-MM-DD | --all] > "$SCRATCH/snap.json"
```

- Default window: PRs created in the last 30 days. Use the window the user
  names ("this month", "since the release"). Say which window you used.
- Per PR it returns: `mine`, `bot`, `status` (`new` / `updated` /
  `unchanged` since the last `--save`), `blockers`, `checks` (failing and
  pending names), `unresolved_threads` (human / bot), `local_merge`
  (conflict files and commits behind base), size, base and head.
- GitHub leaves `mergeable` as `UNKNOWN` for most PRs in big repos, even
  after a REST read. Trust `local_merge`, not `mergeable`.
- The script fetches `refs/pr-triage/<N>` and `refs/pr-triage/base/<branch>`
  into the clone. Use them for diffs; never check out a PR branch.

On a weekly run, deep-review only `new` and `updated` PRs. List `unchanged`
PRs in one line each, carrying forward last week's verdict when you have it.

## 2. My PRs — what blocks the merge

For each `mine` PR, turn each blocker into a cause and a next action:

| Blocker                  | Dig                                                                                                                                                                                                                                                          |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| failing checks           | `gh pr checks N --json name,state,link`, then `gh run view <run> --log-failed \| grep -E "FAIL \|●\|error"`. Name the failing test and the cause line, for example "conferenceWindow.spec mock lacks `powerMonitor`". Lint failures: name the rule and file. |
| merge conflicts          | Name the conflict files from `local_merge`. Say which merged PR or sibling PR caused them (`git log refs/pr-triage/base/<b> --oneline -- <file>`).                                                                                                           |
| unresolved bot threads   | Summarize each ask in one line (GraphQL `reviewThreads` with the first comment body). Separate real bugs from style nits.                                                                                                                                    |
| unresolved human threads | Quote who asked what. These block more than bot threads.                                                                                                                                                                                                     |
| draft                    | Say if it is ready to un-draft, needs work, or should close.                                                                                                                                                                                                 |
| base is not default      | Stacked PR: name the PR it stacks on and the merge order.                                                                                                                                                                                                    |
| no approving review      | Suggest a reviewer only if the repo has a habit (CODEOWNERS, past reviewers on those files).                                                                                                                                                                 |

Then check across the user's PRs:

- **Overlap.** Run `git diff --name-only refs/pr-triage/base/<b>...refs/pr-triage/<N>`
  for each PR and intersect the sets. Shared files mean a merge order
  matters. Say the order.
- **Supersession.** Older PRs whose files a newer PR rewrites (config,
  docs, agent tooling) may be obsolete. Propose to close them.
- **Local notes.** Search `.localdev/workflow/` (cards, handoffs, blockers)
  and project memory for the PR number. A card can name a hidden risk that
  GitHub does not show, for example a runtime mismatch inside a string.

## 3. Third-party PRs — review draft

Dispatch `reviewer` subagents with the brief in
`~/Github/agent-skills/pr-triage/references/review-brief.md`, at most 3 PRs
per agent, all agents in one message. Group PRs that touch the same files.
Add the specific checks you already know (an earlier decision, a sibling PR
on the same file, a code path another PR deletes).

Before you relay a verdict, verify its strongest claim yourself with one
command (for example, `git diff ... -- <file> | tail`). A subagent report is
a claim, not evidence.

## 4. Bot PRs

- **Duplicates.** Hash each bot diff against its base
  (`git diff refs/pr-triage/base/<b> refs/pr-triage/<N> | shasum`). Identical
  hashes mean only the newest matters; propose to close the rest.
- **Base.** Check the base against the repo branching model (AGENTS.md). A
  translation bot that targets the release branch, not the integration
  branch, is a configuration problem. Show what the diff does against the
  integration branch (for example, it deletes newer strings).

## 5. Report

Lead with a 3-5 line summary: counts, the merge order for the user's PRs,
and the decisions only the user can make. Then:

1. **My PRs**, ordered by closest to mergeable: `#N title — blockers → next action`.
2. **Third-party PRs**: what it does, verdict, main risk, suggested reply.
3. **Bots**: duplicates and base problems.
4. **Numbered actions for the user**, most blocking first.

Label each claim as measured (script, log, source), inferred or a guess.

## 6. After the report

- Never post a comment, review, label, close or merge without the user's
  explicit approval of the exact text and the exact PR list.
- Fixes on the user's own PRs follow the normal flow: one worktree per PR,
  and the `babysit` skill once pushed.
- When the user has read the report, run the snapshot again with `--save`
  so the next run marks only changed PRs. State lives in
  `~/Github/agent-skills/pr-triage/local-state.json` (gitignored).

## Weekly runs

Run `/pr-triage` from the repo clone once a week. A cloud routine has no
local clone, so the trial merge and the subagents do not work there. If the
user wants a reminder, propose `/schedule` for a reminder only.
