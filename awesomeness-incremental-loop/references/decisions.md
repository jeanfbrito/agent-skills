# Decisions file

The loop keeps every decision that only the human can make in one file,
`docs/awesomeness-loop-decisions.md`. The human can be away for hours. When
the human comes back, the orchestrator asks each open decision, one question
at a time, and the human answers with a click.

## What goes in it

A decision is a choice that no experiment can settle. Examples: a product
call, a default, a name, a community PR, or permission for an action that the
loop may not take alone. Write one entry each time a cycle writes one of
these: an `ask` row, a decision-type `assumption` row, a toggle verdict, or a
"Tell me if..." line in "Waiting on you".

Do not write a decision for a check that the loop can run itself. That
includes checks on the project's test VMs and test servers, specs
and the dev app. Run the check instead.

## Entry format

```markdown
### D<n> · <ticket or issue> · <short title> · open

- Header: <at most 12 characters>
- Question: <one sentence that ends with "?">
- Options:
  1. <label> (Recommended): <what happens, and why the loop recommends it>
  2. <label>: <what happens>
- Context: <commit, PR, file, and what the loop already did>
- Answer:
- Applied:
```

- Give 2 to 4 options. Put the loop's recommendation first, and mark it
  `(Recommended)`. The human can always type another answer.
- Write the question so that the human can answer it with no other file
  open. Put the facts in the options and in Context.
- Number the entries in order, and never reuse a number.
- The status in the heading is `open`, `answered` or `applied`.
- A decision about feel (how it plays, looks or sounds) gives one full,
  playable URL for each option in its Options. The human tries them and then
  chooses. A text description of a feel is not enough to choose on.
- The human can delegate a decision. Then the loop chooses and writes
  `Answer: delegated, loop chose <option> because <reason>`.
- When an answer picks one option over another, its `Applied` line names
  the check that fails on the rejected option.

## The orchestrator asks

When a human message arrives while the loop runs, and the file has `open`
entries, ask them before you spawn the next cycle. Ask at most 4 per round,
with the harness's question tool (`AskUserQuestion` in Claude Code). Use each
entry's Header, Question and Options. Ask in file order. Skip the rest when
the human says "later".

For each answer, write it in `Answer` with the date, for example
`Answer: option 1, human 2026-10-17`. Copy free text word for word. Set the
heading status to `answered`. Commit the file on the loop branch. Then copy
each answer into the Verdict cell of the matching journal row, if one
exists, so that the brief raises `APPLY`.

A harness can have no question tool. Then print the open entries as a
numbered list. Ask the human to reply with the option numbers.

## A cycle applies

`state.py brief` raises `APPLY-DECISIONS` when an entry has an `Answer` and
an empty `Applied`. The cycle applies each answer as a `DO FIRST` chore.
It writes `Applied: <commit, PR or action>, cycle <n>`, and sets the heading
status to `applied`. An answer that needs an outward action uses only the
actions the human rules allow.
