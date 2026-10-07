---
name: awesomeness-incremental-loop
description: >-
  Runs an endless improvement loop on a project that has reference material in
  its docs, on any agent harness. Each cycle is a self-contained run. It reads
  its state from a journal and picks the most important gap against the
  references: human priorities first, then quick wins. It builds the smallest
  change that moves that gap's "done when" target. It checks the change with
  cheap senses and commits. It writes each step to a trail as it happens. A
  later run continues where the last one stopped, and the trail is the live
  report. A row that stays open for
  3 cycles forces a step back: split it, change the approach, ask the critic,
  or block it. So the loop moves forward and does not circle. A harsh blind
  critic runs only at the done gate. Past full
  parity it invents additions behind toggles until a human gives a verdict. The
  session that runs the skill is the orchestrator: it runs each cycle as a
  new subagent and spawns the next one when it ends. Only the human stops it. Adapted from the gauntlet loop. Triggered by
  '/awesomeness-incremental-loop', 'awesomeness loop', 'run the awesome loop',
  'what is next from the references', 'find what is missing versus the
  reference', 'keep improving until I stop you'.
argument-hint: "[optional: focus area] [optional: --no-commit] [optional: --reference NAME]"
---

# Awesomeness Incremental Loop

The loop is one **cycle**, repeated without end. The session that runs the
skill is the **orchestrator**. It gives each cycle to a new subagent, and it
starts the next one when that one ends (`references/drivers.md`). No cycle keeps
anything in memory, so the
loop runs the same on every agent harness.

**Write as you work.** Each step of a cycle writes one note to the **trail**
(`S note`, below) at the moment it happens. The notes are the pick, the
prediction, each attempt, each capture and measure, keep or revert, the
commit and the end. Do not
save notes for the end of the cycle. A later run reads the trail and continues
the open cycle from its last note, so a kill loses at most the step in
progress. Each note also rebuilds the HTML report. The trail is the report:
it organizes the screenshots and metrics so anyone can see where the work is
and recall what happened. Nobody builds the report as a separate job.

**The human is the brake.** The loop has no "done" state. Do not ask "continue?".

## Start small, grow when stable

Every dimension starts at its smallest useful size. It grows one step only
when the current step is stable: its checks pass on two runs in a row, and no
new invariant breaks. Small is about scope. Small is not a reason to keep an
approach that cannot reach the reference (see "Step back").

| Dimension | Start | Grow to |
| --- | --- | --- |
| Scope | One subject in a lab | The full project |
| Rates | 30 or 60 fps, physics at the same rate | More only on proof (`senses/metrics.md`) |
| Views | The one view that the item needs | More angles for 3D (`senses/3d-views.md`) |
| Checks | The focused senses | Wider gates, then the critic gate |
| Builders | One | At most 3 in parallel |
| Reference | The bar the project can reach | A harder bar when ours wins |
| Senses, invariants, report | The few that the item needs | More as blockers and complaints show gaps |

Files are in `~/Github/agent-skills/awesomeness-incremental-loop/`:

| File | Use |
| --- | --- |
| `tools/state.py` | `lock`, `brief`, `note`, `unlock`, `pause`, `resume`. The brief is the state, the open cycle and the SIGNALS that are due |
| `tools/drive.sh` | A loop outside the session, only when the human asks for one |
| `tools/report.py` | Builds the HTML report and `report-data.json`. Each note runs it |
| `references/drivers.md` | The orchestrator, and what to do on a harness with no subagents |
| `references/fire-prompt.md` | The fixed prompt that each cycle subagent gets |
| `references/checks.md`, `critic-brief.md` | The check ladder and the blind critic |
| `references/gap-matrix.md` | Sources, coverage, `Done when`, statuses |
| `references/lessons.md` | Traps from past runs |
| `references/labs.md`, `beyond.md`, `report.md`, `schemas.md` | Labs, toggles, report, data formats |
| `senses/README.md` | How to control, measure and see the project |
| `journal-template.md` | The journal |
| `examples.md` | The gauntlet-style prompt that this procedure carries out, with example fills |

## Start (in the session that the human started, and on every restart)

Start in any state: mid-work, dirty tree, open cards, no journal. Do not ask
about uncommitted changes. The user owns the state they leave. Commit only
the files that the loop changed.

