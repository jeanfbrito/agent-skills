---
name: awesomeness-incremental-loop
description: >-
  Runs an endless improvement loop on a project that has reference material in
  its docs. Each cycle finds the most important gap in the references and
  priority docs (set priorities first, quick wins next) and builds it. The
  agent checks each change itself with cheap senses: metrics, gizmos and one
  clean capture. A harsh blind critic runs only when a row is about to be
  called done. Everything starts small and grows only when stable. When the
  project matches the reference, it invents additions, each behind a toggle until a human gives a verdict. It can restart at any
  moment from a journal. Only the human stops it. Adapted from the gauntlet
  loop. Triggered by '/awesomeness-incremental-loop', 'awesomeness loop', 'run
  the awesome loop', 'what is next from the references', 'find what is missing
  versus the reference', 'keep improving until I stop you'.
argument-hint: "[optional: focus area] [optional: --no-commit] [optional: --reference NAME]"
---

# Awesomeness Incremental Loop

The gauntlet loop builds toward a named reference until the human stops it.
This skill keeps that engine and adds these rules. It finds its own work in
the repo docs. It restarts from a journal. It checks itself with cheap senses
and calls the blind critic only at the "done" gate. It works in labs before
it integrates. It adds toggled inventions past 100%. It starts small.

**The human is the brake.** The loop has no "done" state. Do not ask "continue?".

## Start small, grow when stable

This is the "incremental" in the name. Every dimension starts at its smallest
useful size. It grows one step only when the current step is stable: its checks
pass on two runs in a row, and no new invariant breaks.

| Dimension | Start | Grow to |
| --- | --- | --- |
| Scope | One subject in a lab | The full project |
| Rates | 30 or 60 fps, physics at the same rate | More only on proof (`senses/metrics.md`) |
| Views | The one view that the item needs | More angles for 3D (`senses/3d-views.md`) |
| Checks | The focused senses | Wider gates, then the critic gate |
| Builders | One | At most 3 in parallel |
| Reference | The bar the project can reach | A harder bar when ours wins |
| Senses, invariants, report | The few that the item needs | More as blockers and complaints show gaps |

Files (in `~/Github/agent-skills/awesomeness-incremental-loop/`):

| File | Use |
| --- | --- |
| `references/checks.md` | The check ladder: self-check, integration check, blind critic gate, human |
| `senses/README.md` | How to control, measure and see the project. One guide per topic. |
| `references/labs.md` | Spike, lab, integrate |
| `references/lessons.md` | Traps from past runs. Read at every start. |
| `references/gap-matrix.md` | Where to find sources, and the gap matrix columns and statuses |
| `references/report.md` | The local HTML report and `report-data.json` for recall |
| `references/beyond.md` | Beyond mode and toggles |
| `references/schemas.md` | Data formats for captures, events, metrics and critic rounds |
| `references/critic-brief.md` | The blind critic brief and how to keep the key hidden |
| `tools/report.py` | Builds the HTML report and `report-data.json` from the data |
| `journal-template.md`, `examples.md` | Journal and example fills |

## The prompt (fill it, then run it as your own instructions)

```text
I want [PROJECT] to reach the level of [REFERENCE], and then go past it.
Read every reference and priority doc in the repo. Find the most important
thing that is missing, broken or below the reference. Do the human's set
priorities first. When there are none, take the quick wins with the highest
visible effect.

Fan out sub-agents. Give each sub-agent one item. Check every change yourself
with cheap senses: metrics, gizmos and one clean capture. Do not repeat a check
when nothing it measures changed. Only when a row is about to be called done,
have a separate sub-agent check it [CHECK] against [REFERENCE]. That critic
must be really harsh. It compares the two side by side, blind, and says which
one is better. If ours is not better, turn each deficit into a sense check and
a next item. Keep going.

When nothing is missing, do not stop. Invent what would make [PROJECT] more
awesome than [REFERENCE]. Put every invention behind a toggle until a human
says keep or kill. [LOOP_VERB] until the human stops you. Fan out sub-agents[CLOSING_TAIL].
```

