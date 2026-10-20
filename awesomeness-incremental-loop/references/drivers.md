# The orchestrator: how the session repeats the cycle

The loop is one cycle, repeated. A cycle reads its state from the journal and
the trail, ships one thing, writes each step as it happens, and ends
(SKILL.md, "One cycle"). The session that the human started with the skill
command runs the loop. It stays in that session, where the human sees it and
stops it.

## Subagents (the default)

The session is the **orchestrator**. It does no cycle work itself:

0. Before the first spawn, and after any long gap, run `state.py brief` and
   read its `LOCK` line. `LOCK: BUSY` means that another live session runs
   the loop. Do not spawn: a cycle would only stop on the busy lock. Tell
   the human which session runs the loop, and wait for their choice.
1. Spawn one new subagent. Give it the prompt in `references/fire-prompt.md`,
   with `{project}` filled. Give it nothing else: its state is on disk.
2. Wait for it to end. Read only its last line, the status line.
3. Print that status line for the human. Then spawn the next new subagent.
   Repeat without end. When the human says finish this cycle and stop, do
   "Stop for the day" (below).

Rules:

- **A new subagent for each cycle.** Do not resume or continue an earlier
  subagent. A resumed subagent carries the history of every cycle before it.
  Each run then costs more, and at last fails at its start on a context
  limit (lessons 24 and 25).
- **The prompt never changes.** Do not add the next item, the commit or
  "do not retry" notes to it. The subagent reads them from the trail
  (`state.py brief`). A plan change from the human goes in the journal as a
  human priority.
- **One cycle at a time.** Spawn the next subagent only after the last one
  ends. The cycle lock also refuses a second cycle.
- **A lock left behind.** The next cycle subagent of this session takes the
  lock back by itself, and continues the open cycle from the trail. Use
  `state.py unlock --orphan` only when a lock from another session blocks the
  loop and that session is gone.
- **No hand work in the orchestrator.** Project ledger chores (cards, done
  lists) belong to the cycles. The orchestrator spawns, reads and prints.
- **Trust the status line.** The subagent did its own self-check. The
  orchestrator does not run those checks again. It opens the evidence only
  when a status line has no commit or no evidence, or disagrees with the
  journal. The live report shows the same facts.
- **The loop does not stop itself.** A status line that says "nothing left"
  is not a stop: the next cycle reads the `EXHAUSTED` signal and continues.
- **Waiting for the human.** A status line with `waiting` in its status
  field means that the cycle found `WAITING`. Do not spawn a cycle. Print
  once: `Waiting on you: <journal path>, section "Waiting on you".` Then run
  `state.py wait --project <project>`, in the background when the harness
  wakes the session. It runs no agent. Exit 0: spawn the next cycle. Exit 5
  (only with `--max-hours`): run it again. Do not spawn cycles to poll.
- **Waiting.** If the harness wakes the session when a background subagent
  ends (Grok and Claude Code do), spawn it in the background and end the
  turn. The completion message starts the next turn: spawn the next cycle
  then. If the harness does not wake the session, wait for the subagent in
  the same turn and do not end the turn.
- **Ask the decisions.** When a human message arrives and
  `docs/awesomeness-loop-decisions.md` has `open` entries, ask them before
  the next spawn, at most 4 per round (`references/decisions.md`). Write each
  answer, commit the file, then spawn. Also ask them when the human returns
  from a `WAITING` stop.
- **Hand work.** If the human asks this session for other work while the loop
  runs, run `state.py pause`, do the work, commit, and run `state.py resume`.
- **Human asks while the loop runs.** When the human gives the loop new work
  ("put this on the todo", or a stream of feature asks), do four things for
  each ask:
  1. Write a card in the project's todo ledger. Quote the human's words, and
     give it a measurable DoD and the facts that you already found.
  2. Add a gap row for the ask, with its own `Done when`, so that the cycles
     note it under that row. A cycle can do the ask under the row of the
     last cycle. Then that row gets cycles with no progress, and the brief
     gives a false `STALL`. This occurred two times in one run.
  3. Add a `Next priorities` line in the journal's `Direction` that names the
     row, in the human's order. Edit the line by its exact text. Do not use a
     script that finds a list number such as `1.`. That number also occurs
     inside other text, and one such script broke a sentence.
  4. Find each `Stop doing` line, `held` row or frozen ask that the new ask
     contradicts. Delete it, or reword it so that it permits the ask. A stale stop
     line beats a card: a cycle reads the Direction first and skips the ask.
  The human is the authority, so the new ask wins over the old line.
- **Side tracks.** The human can ask for more speed ("fan out", "do all we
  can"). Then the orchestrator can run side tracks beside the serial cycles.
  Researchers take rows that need cited numbers. Builders work in their own
  worktrees. Obey these limits:
  1. Give a builder only a row with no timing in its `Done when`. A builder
     runs heavy work with `nice -n 19`, because the timing rows of the loop
     need a quiet machine.
  2. A side track does not edit the journal, the trail or the decisions file.
     It commits on its own branch.
  3. Merge a side branch into the loop branch only between cycles. Then update
     the journal rows of that work.
  4. After each merge, run the checks of the side track again on the merged
     loop branch. A pass in the worktree does not count: a side feature and a
     loop change can each pass alone and fail together.
- **Commit while a cycle runs.** Do not stage files: the git index is
  shared, and the cycle's next commit takes all staged files, under the
  cycle's message. Commit only with `git commit -- <paths>`. If the
  pre-commit hook fails on the cycle's unfinished work, a docs-only commit
  can use `--no-verify`. Write the reason in the commit message.
- **A human verdict gets a check.** When the human picks one option over
  another (a pose, a feel, a default), a written rule is not enough. A
  later cycle can change the chosen option and pass every check. Add a test that passes on the chosen option and fails
  on the rejected one. Prove that it fails on the rejected one. The
  `APPLY` and `APPLY-DECISIONS` chores ask the cycles for the same check.
- **Choices of feel are playable.** A choice about how something feels,
  looks or plays is not a text menu. Build each option (a worktree and a dev
  server per option, or a URL flag), and give the human one full URL for each
  option. Stop those servers after the human chooses.
- **The human delegates.** When the human says "decide it yourself", choose,
  and write the reason in the decision entry
  (`Answer: delegated, loop chose <option> because <reason>`). Ask again only
  about what no experiment can settle and what the human did not delegate.
- **Stop for the day.** When the human says "finish what is open" or "stop":
  1. Do not spawn the next cycle. Let the running cycle end, and print its
     status line.
  2. Run `state.py pause`. It prints the `LOCK` line. Continue only at
     `LOCK: free`.
  3. Stop the dev servers and delete the worktrees that the orchestrator
     started. Keep the patch of each option that is not ported yet.
  4. Report what the loop committed, what it did not push, and the next item. The
     human starts the loop again with `state.py resume`.

## A harness with no subagents

- If the harness can start its next turn by itself (Claude Code `/loop` with
  no interval, Codex `/goal`), do one cycle per turn in the session.
- If it cannot, do the cycles back to back in the current turn. Before the
  first cycle, print once: "This harness cannot restart me. The loop stops
  when this turn ends."

A context compaction loses nothing, because each cycle reads `state.py brief`.

## Outside the session (only when the human asks)

`tools/drive.sh` runs the same cycle prompt with an agent CLI. Each cycle is
a new process. Use it, for example, on a machine with no open agent session.
The skill never starts it by itself, and it refuses to start without
`--human-asked`. `drive.sh --help` gives the presets
(`--agent grok|claude|codex`), `--detach`, `--status` and `--stop`.
