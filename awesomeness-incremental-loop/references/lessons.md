# Lessons: traps that cost real cycles

Each rule below came from a long run that went wrong. Read this file at every
start. When the loop hits a new trap, add it here with the same three parts.

## Measuring

1. **The engine number passed, but the delivered result failed.**
   - Sign: the builder reports green probes, and the blind critic still loses.
     Each time someone measured the delivered clip again, the critic was right.
   - Rule: measure what the human and the critic see. For a video, decode the
     whole clip and measure the frames. Do not seek with a keyframe jump (for
     example `ffmpeg -ss` before `-i`), because it can return the wrong frames.
     The engine state is not the deliverable.
2. **The metric passed through a cheat.**
   - Sign: a number goes green, but the frames show a different behavior. For
     example, a "foot plant" that is a slide, or a "load" signal that only
     repeats the command that the code sent.
   - Rule: after each new PASS, look at the frames once to make sure the pass
     shows the real behavior. Measure the effect, not the command. When one
     signal can be faked, require two or three independent signals together.
3. **The change is too small to see.**
   - Sign: the probe reports motion, and the critic says "nothing moves".
     A few millimetres at a distance can be less than one pixel at capture size.
   - Rule: check that a change is visible at the capture resolution and frame
     rate before you tune it. If the critic cannot see it, it does not exist.
4. **A threshold from one scene does not work in another scene.**
   - Sign: a brightness or colour mask finds the object in our scene, but in
     the reference it finds walls and shadows.
   - Rule: for masks, render a measurement view in flat colours (each part one
     unshaded colour, lossless frames). Compare to the reference only with
     metrics that transfer, such as motion.
5. **The gate was never calibrated.**
   - Rule: run each gate on the reference too, and keep that row in the gate
     file. Fix the method in writing before a run. Do not change the method or
     the limits during a run to make a result pass.

## Targets

6. **The target came from a description, not from the reference.**
   - Sign: many rounds chase a behavior that the reference does not show.
   - Rule: measure the primary reference frame by frame before you set a
     target. Write the result in a reference breakdown doc. Second-hand
     descriptions and articles are hints, not targets.
7. **One number for a target that varies.**
   - Rule: when the reference shows a range, gate on a band (for example
     0.5 to 2.7 s), not on one value.
8. **Plumbing became a goal.**
   - Sign: a "reference gap" for a behavior that the harness needs (a reset, a
     respawn, a debug pose) but the reference never shows.
   - Rule: harness plumbing is never a target. Do not log a gap that the agent
     assumed. Ask the human when the objective is not clear.
9. **The reference has a role.**
   - Rule: tag each reference as `quality bar` or `functional only`. A
     functional reference shows what exists and how it works. It does not set
     the quality level. Human feedback beats both.
10. **Nothing can satisfy the rule.**
    - Sign: an enforced invariant pushes the result into a worse state. For
      example, a clearance rule pushes a part away from where it must sit.
    - Rule: check that the geometry or the math allows the rule before you
      enforce it. If it does not, measure the value and guard only real bugs.
11. **Someone tuned the output in place of its cause.**
    - Sign: the code places a visible part directly, and the parts that
      should drive it bend to follow. The result breaks limits (folded joints, clipping).
    - Rule: model the causal chain. Drive the cause (intent, then body, then
      the tool), inside real limits. The visible result is the output.

## Checks and gates

12. **Someone loosened a check to make it green.**
    - Rule: a check that passed only because of a cheat can go red when the
      cheat goes. Mark it `expected red` in the journal with the step that
      must make it green. Report its numbers. Do not loosen it.
13. **Too many tests for each attempt.**
    - Sign: hours go to full gate sweeps before and after each small try.
    - Rule: while you iterate, run only the one or two checks that the change
      can affect, on one variant. Run the affected gates once at the end. To
      prove "default unchanged", compare output bytes. Do not run a sweep.
14. **The capture recorded old frames.**
    - Sign: the file count is right, but some images repeat. A hidden or occluded
      window can stop painting.
    - Rule: stamp a frame number in each image and require numbers in sequence.
      Use the app's state (DOM, engine state) as the truth for logic, and the
      frames only for the look.

## Agents

15. **A builder's success report is not proof.**
    - Rule: check every builder result yourself: the diff, the focused checks
      and the frames. A builder must not grade its own work.