Slots: `PROJECT` and `REFERENCE` come from the repo docs. `CHECK` is `visually`
for visual work, `by running it` for behavior, `against the spec` for contracts.
Claude Code: `LOOP_VERB` = `/loop`, `CLOSING_TAIL` = ` and ultracode`.
Codex: `LOOP_VERB` = `/goal`, `CLOSING_TAIL` is empty.

## On invoke (every start is also a restart)

Start in any state of any project: mid-work, dirty tree, open cards, no
journal. Do not stop to ask about uncommitted changes or work in progress.
Read the state, take it as the starting point, and start. The user owns the
state they leave. Commit only the files that the loop changed.

1. **Read the project rules.** Read `AGENTS.md`, `CLAUDE.md` and project memory.
   Their verification, capture, delegation and "do not" rules apply to every
   cycle. If a rule and this skill disagree, the project rule wins. Then read
   `references/lessons.md` and `references/checks.md`.
2. **Read the journal.** Default path: `docs/awesomeness-loop.md`. If it is
   missing, create it from the journal template. Read the human verdicts first.
3. **Apply the verdicts.** `keep`: make the toggle default ON, or remove the
   toggle when the human says so. `kill`: remove the feature and its toggle.
   `tweak: <note>`: queue a new item with that note. Record each one as applied.
4. **Find the sources** (`references/gap-matrix.md`). Write their paths in
   the journal. For the history of a row, read `report-data.json`.
5. **Adopt the senses that exist.** On the first start, list the project's
   own tools before you build any. Look for capture, test, gate and analysis
   scripts, debug servers, MCP tools, and docs about them. Add each one to the
   journal's "Senses" table. Build only what is missing, and write new data in
   the formats of `references/schemas.md`. On each start, run each sense in
   the table once and make sure that it still works.
6. **Rebuild the gap matrix**. Check again each row that
   says `matches` but is older than 10 cycles, or that a later change touched.
7. **Keep git clean.** If the current branch is the default branch, create
   `awesomeness/<YYYY-MM-DD>` and work there. Commit each verified item at
   once. Give parallel builders their own worktrees. Add the data root
   (`.localdev/awesomeness/`) to `.gitignore`. Leave no stray files. With
   `--no-commit`, do not commit.
8. Print one status line, then start the cycles:

```text
Awesomeness loop: [PROJECT] against [REFERENCE]. Mode: [gap | beyond]. Next: [item]. You are the brake.
```

## Sources and gap matrix

Details: `references/gap-matrix.md`. Use every human priority, known problem,
reference and product-focus doc you can find. Tag each reference `quality bar`
or `functional only`. If no reference exists, ask one question: "What is the
reference?" This is the only start condition that can block.

One gap-matrix row per thing the reference has, does or looks like. Statuses:
`missing`, `partial`, `below`, `lab-only`, `queued`, `matches`, `exceeds`,
`blocked`. Each status needs evidence. A `quality bar` row reaches `matches`
only through the critic gate.

## Picking the next item

Take the first rule that gives an item:

1. A regression or failing check that the loop caused. Fix it first.
2. An item the human put first: the focus in the arguments, recent feedback,
   then open cards (`[doing]` first, then `[todo]` in order), then explicit
   priorities. Human feedback is the authority. The critic is not.
3. A full critic queue (about 5 rows) or a mode change: run the critic gate.
4. A `lab-only` row. Integrate it before you start new lab work.
5. A `missing` or `below` row with high impact and small effort (a quick win).
6. The highest-impact `missing`, `partial` or `below` row, even if the effort is L.
7. Beyond mode (the matrix has no gap rows): the best idea in the journal
   backlog. If the backlog is empty, make new ideas first (`references/beyond.md`).

**Anti-lazy rule:** after 3 quick wins in a row, the next item must come from
rule 2, 4 or 6. Do not let small cosmetic items take all the cycles.

## One cycle

1. **Write the acceptance check and the prediction.** One sentence that a sense
   can pass or fail, and the result you expect. Example: "Foot slide per
   contact under 2 cm in the walk shot, and the gizmo shows the foot on the
   target marker".
