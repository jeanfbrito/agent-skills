# The sense-check review

Every 3 cycles, `state.py brief` gives `REVIEW-DUE`. That cycle does no
build. It steps back from the rows and asks one question: is the loop making
this project better for the people who use it?

The cycle is a new subagent. It did not do the work that it judges, so it has
no reason to defend it. Be strict, like the critic. A change can be correct,
tested and committed, and still be useless.

## Steps

1. **Read what the project offers.** The `Direction` section of the journal
   (the product focus), the pitch and the current focus in `AGENTS.md`,
   `CLAUDE.md` or the README, and the references. Write down, for yourself,
   who uses this project and what makes it worth using. If the product focus
   in `Direction` is missing or wrong, rewrite it in one or two sentences.
2. **Read the cycles since the last review.** Run `state.py brief`, and do
   its `DO FIRST` chores as in any cycle. These are the cycles with an `end`
   note and a number higher than the last `review` cycle. When there are more
   than 10, take the 10 highest. Read the old `Direction` too: this review
   continues it. Read their `pick` and `end` notes in the trail
   (`.localdev/awesomeness/trail.jsonl`): the item, its `why`, the status
   change, the progress, and the commit. Read the commits only when a note is
   not clear.
3. **Judge each cycle**: `useful`, `marginal` or `useless`, with one line of
   reason. Ask:
   - Would a user of this project notice the change? A value that nobody can
     see or feel is useless, even when it copies the reference exactly.
   - Does it serve the product focus, or is it reference trivia (a constant,
     a byte, one parameter value, a detail of the reference's internals)?
   - Did it change the product, or only measure it? A measure is useful
     when it guards a risk. A run of measures with no change is marginal.
   - Was it the most valuable open thing at that time? Name the bigger thing
     that waited, if there was one.
   - Was the effort in line with the effect?

   When you cannot tell whether a user would notice it (a sound in the mix,
   a small visual change), call it `marginal`, not `useful`. Do not capture
   or listen to find out: this cycle does not build or measure.
4. **Judge the matrix as a whole.**
   - A row that is reference trivia, outside the product focus, or a large
     effort for an effect that nobody notices: set it `held` with
     `low value: <reason>`. When its detail matters, move it into the
     `Done when` of the row that it belongs to.
   - What is missing that a user of this project would miss most? Add at most
     5 rows, each with a `Done when`.
   - Set `Impact` again where the cycles showed that it was wrong.
   - The waste can be a pattern, not one row. Examples: rows made from one
     value of the reference's internals at a time, or many variants of one
     effect in a row. Name the pattern under `Stop doing`. Leave the rows that
     are already closed as they are.
   - Some next steps need what only the human can give: a verdict on feel,
     reference frames, a decision. Write those as an `ask` under
     "Assumptions and asks", not as a gap row.
5. **Update the Direction section** in the journal. Change only what these
   cycles show. A `Stop doing` line stays until cycles show that the waste
   stopped. Keep it under 15 lines:
   - `Product focus:` one or two sentences.
   - `Keep doing:` at most 3 lines, each with the cycles that show it.
   - `Stop doing:` at most 3 lines, each with the cycles that show it.
   - `Next priorities:` at most 5 rows, in order, each with its reason.
   - `Reviewed at cycle:` the number of this cycle.
6. **Write the notes and end.** `S note pick "sense-check review" --row
   review --mode review`. One `see` note with
   `--metric useful=<n> --metric marginal=<n> --metric useless=<n>`. Commit
   the journal. `S note end --status "review" --progress
   "useful <n>/<judged>"`. The status line gives the counts and the first next
   priority.

## Rules

- Do not build, tune or capture in this cycle. The next cycles do the work.
- A human verdict, a human priority and a `held` row that the human froze
  outrank this review. Do not undo them.
- Judge by the user of this project, not by the reference. The reference is
  a bar for quality, not a list of things to copy.
