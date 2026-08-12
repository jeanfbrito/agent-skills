---
name: proposal
description: Drafts a one-page technical initiative proposal backed by real evidence mined from the project (known issues, git history, ledger, CI patterns). Triggered by "/proposal", "draft a proposal", "propose an initiative", "write an improvement proposal", "make the case for X". Draft-first: nothing is filed or posted without explicit approval. Intended cadence: roughly quarterly.
---

# Proposal

Turn observed engineering friction into a one-page technical initiative
proposal leadership can act on — the "propose improvements proactively
instead of reacting" muscle. Typical topics: automated testing, QA
infrastructure, architecture upgrades, tooling, developer experience.

## Purpose

A proposal converts hard-won reactive knowledge (the bugs you kept fixing,
the CI flake you kept rerunning) into a visible initiative someone can fund.
One page maximum — a proposal nobody finishes reading changes nothing. The
reader is an engineering manager or team lead deciding whether to invest.

## Tone (READ FIRST — applies to EVERY section)

**Read the full tone rules before drafting**:
`~/Github/agent-skills/shared/tone.md` (REQUIRED — load it with Read; use
the absolute path, skills are symlink-installed and relative paths break).

Call out inline, since this skill lives or dies on it:

- **Real numbers only.** Every count in the proposal must trace to git
  history, CI, tickets, or the ledger — no invented metrics.
- **Effort sizing is allowed but must be labeled as an estimate.** Use S/M/L
  t-shirt sizing, never invented hours.
- **Frame current gaps as scope/opportunity, not blame.** "No integration
  coverage for path X yet" beats "nobody ever built tests for X" — per the
  tone doc's Rule 1.

## 1. Pick the topic

If the user named a topic, use it and skip to step 2.

Otherwise, mine friction signals and present 2–3 candidate topics, each with
one line of evidence, for the user to pick. Prefer context-mode batch
execution (or equivalent) so raw command output stays out of the
conversation — only the derived signal should surface.

Signal sources (run from the project root):

- **Known issues** — `docs/KNOWN_ISSUES.md`: persistent constraints that
  keep biting.
- **Recurring fix clusters** — subject-prefix frequency shows where fixes
  concentrate:

  ```bash
  git log --since="3 months ago" --oneline --no-merges | sed 's/^[a-f0-9]* //' | cut -d: -f1 | sort | uniq -c | sort -rn | head
  ```

- **The ledger** — repeated themes in `.localdev/workflow/done.md` (CI
  flakes, re-fixed areas, verification pain).
- **Mastermind lessons** — if the `mm_search` MCP tool is available, search
  for recurring war stories or lessons tied to the candidate topics.
- **Stale open PRs** — old open PRs often mark under-resourced areas:

  ```bash
  gh pr list --author "@me" --state open
  ```

## 2. Gather evidence for the chosen topic

Real numbers only. Good evidence: "12 of the last 40 fix commits touch the
downloads subsystem", "3 CI reruns needed this month per the ledger",
"KNOWN_ISSUES has had this entry since <date>". Never: speculated user
counts, estimated hours lost.

## 3. Write the draft

Write to `docs/proposals/<slug>.md` if the project has a `docs/` directory.
If it doesn't, or the user prefers not to commit it, offer the scratchpad or
conversation-only instead — ask before writing to `docs/`.

```markdown
# Proposal: <Title>

## Problem

What hurts today, with the evidence. 2-4 sentences + the numbers.

## Proposed change

Concrete and scoped — what gets built/changed, in what order. Not a wish.

## Effort

S / M / L (estimate), with one sentence on what drives the size.

## Expected impact

Observable outcomes only — what becomes true that isn't today
(e.g. "UI regressions caught before merge instead of in QA passes").

## Risks and alternatives

What could make this not worth it; what else was considered and why not.

## Ask

The specific decision needed and from whom (e.g. "approve 1 sprint of
X's time next quarter").
```

## 4. Deliver (draft-first, ALWAYS)

Present the full draft in the conversation inside a fenced code block (raw
markdown, bare URLs only, no blockquote `>` prefixes) so the user can copy
it wholesale.

Then offer, without executing until the exact text is approved:

- A Confluence page (Atlassian connector).
- A team-channel summary (3–4 lines linking the full doc).
- A Jira ticket via the `jira` skill.

Declining all three is a valid outcome.

## Quality checklist

Before presenting the draft, verify:

- [ ] One page or less
- [ ] Every number traces to git, CI, tickets, or the ledger
- [ ] Effort is labeled as an estimate (S/M/L), never invented hours
- [ ] Tone rules applied — gaps framed as scope, no invented metrics, no
      blame framing
- [ ] The Ask names a specific decision and a specific decider
- [ ] Nothing filed or posted without explicit approval of the exact text
