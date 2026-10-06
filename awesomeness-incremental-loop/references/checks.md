# Checks: the agent checks its own work, the critic only at the gate

Tokens and time cost money. A blind critic round costs a new capture, a
sub-agent and a long answer. Most small changes do not need it, because a good
sense catches the problem in seconds. So use the cheapest check that can
answer, and keep the blind critic for the moment a row is about to be called
done.

## The check ladder

Go up only when the level below cannot answer.

| Level | Who | When | What |
| --- | --- | --- | --- |
| 0. Self-check | The orchestrating agent, with senses | Every change | Run the focused senses again. Read the digest of the affected metrics. Look at the gizmo view and at one clean capture. |
| 1. Integration check | The orchestrating agent, with senses | A lab result goes into the full project, or a change touches shared code | The same senses in the full project. Only the checks that the diff can affect. |
| 2. Blind critic | A separate sub-agent | Only at a gate (see below) | A blind side-by-side against the reference. A verdict and a list of deficits. |
| 3. Human | The user | Taste, feel, toggles | The "Pending verdicts" table in the journal. Human feedback beats the critic. |

## Level 0: make the self-check smart

- **Invariants always on.** The harness watches the common-sense rules on
  every frame (`senses/invariants.md`). Any break is a failing check, even
  when it is not in the item under work. Read the breaks in the digest first.
- **Predict first.** Before you run the sense, write the number or the look
  that you expect. For example: "foot slide under 2 cm, the foot on the target
  marker". A result that differs from the prediction is the signal to look
  deeper. A result that matches lets you move on.
- **Measure, do not trust.** A builder's report is not evidence. The
  orchestrating agent runs the sense again on the real artifact. A sense result
  is evidence, because it is a measurement and not an opinion.
- **Many angles for 3D.** A 3D self-check uses at least two views at 90
  degrees, with everything that is not measured hidden
  (`~/Github/agent-skills/awesomeness-incremental-loop/senses/3d-views.md`).
- **Look once.** After each new PASS, look at one frame or the gizmo view to
  make sure the number shows the real behavior (`lessons.md`, rule 2).
- **Run only what the change can affect.** One or two focused checks on one
  variant. Run the wider gates once, at the gate.
- **Reuse evidence.** Do not run a check again when nothing that it measures
  changed. Do not capture again a shot whose scene, code and assets did not
  change.

## Level 2: when the blind critic runs

Call the critic only for one of these gates:

1. **A row is about to be set `matches` or `exceeds`** for a `quality bar`
   reference. This is the "done" claim. A `functional only` row can be set by
   senses alone.
2. **The senses cannot decide.** The question is about the look or the feel,
   no metric covers it, and the agent's own look is not sure.
3. **A mode change.** Before beyond mode starts, or before you raise the
   reference.
4. **A step back on a `quality bar` row** (signal `STALL`). Run one direction
   round on the current state (`references/critic-brief.md`). It answers "is
   this approach getting closer to the reference?", not "is it done?".
5. **The human asks for it.**

If a `quality bar` reference has no frames or clips in the repo, the critic
has nothing to compare. Add an `ask` row under "Assumptions and asks" for the
frames that you need. Until the human answers, those rows stop at `queued`.

Do not call the critic for a work-in-progress change, for a lab result, or to
repeat what a sense already showed.

## Make each critic round count

- **Batch.** Rows that reach gate 1 wait in the "Critic queue" in the journal.
  Run one critic round for the whole queue: when the queue has about 5 rows,
  when a milestone ends, or before a mode change.
- **Reuse captures.** Use the captures from the last self-check. Capture again
  only the shots that changed since then.
- **Crop to the question.** Give the critic only the shots and regions that
  the queued rows are about (critic mode, see
  `~/Github/agent-skills/awesomeness-incremental-loop/senses/visual-convergence.md`).
- **Turn deficits into senses.** For each deficit, ask: "Can a metric, a gizmo
  or a threshold catch this?" If yes, add that check. Then the fix is proven at
  level 0, and the next critic round is not needed for it. Only a deficit that
  no sense can catch stays a critic-only item.

## Cost signals

Stop and change the method when one of these happens:

- Two critic rounds in a row on the same row. A sense is missing. Build it.
- A row stays open for 3 cycles. Step back (SKILL.md). More cycles of the
  same kind will not close it.
- A check changes in the same commit as the code that it judges. The check
  now follows the code (lesson 26). `state.py` reports it as `SENSE-DRIFT`.
- A capture takes longer than the change. Use a lab, a smaller shot or the
  measurement view.
- The context fills with raw data. Write a digest script.