16. **A report can arrive before the files are final.**
    - Rule: before a timing-sensitive run, wait until the files stop changing.
17. **A guess about the cause is not a finding.**
    - Rule: look at the artifact (frame, log line, file) before you pass on a
      cause that a sub-agent gave.
18. **More builder rounds after repeated losses.**
    - Rule: after 2 failed attempts on one item, send it to an auditor, not
      to another builder round. The auditor finds the root constraint.
19. **Parts are missing from the lab rig.**
    - Sign: the subject passes in the lab. In the full project it changes.
    - Rule: keep a stand-in for each part that touches the subject, for
      example a prop in the hands. Then the lab pose matches the real one.
20. **A rule that only lives in prose.**
    - Rule: when a lesson repeats, move it into the strongest mechanism that
      works: a gate, a check, a test or a hook. Prose is for judgment only.
21. **A blind critic for every small change.**
    - Sign: each little change waits for a new capture and a critic round.
      Tokens and hours go to checks that a metric or a gizmo could do in
      seconds.
    - Rule: check each change with senses. Call the critic only at the gate
      (`references/checks.md`): a row about to be called done, a question no
      sense can answer, or a mode change. Batch the rows. Turn each critic
      deficit into a sense check, so the next fix does not need the critic.
22. **One camera angle for a 3D check.**
    - Sign: a part looks right in the check view and is wrong in depth. A
      capture full of the room and the HUD hides the small error under test.
    - Rule: check 3D from at least two views at 90 degrees, plus the real
      view. Hide everything that is not measured, but do not remove it: a
      removed part can change the behavior (`senses/3d-views.md`).
23. **The human found a defect that any person would call wrong.**
    - Sign: wheels below the ground, a hand through a wall, text off the
      button. The agent did not see it because it checked only its item.
    - Rule: keep invariants on in every run (`senses/invariants.md`), and
      give every capture a metadata record (`senses/capture-metadata.md`).
      Each such complaint becomes a new invariant.

## Loop mechanics

These came from three overnight runs on 2026-10-06 (Grok, scheduled runs, 119
cycles). Each one now has a mechanism. The prose is for the judgment around it.

24. **A run resumed the transcripts of the runs before it.**
    - Sign: each run costs more (0.72 to 4.46 USD over 10 runs). Then a run
      fails at its start on a resume limit (204,800 tokens). Seen in 2 of 3 runs.
    - Rule: each cycle is a new run, and the state lives on disk.
    - Mechanism: `references/drivers.md`, `tools/drive.sh`.
25. **The next item lived in the stored prompt.**
    - Sign: the watcher rewrote the prompt after each run. A run that started
      before the rewrite did finished work again: 31 of 84 runs, about 19 USD.
    - Rule: the stored prompt never changes. The next step is in the trail.
    - Mechanism: `references/fire-prompt.md`, `state.py brief`.
26. **A check followed the code.**
    - Sign: the test changes in the same commit as the code. Its assertions
      turn to fit the new output, or a tolerance opens (0.05 to 0.08). Every
      cycle is green and the row does not move. Seen in 32 of 33 commits of
      one pose test.
    - Rule: a check changes only in its own commit, with the reason. A sense
      measures the distance to the reference, not the current output.
    - Mechanism: `state.py` signal `SENSE-DRIFT`.
27. **A row stayed open for ever.**
    - Sign: about 60 green cycles over 10 hours on one row, each one posing
      one more limb (rule 11), and the row still `partial`.
    - Rule: each row has a `Done when`. After 3 cycles, step back: split it,
      change the approach, ask the critic, or block it.
    - Mechanism: `state.py` signals `STALL` and `NO-DONE-WHEN`.
28. **The loop stopped itself when no row was open.**
    - Sign: a run reported "no unblocked gap remains", and the watcher
      removed the schedule. The machine stood idle for 6 hours.
    - Rule: do the exhausted procedure: coverage, unblock, beyond mode.
    - Mechanism: `state.py` signal `EXHAUSTED`. The run prompt forbids
      schedule changes.
29. **The watcher did the work again.**
    - Sign: the session that started the scheduler ran each run's checks
      again: 62 USD of 138, and no false claim found.
    - Rule: the watcher reads the status line. It opens the evidence only on
      a missing commit, missing evidence, or a disagreement with the journal.