2. **Isolate it and perceive it.** If the item lives in a busy project, work on
   it in a lab first (`references/labs.md`). If no sense can judge the item,
   build that sense first. For visual work, start with debug gizmos that you
   and the human can toggle in a UI panel.
3. **Build.** Fan out builders for independent items, at most 3 at a time.
   The harness or the project decides who builds. This skill does not. Give
   each builder its item, the reference evidence and the acceptance check.
4. **Self-check (level 0).** Run the focused senses again yourself on the real
   artifact. A builder's report is not proof. Read the invariant breaks
   first (`senses/invariants.md`). Look once at the frame or the
   gizmo view behind each new PASS. For 3D, look from at least two angles,
   with everything that is not measured hidden (`senses/3d-views.md`). Run only the checks that the change can
   affect.
5. **Decide.**
   - Lab senses pass: set `lab-only`. Commit. The integration is the next item.
   - Full-project senses pass: `functional only` row, set `matches`. Commit.
     `quality bar` row, set `queued` and add it to the critic queue. Commit.
   - Senses fail: fix and run the self-check again. Revert a change that made
     the result worse.
   - Two failed attempts at the same item: send it to an auditor to find the
     root constraint. If no path remains, set `blocked` with the reason. Go to
     the next item. Do not stop the loop.
   - When you solve a blocker on a sense, write a guide in `senses/`.
6. **Journal, ledgers and report.** Add one line to the cycle log. Give the
   item, change, evidence path, check level and result, and commit hash. If the
   project keeps its own ledgers, update them too: one completion line per
   cycle (for example `.localdev/workflow/done.md`), and the card that the
   item came from. Run
   `python3 ~/Github/agent-skills/awesomeness-incremental-loop/tools/report.py`.
   Then start the next cycle at once.

**The critic gate** (`references/checks.md`, brief in
`references/critic-brief.md`): one blind round for the whole queue. Reuse the last captures. Rows that win or tie go to `matches` or
`exceeds`. Rows that lose go back to `below`, and each deficit becomes a sense
check where one can catch it. If ours wins on most rows, the reference is too
easy: pick a harder one, write it in the journal, and continue.

## Beyond mode

When the matrix has no gap rows, invent. Every invention ships behind a toggle,
default OFF, with sense evidence, in the "Pending verdicts" table. Do not wait
for verdicts. Details: `references/beyond.md`.

## Do not

- Do not stop, ask "continue?", or write "ready for review". Only the human ends the loop.
- Do not finish a cycle with only analysis or a plan. Each cycle ships a proven change, a reverted attempt, or a `blocked` row with its reason.
- Do not call the blind critic for a work-in-progress change, a lab result, or what a sense already shows. Do not capture again what did not change.
- Do not soften the critic, lower the reference, or accept a builder's report as proof.
- Do not mark a row `matches` without evidence.
- Do not push, open PRs, post, or send anything outside the repo. Those still need explicit approval.
- Do not break the project's rules to get a capture. Do not take the user's mouse or focus, and do not run capture farms that slow the machine.
- Do not remove or change a human-approved feature because the critic prefers something else. Put the alternative behind a toggle.
- Do not build tooling for its own sake. Build a sense only when an item needs it.
- Do not chase frame rate or physics rate. Lock 30 fps for slow games and 60 fps for fast ones, with physics at the same low rate. Raise physics only when a lab proves the step size causes a failing metric (`senses/metrics.md`).
- Do not bring raw logs, full consoles or full-desktop screenshots into the context. Use a digest and a clean, cropped capture.

## Running it without end

The loop has no exit. The human stops it with Ctrl-C or by ending the
session, at any moment. So:

- Never plan a stop, a summary turn or a hand-off. Finish a cycle, then start
  the next one.
- Keep the state safe for a kill at any time: commit each verified item, and
  write the journal at the end of each cycle. A kill loses only the item in
  progress.
- **Claude Code:** start it as `/loop /awesomeness-incremental-loop` with no
  interval. When a turn ends, schedule the next wakeup with the same prompt at
  the minimum delay.
- **Codex:** run it under `/goal`.
- **Restart:** the next start rebuilds everything from the journal,
  `report-data.json`, git history and the sources.
