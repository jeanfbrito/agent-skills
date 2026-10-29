# Signal cycles

The brief's item line names one of these signals. The cycle that sees it
follows the section here instead of normal item work. Read the section when
the brief names it. The cycle steps in `SKILL.md` ("One cycle") still apply:
lock, pick, note, end and unlock.

## Step back (signal `STALL`)

A row can stay open for 3 cycles, or for 2 cycles in a row with no progress.
Then the row is too big, or its approach is wrong. More cycles of the same kind
will not close it. This cycle does no build. It does this:

1. Read the row's `Done when`, its trail notes, its commits, and
   `references/lessons.md`.
2. Write the one sentence that every cycle on this row assumed. Test it. Ask:
   can this approach reach `Done when` at all? Does it drive the cause, or
   does it pose the output?
3. Choose one result and write it in the journal:
   - **Split**: replace the row with smaller rows that can each close in 1–2
     cycles. Give each one its own `Done when`.
   - **Change the approach**: write the new approach and why the old one
     cannot reach the target. You can make a structural change here. Do it in
     a lab when the project is busy.
   - **Ask the critic**: for a `quality bar` row, run one direction round on
     the current state (`references/critic-brief.md`).
   - **Block**: no path remains. Set `blocked` with the root constraint.
4. Note it: the cycle pick needs `--target "choose a different route or block this row"`
   and `--check "test the premise against the trail and source"`. Record
   `S note step-back "<result and why>"`. Commit the journal, and
   end the cycle. The step-back note resets the row's cycle count.

## When no row is open (signal `EXHAUSTED`)

`EXHAUSTED` means that no row is open or queued, and some rows are `blocked`
or `held` (the human froze them). Do not stop the loop. The three steps take
turns, one round each, and the brief names the next one. A round is one
cycle, and the work it opens is done before the next `EXHAUSTED`.

1. **Coverage**: compare the matrix with the reference, area by area. Add a
   row for each area with no row. A row names something that a user sees or
   does (a mode, a screen, a mechanic, a behavior, a look). It is not a
   constant, a byte or one value of a parameter: put those in the `Done when`
   of the row they belong to.
2. **Unblock**: take the oldest `blocked` row. Attack its premise, or send it
   to an auditor. A new path sets the row back to `partial`. With no
   `blocked` row (only `held`), the brief skips this step.
3. **Beyond mode**: invent (`references/beyond.md`).

## When only the human can help (signal `WAITING`)

`WAITING` applies after six cycles with no product change, in one of two
cases. In the first case, no row is open or queued. In the second case, a
row waits for a human verdict, and no cycle in the run made measured
progress on another row.
In the second case, open rows do not keep the loop running. A product change
or measured progress resets the count. This cycle
does not build and does not review. It does this:

1. Read the empty cells in "Pending verdicts" and "Assumptions and asks", and
   the `Next priorities` in `Direction`.
2. Write at most 5 items in the journal's `Waiting on you` section, the most
   useful first. Each one names what the human gives (a `keep`, a reference
   frame, a decision) and what a user then sees. Write each decision also as
   an entry in `docs/awesomeness-loop-decisions.md`
   (`references/decisions.md`).
3. Commit the journal. `S note end --status waiting --progress none --next
   "<the first item>"`.

The orchestrator then runs `S wait`, which uses no agent. It returns when the
human changes the journal, the code or the ledger cards. If the human gave a
verdict in chat, record it in the journal first. Set its blocked row back to
`partial` only when the verdict addresses the blocker. The next cycle can then
pick that row. A `waiting` end resets the count, so a wake gets 6 more cycles
before the loop waits again. Waiting is not a stop: the human is still the brake.