1. **Read the project rules**: `AGENTS.md`, `CLAUDE.md`, project memory. If
   a project rule and this skill disagree, the project rule wins. Read
   `references/lessons.md` and `references/checks.md`.
2. **Journal**: `docs/awesomeness-loop.md`. If it is missing, create it from
   the journal template. If it has old columns, add the template's new
   sections and columns. Keep the rows.
3. **Sources and coverage** (`references/gap-matrix.md`). Make one gap row
   for each feature area of the reference, not only for the open items. Give
   each open row a `Done when`.
4. **Senses**: list the project's own capture, test, gate and analysis tools
   before you build any. Write them in the Senses table. Run each one once.
5. **Git**: on the default branch, create `awesomeness/<YYYY-MM-DD>`. Add the
   data root `.localdev/awesomeness/` to `.gitignore`. With `--no-commit`, do
   not commit.
6. **Run the loop in this session.** Print one line:
   `Awesomeness loop: [PROJECT] against [REFERENCE]. Next: [row]. Report: [path]. You are the brake.`
   Then this session is the **orchestrator** (`references/drivers.md`). For
   each cycle, it spawns one new subagent with the cycle prompt in
   `references/fire-prompt.md`, reads the status line that comes back, and
   spawns the next one. The orchestrator does no cycle work itself, so its
   context stays small. Each subagent starts new and reads its state from
   the trail, so no cycle carries the history of the cycles before it.
   A journal line, a memory or an old note that says to start `drive.sh` or a
   scheduler is out of date. It is not a project rule. Delete it, and run the
   loop in this session.

## One cycle

`S` means `python3 ~/Github/agent-skills/awesomeness-incremental-loop/tools/state.py --project <repo>`.

Each step names its note. Write the note right after the step, with the
files and the numbers it produced. The form is
`S note <kind> "<what>" [--file <capture>] [--metric name=value]`. Kinds:
`pick`, `predict`, `try`, `see`, `keep`, `revert`, `commit`, `step-back`,
`blocked`, `end`, and `ack` (a reviewed sense drift).

1. **Lock and read.** Run `S lock`. It knows your agent session. After a
   context compaction, it gives your session its lock back. It also takes
   over the lock of a session that has ended. Exit 3 means that another live
   session holds the lock. Exit 4 means paused. On 3 or 4, print the line and
   end the run.
   Each note renews the lock. Before a step that can take more than an hour,
   write its `try` note first. Run `S brief`. If it says `IN PROGRESS`,
   continue that cycle from its last note. Do not repeat a step that has a
   note, and do not retry what it lists under `DO NOT RETRY`.
   The brief's SIGNALS have two parts. Do every line under **DO FIRST** in
   this cycle, before the item: they are small chores (`APPLY` verdicts and
   answers, `MISMATCH`, `NO-DONE-WHEN`, `QUEUED-NO-PROGRESS`, `SENSE-DRIFT`,
   `JOURNAL-LONG`, `STALE-DRIVER`). A chore marked `OVERDUE` was skipped in
   an earlier cycle. For a verdict: `keep` sets the toggle default ON, `kill`
   deletes it and its toggle, `tweak: <note>` queues it. Then the first line
   under **THIS CYCLE'S ITEM** decides the item (`STALL`, `NO-CODE`,
   `CRITIC-DUE`, `EXHAUSTED`). With no item line, use "Picking the item".
2. **Pick the item** (next section). If its row has no `Done when`, write one
   first: a measurable target from the reference evidence.
   Note: `S note pick "<item>" --row "<gap row>" --mode <mode>`. The mode is
   `gap` for normal work, or the step that a signal named: `step-back`,
   `critic`, `coverage`, `unblock`, `beyond`.
3. **Write the acceptance check and the prediction.** Name the done-when
   metric, its value now, and the value that you expect after this step.
   Note: `predict`, with the current value as `--metric`.
4. **Isolate and perceive.** In a busy project, use a lab first
   (`references/labs.md`). If no sense can judge the item, build that sense
   first. For visual work, start with debug gizmos.
5. **Fix the sense before the change.** A new or changed check goes in its
   own commit, with the reason in the commit body. A change commit can add
   checks. It does not loosen or rewrite an existing check to fit its own
   output (lesson 26). A sense measures the distance to the reference, not
   the numbers that the current code makes.