30. **A session with no driver stopped when its turn ended.**
    - Sign: 5 cycles, then 8 hours idle, until the human came back.
    - Rule: the skill starts its own driver at the end of the Start steps.
    - Mechanism: `drive.sh --agent <cli> --detach` (`references/drivers.md`).
31. **The loop wrote its state only at the end of a cycle.**
    - Sign: a run that stopped in the middle left no record. The next run
      started that cycle from zero, and the report was a job at the end.
    - Rule: write each step to the trail when it happens. The trail is the
      report: it keeps the screenshots and metrics in one place to recall.
    - Mechanism: `state.py note` (it rebuilds the report), and the
      `IN PROGRESS` part of `state.py brief`. A new `pick` is refused while a
      cycle is open.
32. **The loop left the session.**
    - Sign: the skill started a detached driver process. The loop then ran
      outside the agent that the human commanded, where the human could not
      see it or stop it with that agent.
    - Rule: the session that runs the skill is the orchestrator. Each cycle
      is a new subagent of that session. A loop outside the session runs
      only when the human asks for one.
    - Sign, later: an old journal line and an agent memory said to restart
      the driver. The next start obeyed them and not the skill.
    - Mechanism: SKILL.md Start step 6. `drive.sh` refuses to start without
      `--human-asked`. `state.py brief` gives `STALE-DRIVER` for an old
      journal line.

## Night two (2026-10-07, 123 cycles in three projects, in-session subagents)

33. **A compacted cycle hit its own lock.**
    - Sign: after a context compaction, the cycle ran its prompt again, got
      BUSY on its own lock, and left the lock behind. Two cycles, about 4 USD,
      and 4 orchestrator turns to find the dead owner.
    - Rule: the lock knows the agent session. The same session takes it back.
    - Mechanism: `state.py lock` records the agent pid (a session and its
      subagents share it).
34. **One signal starved the others.**
    - Sign: `EXHAUSTED` won every cycle. `JOURNAL-LONG` showed in 12 cycles in
      a row (40.8 to 54.8 KB), and a `SENSE-DRIFT` waited 2 cycles.
    - Rule: small chores come first, in the same cycle, before the item.
    - Mechanism: the brief splits `DO FIRST` from `THIS CYCLE'S ITEM`, and
      marks a chore `OVERDUE` in its second cycle.
35. **Coverage turned into a new way to circle.**
    - Sign: 27 coverage rounds in one project. 19 cycles in a row added one
      row each at the level of one audio constant. 0 unblock rounds with 12
      to 21 rows parked.
    - Rule: coverage, unblock and beyond take turns. A coverage row names
      what a user sees or does, not a constant.
    - Mechanism: `pick --mode`, and the brief names the next step.
36. **The same sense drift came back every cycle.**
    - Sign: one commit was listed in 3 cycles in a row, and 4 times in one brief.
    - Rule: review it once, and record the result.
    - Mechanism: `note ack --drift <sha> "<why>"`, one line per commit.
37. **Cycles measured and did not build.**
    - Sign: 16 cycles (3.9 hours, about 17 USD) changed no product file.
      Rows went to `queued` on measures alone, and the first critic round
      gave 0 wins and 6 losses.
    - Rule: a row waits for the critic only after the product changed and
      its metric moved.
    - Mechanism: `NO-CODE` after 3 such cycles, and `QUEUED-NO-PROGRESS`.
38. **The loop spun for 13 hours with nothing left to do.**
    - Sign: in one project, the last product commit was cycle 78. Cycles 79
      to 279 shipped nothing. 50 reviews in a row gave `useful 0/3`, and 202
      cycle runs used about 445M tokens. The reviews named the cause (only a
      human verdict could change what a user sees), but no step acted on it.
      The reviews also banned beyond mode, so every round became a recount.
    - Rule: when no row is open and the product has not changed for 6
      cycles, write the asks for the human and wait. Do not poll with agent
      runs. A review does not turn a step of the skill into a no-op.
    - Mechanism: the brief gives `WAITING`. The cycle ends `--status waiting`,
      and the orchestrator and `drive.sh` run `state.py wait`, which runs no
      agent and returns on a human change. At most 5 toggles wait for a
      verdict: at the cap, the brief skips beyond mode.
