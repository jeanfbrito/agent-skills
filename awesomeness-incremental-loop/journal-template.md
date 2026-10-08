# Awesomeness loop journal

The awesomeness-incremental-loop skill reads this file at the start of each
cycle, through `tools/state.py brief`. This file holds the decisions: setup,
sources, the gap matrix and your verdicts. The step-by-step history is the
trail (`.localdev/awesomeness/trail.jsonl`). The loop writes it as it works,
and the live report shows it: `.localdev/awesomeness/report/index.html`.

Write your verdicts in "Pending verdicts" and your answers in "Assumptions and
asks". The next cycle applies them. To pause every driver, run `state.py pause`.

## Setup

- Project:
- Reference (current bar):
- Earlier references (too easy):
- Branch:
- Frame-rate target: 30 | 60 | other (reason)
- Physics rate: (Hz, substeps, solver iterations, and the metric that proved each raise)
- Mode: gap | beyond

## Direction

The review cycle (every 3 cycles, `references/review-prompt.md`) rewrites
this section. Each cycle reads it in the brief. The human can edit it too.

- Product focus: (who uses this project, and what makes it worth using)
- Keep doing:
- Stop doing:
- Next priorities:
- Reviewed at cycle:

## Waiting on you

A `WAITING` cycle writes here what only the human can give, at most 5 items,
the most useful first. The loop waits, with no agent run, until you change
this journal, the code or the ledger cards.

## Sources

| Kind | Path | Notes |
| --- | --- | --- |
| Human priorities | | |
| Known problems | | |
| References | | |
| Product focus | | |

## Pending verdicts

Toggles only. Write `keep`, `kill` or `tweak: <note>` in the Verdict column.

| Toggle | What it does | How to turn it on | Evidence | Verdict | Applied |
| --- | --- | --- | --- | --- | --- |

## Assumptions and asks

`assumption`: the loop chose a value or a gesture that the sources leave open.
`ask`: the loop needs something only the human can give, for example reference
frames. Write your answer in the Verdict column.

| Kind | What | Where it lives | Why | Verdict | Applied |
| --- | --- | --- | --- | --- | --- |

## Senses

| Sense | How to call it | Returns | Cost | Proven to fail on |
| --- | --- | --- | --- | --- |

## Invariants

Rules from `senses/invariants.md` that this project uses, and its exceptions.
Only the human or a project doc adds an exception.

| Invariant | Tolerance | Exception and reason | Added after (complaint or cycle) |
| --- | --- | --- | --- |

## Labs

| Lab | Subject | How to run it | Measures | Status |
| --- | --- | --- | --- | --- |

## Gap matrix

`Done when` is one measurable target from the reference evidence. A row
should close within 3 cycles. If it does not, the next cycle is a step back.

| Item | Reference evidence | Done when | Status | Lab result | Full-project result | Impact | Effort | Last checked |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

## Critic queue

Rows whose senses pass in the full project. One blind critic round runs for the
whole queue (at about 5 rows, at a milestone, or before a mode change).

| Item | Shots to compare | Sense evidence | Queued at cycle |
| --- | --- | --- | --- |

## Blocked

| Item | Attempts | Root constraint | What would unblock it |
| --- | --- | --- | --- |

## Idea backlog (beyond mode)

| Idea | Source | Impact | Effort | Status |
| --- | --- | --- | --- | --- |