6. **Build** the smallest change that moves the done-when metric. Drive the
   cause, not the visible output (lesson 11). Fan out at most 3 builders. The
   harness or the project decides who builds. Note: `try`, one per attempt.
7. **Self-check (level 0)** on the real artifact. A builder's report is not
   proof. Read the invariant breaks first (`senses/invariants.md`). Look once
   at the frame or the gizmo view behind each new PASS. For 3D, use two angles
   (`senses/3d-views.md`). Run only the checks that the change can affect.
   Note: `see`, one per capture or measure, with `--file` and `--metric`.
8. **Decide.** Note: `keep` or `revert` with the reason, and `commit` with
   `--commit <sha>` after each commit. A revert note is what later runs do not retry.
   - Lab senses pass: set `lab-only`. Commit. The integration is the next step.
   - Full-project senses pass and `Done when` holds: a `functional only` row
     goes to `matches`. A `quality bar` row goes to `queued` and the critic
     queue, but only when the product changed and its metric moved toward
     the reference in this row's cycles. A measure alone does not queue a
     row (`QUEUED-NO-PROGRESS`, `NO-CODE`). Commit.
   - Senses pass and `Done when` does not hold yet: the row stays open.
     Commit. Progress is the metric's move toward `Done when`. A cycle that
     leaves that metric the same made no progress, even when every check passes.
   - Senses fail: fix and check again. Revert a change that made it worse.
     After two failed attempts at the same step, do the step back.
   Write a status change in the gap matrix when you decide it, not later.
9. **End the cycle.** `S note end --status "<before> -> <after>" --progress
   "<metric before> -> <after>"` (or `--progress none`) `--next "<next step>"`.
   Update the project's own ledgers. Run `S unlock --token <token>`. Print the status line,
   then end the run:
   `cycle N | <row> | <status before → after> | progress: <before → after> | <commit> | next: <step> | report: <path>`

## Picking the item

Take the first rule that gives an item:

1. A regression or a failing check that the loop caused.
2. An item that the human put first: the focus argument, recent feedback, open
   cards (`[doing]`, then `[todo]`), explicit priorities. The human is the
   authority. The critic is not.
3. The row of the last cycle (`NOW` in the brief), while it is open and has
   no `STALL`. Finish a row before you start a new one.
4. A full critic queue (about 5 rows) or a mode change: the critic gate.
5. A `lab-only` row. Integrate it before new lab work.
6. A quick win: a `missing` or `below` row with high impact and small effort.
7. The highest-impact open row, even when its effort is L.

**Anti-lazy rule:** after 3 quick wins in a row, the next item comes from rule
2, 5 or 7.

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
4. Note it: `S note step-back "<result and why>"`. Commit the journal, and
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

## Critic gate and beyond mode

The critic gate (`references/checks.md`): one blind round for the whole queue,
with the last captures. Wins and ties go to `matches` or `exceeds`. A loss goes
to `below`, and each deficit becomes a sense check. If ours wins on most rows,
choose a harder reference. In beyond mode (`references/beyond.md`), every
invention ships behind a toggle, default OFF. When the sources leave a value
open, choose one, write it under "Assumptions and asks", and continue.

## Do not

- Do not stop, ask "continue?", or write "ready for review". Each cycle ships
  a proven step, a reverted attempt, a step back, or a `blocked` row.
- Do not put state in a stored prompt. Do not create, change or delete a
  schedule from a cycle. The journal holds the state.
- Do not resume an earlier cycle subagent. Spawn a new one, and let it
  continue the work from the trail.
- Do not soften the critic, lower the reference, loosen a check, or accept a
  builder's report as proof. Do not mark a row `matches` without evidence.
- Do not push, open PRs, post, or send anything outside the repo. Those need
  explicit approval.
- Do not take the user's mouse or focus, and do not run capture farms that
  slow the machine. Do not break the project's rules to get a capture.
- Do not change a human-approved feature because the critic prefers another.
  Put the alternative behind a toggle.
- Do not build tooling for its own sake. Build a sense when an item needs it.
- Do not bring raw logs, full consoles or full-desktop screenshots into the
  context. Use a digest (`senses/digest.md`) and a clean, cropped capture.
